import os
import sqlite3
from datetime import datetime

DB_PATH = "data/monitoring.db"

def get_db_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema if it doesn't already exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Target websites table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS targets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 2. Monitoring log records table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS monitoring_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        target_id INTEGER NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        similarity_score REAL,
        is_defaced INTEGER DEFAULT 0,
        confidence INTEGER DEFAULT 0,
        change_type TEXT,
        analysis_summary TEXT,
        screenshot_path TEXT,
        diff_path TEXT,
        popup_path TEXT,
        status TEXT NOT NULL,
        error_message TEXT,
        FOREIGN KEY (target_id) REFERENCES targets (id) ON DELETE CASCADE
    )
    """)

    cursor.execute("PRAGMA table_info(monitoring_logs)")
    log_columns = [row[1] for row in cursor.fetchall()]
    if "popup_path" not in log_columns:
        cursor.execute("ALTER TABLE monitoring_logs ADD COLUMN popup_path TEXT DEFAULT ''")

    # 3. Settings table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    # Default settings seed
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('webhook_url', '')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('webhook_payload_format', 'n8n')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('webhook_trigger_on', 'defacement')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('check_interval', '5')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('check_interval_unit', 'minutes')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('similarity_threshold', '0.98')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('use_llm', 'true')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('browser_engine', 'firefox')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('ollama_url', 'http://localhost:11434')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('ollama_model', 'llama3.2-vision')")

    conn.commit()
    conn.close()

def add_target(url: str, name: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO targets (url, name) VALUES (?, ?)", (url, name))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        cursor.execute("SELECT id FROM targets WHERE url = ?", (url,))
        row = cursor.fetchone()
        if row:
            cursor.execute("UPDATE targets SET name = ? WHERE id = ?", (name, row['id']))
            conn.commit()
            return row['id']
        return None
    finally:
        conn.close()

def update_target(target_id: int, url: str, name: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE targets SET url = ?, name = ? WHERE id = ?", (url, name, target_id))
    conn.commit()
    conn.close()

def get_targets():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, url, name, is_active, created_at FROM targets ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_target(target_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, url, name, is_active, created_at FROM targets WHERE id = ?", (target_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_target_status(target_id: int, is_active: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE targets SET is_active = ? WHERE id = ?", (is_active, target_id))
    conn.commit()
    conn.close()

def delete_target(target_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM targets WHERE id = ?", (target_id,))
    cursor.execute("DELETE FROM monitoring_logs WHERE target_id = ?", (target_id,))
    conn.commit()
    conn.close()

def add_log(
    target_id: int,
    similarity_score: float,
    is_defaced: int,
    confidence: int,
    change_type: str,
    analysis_summary: str,
    screenshot_path: str,
    diff_path: str,
    status: str,
    error_message: str = None,
    popup_path: str = ""
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO monitoring_logs (
        target_id, similarity_score, is_defaced, confidence, change_type,
        analysis_summary, screenshot_path, diff_path, popup_path, status, error_message, timestamp
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        target_id, similarity_score, is_defaced, confidence, change_type,
        analysis_summary, screenshot_path, diff_path, popup_path, status, error_message, datetime.now().isoformat()
    ))
    log_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return log_id

def get_logs(target_id: int = None, limit: int = 50):
    conn = get_db_connection()
    cursor = conn.cursor()
    if target_id:
        cursor.execute("""
            SELECT l.*, t.name as target_name, t.url as target_url
            FROM monitoring_logs l
            JOIN targets t ON l.target_id = t.id
            WHERE l.target_id = ?
            ORDER BY l.timestamp DESC LIMIT ?
        """, (target_id, limit))
    else:
        cursor.execute("""
            SELECT l.*, t.name as target_name, t.url as target_url
            FROM monitoring_logs l
            JOIN targets t ON l.target_id = t.id
            ORDER BY l.timestamp DESC LIMIT ?
        """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_latest_log(target_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM monitoring_logs
        WHERE target_id = ? AND status = 'SUCCESS'
        ORDER BY timestamp DESC LIMIT 1
    """, (target_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_settings():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM settings")
    rows = cursor.fetchall()
    conn.close()
    return {row['key']: row['value'] for row in rows}

def save_settings(settings_dict: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    for key, value in settings_dict.items():
        cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database schema initialized.")
