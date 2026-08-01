import asyncio
import sys
from pathlib import Path

# Ensure local imports work cleanly regardless of CWD
SCRAPING_DIR = Path(__file__).resolve().parent
if str(SCRAPING_DIR) not in sys.path:
    sys.path.insert(0, str(SCRAPING_DIR))

from golden_village.scraper import scrape_golden_village
from golden_village.parser import parse_movies as parse_gv_movies
from shaw_theatre.scraper import scrape_shaw_theatre
from shaw_theatre.parser import parse_movies as parse_shaw_movies
from db_writer import save_movies


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
        gv_raw_movies = []
    else:
        gv_raw_movies, gv_schedules = gv_res

    if isinstance(shaw_res, Exception):
        print(f"[Shaw Theatre] Scraping error: {shaw_res}")
        shaw_raw_movies = []
    else:
        shaw_raw_movies, shaw_schedules = shaw_res

    print(f"\nScraped {len(gv_raw_movies)} Golden Village movies raw.")
    print(f"Scraped {len(shaw_raw_movies)} Shaw Theatre movies raw.")

    # 2. Parse the scraped movies
    gv_parsed_movies = parse_gv_movies(gv_raw_movies)
    shaw_parsed_movies = parse_shaw_movies(shaw_raw_movies)

    all_parsed_movies = gv_parsed_movies + shaw_parsed_movies
    print(f"\nParsed {len(all_parsed_movies)} total movies (GV: {len(gv_parsed_movies)}, Shaw: {len(shaw_parsed_movies)}).")

    # 3. Insert/update parsed movies into PostgreSQL
    if all_parsed_movies:
        saved_count = save_movies(all_parsed_movies)
        print(f"\nPipeline completed: {saved_count} movies inserted/updated in database.")
    else:
        print("\nNo parsed movies to insert.")


if __name__ == "__main__":
    asyncio.run(main())
