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
    print("=" * 60)
    print("ScreenScout Database Cleanup & Maintenance")
    print("=" * 60)
    
    res = clean_database()
    stats = res.get("db_stats", {})

    print("\n" + "=" * 60)
    print("📊 Database Cleanup Outcome Statistics")
    print("=" * 60)
    print("🧹 Purged Outdated Records:")
    print(f"   • Expired Schedules Removed : {res.get('deleted_schedules', 0):,}")
    print(f"   • Outdated Movies Removed   : {res.get('deleted_movies', 0):,}")
    
    print("\n💾 Live Database Snapshot (Post-Cleanup):")
    print(f"   • Active Movies Catalog     : {stats.get('total_movies', 0):,} ({stats.get('now_showing_movies', 0):,} Now Showing, {stats.get('coming_soon_movies', 0):,} Coming Soon)")
    print(f"   • Active Showtime Schedules : {stats.get('total_schedules', 0):,}")
    print(f"   • Cinema Locations          : {stats.get('total_cinemas', 0):,}")
    
    print("\n⚡ Backend Invalidation:")
    invalidate_backend_cache()
    print("============================================================\n")


if __name__ == "__main__":
    main()

