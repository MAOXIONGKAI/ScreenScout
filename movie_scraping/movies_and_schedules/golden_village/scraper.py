import asyncio
from dataclasses import asdict
from datetime import datetime
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Set, Tuple
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
BASE_URL = "https://www.gv.com.sg"

FILM_INFO_API = f"{BASE_URL}/.gv-api/filminfo"
SCHEDULE_API = f"{BASE_URL}/.gv-api/sessionforfilm"
SHOWING_NOW_API = f"{BASE_URL}/.gv-api/homenowshowing"
COMING_SOON_API = f"{BASE_URL}/.gv-api/homecomingsoon"
ADVANCE_SALES_API = f"{BASE_URL}/.gv-api/homeadvancesales"

SEM = asyncio.Semaphore(5)
HEADLESS = os.getenv("HEADLESS", "true").lower() in ("true", "1", "yes")

# Auto-start virtual display on Linux if running in non-headless mode
if not HEADLESS and sys.platform.startswith("linux"):
    try:
        from pyvirtualdisplay import Display
        display = Display(visible=0, size=(1280, 720))
        display.start()
    except Exception as e:
        print(f"[VirtualDisplay] Warning: {e}")


# ============================================================
# Utilities
# ============================================================
def extract_film_codes(data: Any) -> Set[str]:
    """Recursively search a JSON object/list for `filmCd` fields."""
    result: Set[str] = set()

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            film_cd = obj.get("filmCd")
            if film_cd is not None:
                result.add(str(film_cd))
            for value in obj.values():
                walk(value)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(data)
    return result


async def post_json(client: httpx.AsyncClient, url: str, payload: Optional[Dict[str, Any]] = None) -> Any:
    """Generic HTTP POST helper guarded by semaphore."""
    async with SEM:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()


# ============================================================
# Scraper API Functions
# ============================================================
async def fetch_movie(client: httpx.AsyncClient, movie_id: str) -> Optional[Dict[str, Any]]:
    """Fetch complete movie information from GV filminfo API."""
    try:
        data = await post_json(client, FILM_INFO_API, {"filmCode": movie_id})
        if not data.get("success"):
            print(f"[{movie_id}] Error: {data.get('errorMessage')}")
            return None
        return data.get("data")
    except Exception as e:
        print(f"[{movie_id}] Exception fetching info: {e}")
        return None


async def fetch_movie_ids(client: httpx.AsyncClient) -> Dict[str, Set[str]]:
    """Fetch movie IDs from Now Showing, Coming Soon, and Advance Sales endpoints."""
    print("Fetching showing now movies...")
    try:
        showing_now_data = await post_json(client, SHOWING_NOW_API)
    except Exception as e:
        print(f"Warning fetching showing now movies: {e}")
        showing_now_data = {}

    print("Fetching coming soon movies...")
    try:
        coming_soon_data = await post_json(client, COMING_SOON_API)
    except Exception as e:
        print(f"Warning fetching coming soon movies: {e}")
        coming_soon_data = {}

    print("Fetching advance sales movies...")
    try:
        advance_sales_data = await post_json(client, ADVANCE_SALES_API)
    except Exception as e:
        print(f"Warning fetching advance sales movies: {e}")
        advance_sales_data = {}

    showing_now_ids = extract_film_codes(showing_now_data)
    coming_soon_ids = extract_film_codes(coming_soon_data)
    advance_sales_ids = extract_film_codes(advance_sales_data)
    all_ids = showing_now_ids | coming_soon_ids | advance_sales_ids

    print(f"Showing now: {len(showing_now_ids)}")
    print(f"Advance sales: {len(advance_sales_ids)}")
    print(f"Coming soon: {len(coming_soon_ids)}")
    print(f"Total unique movies: {len(all_ids)}")

    return {
        "showing_now": showing_now_ids,
        "coming_soon": coming_soon_ids,
        "advance_sales": advance_sales_ids,
        "all": all_ids,
    }


