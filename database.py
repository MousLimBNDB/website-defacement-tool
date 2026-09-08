import os
import sys
import json
import logging
import sqlite3
from datetime import datetime
import config

logger = logging.getLogger(__name__)

# Check if psycopg2 is available for PostgreSQL
HAS_PSYCOPG2 = False
try:
    import psycopg2
    import psycopg2.extras
    HAS_PSYCOPG2 = True
except ImportError:
    pass

def get_db_connection():
    """
    Returns a PostgreSQL database connection if configured and reachable.
    Otherwise, gracefully falls back to local SQLite.
    """
    if HAS_PSYCOPG2 and config.POSTGRES_PASSWORD:
        try:
            conn = psycopg2.connect(
                host=config.POSTGRES_HOST,
                port=config.POSTGRES_PORT,
                dbname=config.POSTGRES_DB,
                user=config.POSTGRES_USER,
                password=config.POSTGRES_PASSWORD,
                connect_timeout=3
            )
            return conn, "postgres"
        except Exception as e:
            logger.warning(f"PostgreSQL connection to {config.POSTGRES_HOST} failed ({e}). Falling back to SQLite.")

    # SQLite fallback
    os.makedirs(os.path.dirname(os.path.abspath(config.SQLITE_DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(config.SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn, "sqlite"

def init_db():
    """
    Initializes PostgreSQL / SQLite database schema.
    Creates defacement_logs, defacement_incidents, and defacement_popups tables.
    """
    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    
    if db_type == "postgres":
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS defacement_logs (
            id SERIAL PRIMARY KEY,
            target_id INTEGER,
            url TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            similarity_score REAL,
            is_defaced BOOLEAN DEFAULT FALSE,
            confidence INTEGER DEFAULT 0,
            change_type VARCHAR(100),
            analysis_summary TEXT,
            screenshot_path TEXT,
            diff_path TEXT,
            popup_screenshot_path TEXT,
            status VARCHAR(50) DEFAULT 'SUCCESS',
            error_message TEXT
        );
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS defacement_incidents (
            id SERIAL PRIMARY KEY,
            target_id INTEGER,
            url TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            change_type VARCHAR(100),
            confidence INTEGER DEFAULT 0,
            summary TEXT,
            alert_sent BOOLEAN DEFAULT FALSE
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS defacement_popups (
            id SERIAL PRIMARY KEY,
            target_id INTEGER,
            url TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            popup_screenshot_path TEXT,
            is_defaced BOOLEAN DEFAULT FALSE,
            analysis_summary TEXT
        );
        """)
    else:
        # SQLite dialect
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS defacement_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_id INTEGER,
            url TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            similarity_score REAL,
            is_defaced INTEGER DEFAULT 0,
            confidence INTEGER DEFAULT 0,
            change_type TEXT,
            analysis_summary TEXT,
            screenshot_path TEXT,
            diff_path TEXT,
            popup_screenshot_path TEXT,
            status TEXT DEFAULT 'SUCCESS',
            error_message TEXT
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS defacement_incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_id INTEGER,
            url TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            change_type TEXT,
            confidence INTEGER DEFAULT 0,
            summary TEXT,
            alert_sent INTEGER DEFAULT 0
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS defacement_popups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_id INTEGER,
            url TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            popup_screenshot_path TEXT,
            is_defaced INTEGER DEFAULT 0,
            analysis_summary TEXT
        );
        """)

    conn.commit()
    cursor.close()
    conn.close()
    logger.info(f"Database schema initialized using {db_type.upper()}.")

def add_log(target_id: int, url: str, similarity_score: float, is_defaced: bool, 
            confidence: int, change_type: str, analysis_summary: str, 
            screenshot_path: str = "", diff_path: str = "", 
            popup_screenshot_path: str = "", status: str = "SUCCESS", 
            error_message: str = "") -> int:
    """
    Inserts a monitoring execution record into the defacement_logs table.
    """
    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now()
    
    placeholder = "%s" if db_type == "postgres" else "?"
    query = f"""
    INSERT INTO defacement_logs 
    (target_id, url, timestamp, similarity_score, is_defaced, confidence, change_type, analysis_summary, screenshot_path, diff_path, popup_screenshot_path, status, error_message)
    VALUES ({', '.join([placeholder]*13)})
    """
    
    is_defaced_val = bool(is_defaced) if db_type == "postgres" else (1 if is_defaced else 0)
    
    params = (
        target_id, url, now, similarity_score, is_defaced_val, 
        confidence, change_type, analysis_summary, screenshot_path, 
        diff_path, popup_screenshot_path, status, error_message
    )
    
    cursor.execute(query, params)
    log_id = cursor.lastrowid if db_type == "sqlite" else None
    conn.commit()
    cursor.close()
    conn.close()
    return log_id

def add_incident(target_id: int, url: str, change_type: str, confidence: int, summary: str, alert_sent: bool = True) -> int:
    """
    Records a verified defacement incident in defacement_incidents table.
    """
    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now()
    
    placeholder = "%s" if db_type == "postgres" else "?"
    query = f"""
    INSERT INTO defacement_incidents 
    (target_id, url, timestamp, change_type, confidence, summary, alert_sent)
    VALUES ({', '.join([placeholder]*7)})
    """
    alert_sent_val = bool(alert_sent) if db_type == "postgres" else (1 if alert_sent else 0)
    params = (target_id, url, now, change_type, confidence, summary, alert_sent_val)
    cursor.execute(query, params)
    incident_id = cursor.lastrowid if db_type == "sqlite" else None
    conn.commit()
    cursor.close()
    conn.close()
    return incident_id

def add_popup_log(target_id: int, url: str, popup_screenshot_path: str, is_defaced: bool = False, analysis_summary: str = "") -> int:
    """
    Records an isolated popup capture into defacement_popups table.
    """
    conn, db_type = get_db_connection()
    cursor = conn.cursor()
    now = datetime.now()
    
    placeholder = "%s" if db_type == "postgres" else "?"
    query = f"""
    INSERT INTO defacement_popups 
    (target_id, url, timestamp, popup_screenshot_path, is_defaced, analysis_summary)
    VALUES ({', '.join([placeholder]*6)})
    """
    is_defaced_val = bool(is_defaced) if db_type == "postgres" else (1 if is_defaced else 0)
    params = (target_id, url, now, popup_screenshot_path, is_defaced_val, analysis_summary)
    cursor.execute(query, params)
    popup_id = cursor.lastrowid if db_type == "sqlite" else None
    conn.commit()
    cursor.close()
    conn.close()
    return popup_id

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
    print("Database initialization successful.")
