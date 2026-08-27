import argparse
import asyncio
from dataclasses import asdict
from datetime import datetime
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

# Ensure local imports work cleanly regardless of CWD
SCRAPING_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRAPING_DIR.parent
if str(SCRAPING_DIR) not in sys.path:
    sys.path.insert(0, str(SCRAPING_DIR))
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from golden_village.scraper import scrape_golden_village
from golden_village.parser import parse_movies as parse_gv_movies, parse_schedules as parse_gv_schedules
from shaw_theatre.scraper import scrape_shaw_theatre
from shaw_theatre.parser import parse_movies as parse_shaw_movies, parse_schedules as parse_shaw_schedules
from db_writer import save_movies, save_schedules

SG_TZ = ZoneInfo("Asia/Singapore")


async def main():
    parser = argparse.ArgumentParser(description="Scrape movies and showtimes for Golden Village and/or Shaw Theatre.")
    parser.add_argument(
        "--provider",
        choices=["all", "gv", "shaw"],
        default="all",
        help="Scrape specific provider ('gv', 'shaw', or 'all'). Default: 'all'",
    )
    args = parser.parse_args()
    provider = args.provider.lower()

    run_gv = provider in ("all", "gv")
    run_shaw = provider in ("all", "shaw")

    print("=" * 50)
    print(f"ScreenScout Movie & Schedule Scraper ({provider.upper()})")
    print("=" * 50)

    tasks = []
    task_keys = []
    if run_gv:
        tasks.append(scrape_golden_village())
        task_keys.append("gv")
    if run_shaw:
        tasks.append(scrape_shaw_theatre())
        task_keys.append("shaw")

    results = await asyncio.gather(*tasks, return_exceptions=True)

    gv_raw_movies, gv_raw_schedules = [], []
    shaw_raw_movies, shaw_raw_schedules = [], []

    for key, res in zip(task_keys, results):
        if key == "gv":
            if isinstance(res, Exception):
                print(f"[Golden Village] Scraping error: {res}")
            elif res:
                gv_raw_movies, gv_raw_schedules = res
        elif key == "shaw":
            if isinstance(res, Exception):
                print(f"[Shaw Theatre] Scraping error: {res}")
            elif res:
                shaw_raw_movies, shaw_raw_schedules = res

    # Parse movies and schedules
    gv_parsed_movies = parse_gv_movies(gv_raw_movies) if run_gv else []
    shaw_parsed_movies = parse_shaw_movies(shaw_raw_movies) if run_shaw else []

    gv_parsed_schedules = parse_gv_schedules(gv_raw_schedules) if run_gv else []
    shaw_parsed_schedules = parse_shaw_schedules(shaw_raw_schedules) if run_shaw else []

    all_parsed_movies = gv_parsed_movies + shaw_parsed_movies
    all_parsed_schedules = gv_parsed_schedules + shaw_parsed_schedules

    today = datetime.now(SG_TZ).date()

    gv_showing = sum(1 for m in gv_parsed_movies if m.release_date <= today)
    gv_coming = len(gv_parsed_movies) - gv_showing

    shaw_showing = sum(1 for m in shaw_parsed_movies if m.release_date <= today)
    shaw_coming = len(shaw_parsed_movies) - shaw_showing

    total_showing = gv_showing + shaw_showing
    total_coming = gv_coming + shaw_coming

    gv_sched_movies = len(set(s.movie_id for s in gv_parsed_schedules))
    shaw_sched_movies = len(set(s.movie_id for s in shaw_parsed_schedules))
    all_sched_movies = len(set(s.movie_id for s in all_parsed_schedules))

    print("\n" + "=" * 50)
    print("Scraping & Parsing Summary")
    print("=" * 50)
    print(f"Movies   : {len(all_parsed_movies)} total ({total_showing} showing now, {total_coming} coming soon)")
    if run_gv:
        print(f"  - Golden Village : {len(gv_parsed_movies)} movies ({gv_showing} showing now, {gv_coming} coming soon)")
    if run_shaw:
        print(f"  - Shaw Theatre   : {len(shaw_parsed_movies)} movies ({shaw_showing} showing now, {shaw_coming} coming soon)")

    print(f"\nSchedules: {len(all_parsed_schedules)} total (across {all_sched_movies} movies)")
    if run_gv:
        print(f"  - Golden Village : {len(gv_parsed_schedules)} schedules (across {gv_sched_movies} movies)")
    if run_shaw:
        print(f"  - Shaw Theatre   : {len(shaw_parsed_schedules)} schedules (across {shaw_sched_movies} movies)")

    # Save parsed movies and schedules to outputs directory
    output_dir = (SCRAPING_DIR / ".." / "outputs").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if gv_parsed_movies:
        with open(output_dir / "gv_movies.json", "w", encoding="utf-8") as f:
            json.dump([asdict(m) for m in gv_parsed_movies], f, indent=4, default=str, ensure_ascii=False)

    if shaw_parsed_movies:
        with open(output_dir / "shaw_movies.json", "w", encoding="utf-8") as f:
            json.dump([asdict(m) for m in shaw_parsed_movies], f, indent=4, default=str, ensure_ascii=False)

    if gv_parsed_schedules:
        with open(output_dir / "gv_schedules.json", "w", encoding="utf-8") as f:
            json.dump([asdict(s) for s in gv_parsed_schedules], f, indent=4, default=str, ensure_ascii=False)

    if shaw_parsed_schedules:
        with open(output_dir / "shaw_schedules.json", "w", encoding="utf-8") as f:
            json.dump([asdict(s) for s in shaw_parsed_schedules], f, indent=4, default=str, ensure_ascii=False)

    # Insert/update parsed movies and schedules into PostgreSQL
    print("\n" + "=" * 50)
    print("Database Persistence")
    print("=" * 50)

    if all_parsed_movies:
        try:
            saved_movies = save_movies(all_parsed_movies)
            print(f"Movies database    : {saved_movies} movies inserted/updated successfully.")
        except Exception as e:
            print(f"Movies database    : write skipped or failed ({e})")

    if all_parsed_schedules:
        try:
            saved_schedules = save_schedules(all_parsed_schedules)
            print(f"Schedules database : {saved_schedules} schedules inserted/updated successfully.")
        except Exception as e:
            print(f"Schedules database : write skipped or failed ({e})")

    # Invalidate Redis Movie Cache in Backend if active
    try:
        import urllib.request
        api_url = os.getenv("BACKEND_API_URL", "http://localhost:8080")
        req = urllib.request.Request(f"{api_url}/api/cache/movies/invalidate", method="POST", data=b"")
        with urllib.request.urlopen(req, timeout=2) as resp:
            if resp.status == 200:
                print("Cache Invalidation  : Redis movie cache invalidated successfully.")
    except Exception:
        pass

    print("=" * 50 + "\n")

    # Monitor & Trigger Subscriptions
    try:
        from monitor.subscription_checker import check_and_trigger_subscriptions
        check_and_trigger_subscriptions()
    except Exception as e:
        print(f"[Subscription Monitor Warning] Could not run subscription checker: {e}")


if __name__ == "__main__":
    asyncio.run(main())
