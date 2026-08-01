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


async def main():
    print("Starting cinema scraping tasks...")

    shaw_res = await scrape_shaw_cinemas()
    parsed_shaw_cinemas = parse_shaw_cinemas(shaw_res)

    output_dir = (CINEMAS_DIR / ".." / "outputs").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(output_dir / "shaw_theatre_cinemas.json", "w", encoding="utf-8") as f:
        json.dump([asdict(c) for c in parsed_shaw_cinemas], f, indent=4, default=str)

    print(f"Scraped {len(shaw_res)} Shaw cinema locations.")
    print(f"Parsed {len(parsed_shaw_cinemas)} Shaw cinema locations.")


if __name__ == "__main__":
    asyncio.run(main())
