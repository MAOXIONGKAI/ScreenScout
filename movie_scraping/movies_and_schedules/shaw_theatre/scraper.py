import asyncio
from dataclasses import asdict
from datetime import datetime, timedelta
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import httpx
from playwright.async_api import async_playwright

try:
    from .parser import parse_movies, parse_schedules
except ImportError:
    from parser import parse_movies, parse_schedules

# ============================================================
# Configuration & Constants
# ============================================================
OUTPUT_DIR = (Path(__file__).resolve().parent.parent.parent / "outputs").resolve()

SG_TZ = ZoneInfo("Asia/Singapore")
BASE_URL = "https://shaw.sg"
FILM_INFO_API = f"{BASE_URL}/internal/get_movie_release?id="

SEM = asyncio.Semaphore(5)


# ============================================================
# Scraper API Functions
# ============================================================
async def fetch_movie(client: httpx.AsyncClient, movie_id: str) -> Optional[Dict[str, Any]]:
    """Fetch complete movie information from Shaw internal API."""
    async with SEM:
        try:
            response = await client.get(FILM_INFO_API + str(movie_id))
            response.raise_for_status()
            data = response.json()
            if not data:
                print(f"[{movie_id}] Failed to retrieve movie info.")
                return None
            return data
        except Exception as e:
            print(f"[{movie_id}] Exception fetching info: {e}")
            return None


async def fetch_schedules(context: Any, movie_id: str) -> List[Any]:
    """Fetch all available showtime schedules for a movie across consecutive dates."""
    all_schedules = []
    current_date = datetime.now(SG_TZ).date()

    while True:
        date_str = current_date.strftime("%Y-%m-%d")
        async with SEM:
            response = await context.request.get(
                f"{BASE_URL}/internal/get_show_times?date={date_str}&movieId={movie_id}&locationId=0&promotionId=0",
                headers={
                    "x-api-forward-to": "internal",
                    "x-app": "PWSM",
                },
            )

        data = await response.json()
        if not data:
            break

        if isinstance(data, list):
            all_schedules.extend(data)
        else:
            all_schedules.append(data)

        current_date += timedelta(days=1)

    return all_schedules


# ============================================================
# Main Scraper Pipeline
# ============================================================
async def scrape_shaw_theatre() -> Tuple[List[Dict[str, Any]], List[Any]]:
    """Main async pipeline to scrape Shaw Theatre movies and showtimes."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, channel="chrome")
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
            bypass_csp=True,
        )
        page = await context.new_page()

        print("Opening Shaw Theatre...")
        try:
            for attempt in range(3):
                try:
                    await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=45000)
                    break
                except Exception as e:
                    print(f"Shaw navigation attempt {attempt + 1} failed: {e}")
                    if attempt == 2:
                        print("Shaw Theatre site unreachable. Skipping Shaw scrape.")
                        await browser.close()
                        return [], []
        except Exception as e:
            print(f"Shaw scraper error: {e}")
            await browser.close()
            return [], []

        release_ids = await page.locator("a[href^='/movie-details/']").evaluate_all(
            """els => [...new Set(els.map(e => e.getAttribute('href').split('/').pop()))]"""
        )

        cookies = await context.cookies()
        cookie_dict = {c["name"]: c["value"] for c in cookies}

        user_agent = await page.evaluate("navigator.userAgent")
        headers = {
            "User-Agent": user_agent,
            "Referer": f"{BASE_URL}/movie-details/",
            "Accept": "application/json, text/plain, */*",
            "x-api-forward-to": "internal",
            "x-app": "PWSM",
        }

        async with httpx.AsyncClient(timeout=30, headers=headers, cookies=cookie_dict) as client:
            print(f"Fetching details for {len(release_ids)} movies...")
            movies = await asyncio.gather(
                *(fetch_movie(client, release_id) for release_id in release_ids),
                return_exceptions=True,
            )

            valid_movies = [m for m in movies if isinstance(m, dict)]
            print(f"Successfully fetched {len(valid_movies)} movie details.")

            movie_ids = [m["movieId"] for m in valid_movies if "movieId" in m]

            print("Fetching schedules...")
            schedules = await asyncio.gather(
                *(fetch_schedules(context, movie_id) for movie_id in movie_ids),
                return_exceptions=True,
            )

        await browser.close()

        valid_schedules = [s for s in schedules if isinstance(s, (dict, list)) and s]

        return valid_movies, valid_schedules


# ============================================================
# Entry Point
# ============================================================
if __name__ == "__main__":
    valid_movies, valid_schedules = asyncio.run(scrape_shaw_theatre())

    # Parse raw dictionaries into dataclasses
    parsed_movies = parse_movies(valid_movies)
    parsed_schedules = parse_schedules(valid_schedules)

    # Ensure outputs directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    movies_path = OUTPUT_DIR / "shaw_movies.json"
    schedules_path = OUTPUT_DIR / "shaw_schedules.json"

    # Save parsed JSON files
    with open(movies_path, "w", encoding="utf-8") as f:
        json.dump([asdict(m) for m in parsed_movies], f, indent=4, ensure_ascii=False, default=str)

    with open(schedules_path, "w", encoding="utf-8") as f:
        json.dump([asdict(s) for s in parsed_schedules], f, indent=4, ensure_ascii=False, default=str)

    print("\n" + "=" * 50)
    print("Shaw Theatre Scraping Completed (Main Execution)")
    print("=" * 50)
    print(f"Logged parsed JSONs to output folder: {OUTPUT_DIR}")
    print(f"- {movies_path.name}: {len(parsed_movies)} movies")
    print(f"- {schedules_path.name}: {len(parsed_schedules)} schedules")
    print("=" * 50 + "\n")