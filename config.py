import os
from pathlib import Path

# Base workspace directory
BASE_DIR = Path(__file__).resolve().parent

# Load .env file manually if python-dotenv is not installed
env_file = BASE_DIR / ".env"
if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))

# PostgreSQL Database Configuration
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "website_defacement")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")

# Fallback SQLite DB path (used if PostgreSQL connection is unavailable)
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", str(BASE_DIR / "data" / "monitoring.db"))

# Ollama Multimodal Vision AI Configuration (e.g. running on client VM)
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "60"))

# Detection & Comparison Thresholds
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.98"))
PIXEL_DIFF_THRESHOLD = int(os.getenv("PIXEL_DIFF_THRESHOLD", "15"))

# Alerting Webhook Configuration
ALERT_WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL", "")

# Targets Configuration File
TARGETS_FILE = os.getenv("TARGETS_FILE", str(BASE_DIR / "targets.json"))

# Screenshots directory
SCREENSHOTS_DIR = BASE_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
