import os
import sys
import urllib.request
from pathlib import Path

# Ensure local imports work cleanly regardless of CWD
CLEAN_DIR = Path(__file__).resolve().parent
if str(CLEAN_DIR) not in sys.path:
    sys.path.insert(0, str(CLEAN_DIR))

from db_cleaner import clean_database


def invalidate_backend_cache():
    api_url = os.getenv("BACKEND_API_URL", "http://localhost:8080")
    try:
        req = urllib.request.Request(f"{api_url}/api/cache/movies/invalidate", method="POST", data=b"")
        with urllib.request.urlopen(req, timeout=2) as resp:
            if resp.status == 200:
                print("- Redis movie cache invalidated successfully")
    except Exception:
        pass


def main():
    print("Starting database cleanup task...")
    res = clean_database()
    print(f"\nCleanup task completed successfully:")
    print(f"- Expired schedules removed: {res['deleted_schedules']}")
    print(f"- Outdated movies removed: {res['deleted_movies']}")
    invalidate_backend_cache()


if __name__ == "__main__":
    main()

