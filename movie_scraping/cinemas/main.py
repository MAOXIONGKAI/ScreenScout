import argparse
import asyncio
from dataclasses import asdict
import json
from pathlib import Path
import sys

CINEMAS_DIR = Path(__file__).resolve().parent
if str(CINEMAS_DIR) not in sys.path:
    sys.path.insert(0, str(CINEMAS_DIR))

from shaw_theatre.scraper import scrape_shaw_cinemas
from shaw_theatre.parser import parse_cinemas as parse_shaw_cinemas
from golden_village.scraper import scrape_golden_village_cinemas
from golden_village.parser import parse_cinemas as parse_gv_cinemas
from db_writer import save_cinemas


async def main():
    parser = argparse.ArgumentParser(description="Scrape cinema locations for Golden Village and/or Shaw Theatre.")
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

    print(f"Starting cinema scraping tasks for provider(s): {provider.upper()}...")

    shaw_res, gv_res = [], []
    tasks = []
    task_keys = []
    if run_shaw:
        tasks.append(scrape_shaw_cinemas())
        task_keys.append("shaw")
    if run_gv:
        tasks.append(scrape_golden_village_cinemas())
        task_keys.append("gv")

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for key, res in zip(task_keys, results):
        if key == "shaw":
            if isinstance(res, Exception):
                print(f"Shaw scraper failed: {res}")
            else:
                shaw_res = res
        elif key == "gv":
            if isinstance(res, Exception):
                print(f"Golden Village scraper failed: {res}")
            else:
                gv_res = res

    parsed_shaw_cinemas = parse_shaw_cinemas(shaw_res) if run_shaw else []
    parsed_gv_cinemas = parse_gv_cinemas(gv_res) if run_gv else []

    output_dir = (CINEMAS_DIR / ".." / "outputs").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if run_shaw:
        with open(output_dir / "shaw_cinemas.json", "w", encoding="utf-8") as f:
            json.dump([asdict(c) for c in parsed_shaw_cinemas], f, indent=4, default=str, ensure_ascii=False)
        print(f"\nScraped {len(shaw_res)} Shaw cinema locations.")
        print(f"Parsed {len(parsed_shaw_cinemas)} Shaw cinema locations.")

    if run_gv:
        with open(output_dir / "gv_cinemas.json", "w", encoding="utf-8") as f:
            json.dump([asdict(c) for c in parsed_gv_cinemas], f, indent=4, default=str, ensure_ascii=False)
        print(f"Scraped {len(gv_res)} Golden Village cinema locations.")
        print(f"Parsed {len(parsed_gv_cinemas)} Golden Village cinema locations.")

    # Save to PostgreSQL database if connection is available
    all_parsed_cinemas = parsed_shaw_cinemas + parsed_gv_cinemas
    if all_parsed_cinemas:
        try:
            saved_count = save_cinemas(all_parsed_cinemas)
            print(f"\nSuccessfully inserted/updated {saved_count} cinemas into the database.")
        except Exception as e:
            print(f"\nDatabase write skipped or failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