async def fetch_schedules(client: httpx.AsyncClient, movie_id: str) -> Optional[Dict[str, Any]]:
    """Fetch showtime schedule for a movie from GV sessionforfilm API."""
    try:
        data = await post_json(client, SCHEDULE_API, {"filmCode": movie_id})
        if not data:
            print(f"[{movie_id}] Failed to retrieve schedule info.")
            return None
        return data
    except Exception as e:
        print(f"[{movie_id}] Schedule exception: {e}")
        return None


# ============================================================
# Main Scraper Pipeline
# ============================================================
async def scrape_golden_village() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Main async pipeline to scrape Golden Village raw movies and showtimes."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
            bypass_csp=True,
        )
        page = await context.new_page()

        print("Opening Golden Village...")
        await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)

        cookies = await context.cookies()
        cookie_dict = {c["name"]: c["value"] for c in cookies}
        user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"

        headers = {
            "User-Agent": user_agent,
            "Accept": "application/json, text/plain, */*",
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/",
            "x_developer": "ENOVAX",
        }

        async with httpx.AsyncClient(timeout=30, cookies=cookie_dict, headers=headers) as client:
            # 1. Fetch movie IDs
            id_groups = await fetch_movie_ids(client)
            all_movie_ids = id_groups["all"]

            # 2. Fetch movie details
            print(f"Fetching details for {len(all_movie_ids)} movies...")
            movies_res = await asyncio.gather(
                *(fetch_movie(client, m_id) for m_id in all_movie_ids),
                return_exceptions=True,
            )
            valid_movies = [m for m in movies_res if isinstance(m, dict)]
            print(f"Successfully fetched {len(valid_movies)} movie details.")

            # 3. Fetch schedules
            print("Fetching schedules...")
            schedules_res = await asyncio.gather(
                *(fetch_schedules(client, m_id) for m_id in all_movie_ids),
                return_exceptions=True,
            )
            valid_schedules = [s for s in schedules_res if isinstance(s, dict)]
            active_sched_movies = [s for s in valid_schedules if s.get("data") and s["data"].get("locations")]
            print(f"Successfully fetched schedules for {len(active_sched_movies)} movies.")

        await browser.close()

    return valid_movies, valid_schedules


# ============================================================
# Entry Point
# ============================================================
if __name__ == "__main__":
    valid_movies, valid_schedules = asyncio.run(scrape_golden_village())

    # Parse raw dictionaries into dataclasses
    parsed_movies = parse_movies(valid_movies)
    parsed_schedules = parse_schedules(valid_schedules)

    today = datetime.now(SG_TZ).date()
    showing_count = sum(1 for m in parsed_movies if m.release_date <= today)
    coming_count = len(parsed_movies) - showing_count
    sched_movies_count = len(set(s.movie_id for s in parsed_schedules))

    # Ensure outputs directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    movies_path = OUTPUT_DIR / "gv_movies.json"
    schedules_path = OUTPUT_DIR / "gv_schedules.json"

    # Save parsed JSON files
    with open(movies_path, "w", encoding="utf-8") as f:
        json.dump([asdict(m) for m in parsed_movies], f, indent=4, ensure_ascii=False, default=str)

    with open(schedules_path, "w", encoding="utf-8") as f:
        json.dump([asdict(s) for s in parsed_schedules], f, indent=4, ensure_ascii=False, default=str)

    print("\n" + "=" * 50)
    print("Golden Village Scraping Completed (Main Execution)")
    print("=" * 50)
    print(f"Showing now  : {showing_count}")
    print(f"Coming soon  : {coming_count}")
    print(f"Total movies : {len(parsed_movies)}")
    print(f"Schedules    : {len(parsed_schedules)} (across {sched_movies_count} movies)")
    print(f"Logged parsed JSONs to output folder: {OUTPUT_DIR}")
    print("=" * 50 + "\n")