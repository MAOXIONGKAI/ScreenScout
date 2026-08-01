import sys
from pathlib import Path

# Ensure local imports work cleanly regardless of CWD
CLEAN_DIR = Path(__file__).resolve().parent
if str(CLEAN_DIR) not in sys.path:
    sys.path.insert(0, str(CLEAN_DIR))

from db_cleaner import clean_database


def main():
    print("Starting database cleanup task...")
    res = clean_database()
    print(f"\nCleanup task completed successfully:")
    print(f"- Expired schedules removed: {res['deleted_schedules']}")
    print(f"- Outdated movies removed: {res['deleted_movies']}")


if __name__ == "__main__":
    main()
