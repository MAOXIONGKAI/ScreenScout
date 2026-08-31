import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent

DEFAULT_BOT_TOKEN = "8741735560:AAHEXG5BgqrDFZmPHd4ADL54P_O-RGt6unQ"

# Load .env file from workspace root with override
load_dotenv(ROOT_DIR / ".env", override=True)

HOST = os.getenv("NOTIFICATION_SERVICE_HOST", "0.0.0.0")
PORT = int(os.getenv("NOTIFICATION_SERVICE_PORT", "8085"))
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "8741735560:AAFa9GjTfZf2u11aZ9oK8L7M6N5P4Q3R2S1":
    TELEGRAM_BOT_TOKEN = DEFAULT_BOT_TOKEN

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/screenscout")
CACHE_FILE = BASE_DIR / "telegram_users_cache.json"
