import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent

# Load .env file from workspace root
load_dotenv(ROOT_DIR / ".env")

HOST = os.getenv("NOTIFICATION_SERVICE_HOST", "0.0.0.0")
PORT = int(os.getenv("NOTIFICATION_SERVICE_PORT", "8085"))
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/screenscout")
CACHE_FILE = BASE_DIR / "telegram_users_cache.json"
