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
    print("Starting cinema scraping tasks for Shaw Theatre and Golden Village...")

    results = await asyncio.gather(
        scrape_shaw_cinemas(),
        scrape_golden_village_cinemas(),
        return_exceptions=True,
    )

    shaw_res, gv_res = results

    if isinstance(shaw_res, Exception):
        print(f"Shaw scraper failed: {shaw_res}")
        shaw_res = []

    if isinstance(gv_res, Exception):
        print(f"Golden Village scraper failed: {gv_res}")
        gv_res = []

    parsed_shaw_cinemas = parse_shaw_cinemas(shaw_res)
    parsed_gv_cinemas = parse_gv_cinemas(gv_res)

    output_dir = (CINEMAS_DIR / ".." / "outputs").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "shaw_cinemas.json", "w", encoding="utf-8") as f:
        json.dump([asdict(c) for c in parsed_shaw_cinemas], f, indent=4, default=str, ensure_ascii=False)

    with open(output_dir / "gv_cinemas.json", "w", encoding="utf-8") as f:
        json.dump([asdict(c) for c in parsed_gv_cinemas], f, indent=4, default=str, ensure_ascii=False)

    print(f"\nScraped {len(shaw_res)} Shaw cinema locations.")
    print(f"Parsed {len(parsed_shaw_cinemas)} Shaw cinema locations.")
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
