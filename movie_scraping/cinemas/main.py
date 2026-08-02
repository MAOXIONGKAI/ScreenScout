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

    print("=" * 50)
    print(f"ScreenScout Cinema Location Scraper ({provider.upper()})")
    print("=" * 50)

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
                print(f"[Shaw Theatre] Scraper failed: {res}")
            else:
                shaw_res = res
        elif key == "gv":
            if isinstance(res, Exception):
                print(f"[Golden Village] Scraper failed: {res}")
            else:
                gv_res = res

    parsed_shaw_cinemas = parse_shaw_cinemas(shaw_res) if run_shaw else []
    parsed_gv_cinemas = parse_gv_cinemas(gv_res) if run_gv else []

    output_dir = (CINEMAS_DIR / ".." / "outputs").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 50)
    print("Cinema Location Summary")
    print("=" * 50)

    if run_shaw:
        with open(output_dir / "shaw_cinemas.json", "w", encoding="utf-8") as f:
            json.dump([asdict(c) for c in parsed_shaw_cinemas], f, indent=4, default=str, ensure_ascii=False)
        print(f"Shaw Theatre   : {len(parsed_shaw_cinemas)} cinema locations parsed")

    if run_gv:
        with open(output_dir / "gv_cinemas.json", "w", encoding="utf-8") as f:
            json.dump([asdict(c) for c in parsed_gv_cinemas], f, indent=4, default=str, ensure_ascii=False)
        print(f"Golden Village : {len(parsed_gv_cinemas)} cinema locations parsed")

    # Save to PostgreSQL database if connection is available
    all_parsed_cinemas = parsed_shaw_cinemas + parsed_gv_cinemas
    print("\n" + "=" * 50)
    print("Database Persistence")
    print("=" * 50)

    if all_parsed_cinemas:
        try:
            saved_count = save_cinemas(all_parsed_cinemas)
            print(f"Cinemas database : {saved_count} cinemas inserted/updated successfully.")
        except Exception as e:
            print(f"Cinemas database : write skipped or failed ({e})")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
