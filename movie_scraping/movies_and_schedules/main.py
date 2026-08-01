import asyncio
from dataclasses import asdict
import json
import sys
from pathlib import Path

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
from clean.db_cleaner import clean_database


async def main():
    print("Starting scraping tasks for Golden Village and Shaw Theatre...")

    # 1. Run async scraping tasks
    results = await asyncio.gather(
        scrape_golden_village(),
        scrape_shaw_theatre(),
        return_exceptions=True,
    )

    gv_res, shaw_res = results

    if isinstance(gv_res, Exception):
        print(f"[Golden Village] Scraping error: {gv_res}")
        gv_raw_movies, gv_raw_schedules = [], []
    else:
        gv_raw_movies, gv_raw_schedules = gv_res

    if isinstance(shaw_res, Exception):
        print(f"[Shaw Theatre] Scraping error: {shaw_res}")
        shaw_raw_movies, shaw_raw_schedules = [], []
    else:
        shaw_raw_movies, shaw_raw_schedules = shaw_res

    print(f"\nScraped {len(gv_raw_movies)} Golden Village movies raw.")
    print(f"Scraped {len(shaw_raw_movies)} Shaw Theatre movies raw.")

    # 2. Parse movies and schedules
    gv_parsed_movies = parse_gv_movies(gv_raw_movies)
    shaw_parsed_movies = parse_shaw_movies(shaw_raw_movies)

    gv_parsed_schedules = parse_gv_schedules(gv_raw_schedules)
    shaw_parsed_schedules = parse_shaw_schedules(shaw_raw_schedules)

    all_parsed_movies = gv_parsed_movies + shaw_parsed_movies
    all_parsed_schedules = gv_parsed_schedules + shaw_parsed_schedules

    print(f"\nParsed {len(all_parsed_movies)} total movies (GV: {len(gv_parsed_movies)}, Shaw: {len(shaw_parsed_movies)}).")
    print(f"Parsed {len(all_parsed_schedules)} total schedules (GV: {len(gv_parsed_schedules)}, Shaw: {len(shaw_parsed_schedules)}).")

    # 3. Save parsed schedules to outputs directory
    output_dir = (SCRAPING_DIR / ".." / "outputs").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "gv_schedules.json", "w", encoding="utf-8") as f:
        json.dump([asdict(s) for s in gv_parsed_schedules], f, indent=4, default=str, ensure_ascii=False)

    with open(output_dir / "shaw_schedules.json", "w", encoding="utf-8") as f:
        json.dump([asdict(s) for s in shaw_parsed_schedules], f, indent=4, default=str, ensure_ascii=False)

    # 4. Insert/update parsed movies and schedules into PostgreSQL
    if all_parsed_movies:
        try:
            saved_movies = save_movies(all_parsed_movies)
            print(f"\nInserted/updated {saved_movies} movies in database.")
        except Exception as e:
            print(f"\nMovie database write skipped or failed: {e}")

    if all_parsed_schedules:
        try:
            saved_schedules = save_schedules(all_parsed_schedules)
            print(f"Inserted/updated {saved_schedules} schedules in database.")
        except Exception as e:
            print(f"Schedule database write skipped or failed: {e}")

    # 5. Clean outdated schedules and movies from PostgreSQL
    try:
        cleanup_stats = clean_database()
        print(f"\nDatabase cleanup completed: {cleanup_stats['deleted_schedules']} expired schedules, {cleanup_stats['deleted_movies']} outdated movies cleaned.")
    except Exception as e:
        print(f"\nDatabase cleanup skipped or failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
