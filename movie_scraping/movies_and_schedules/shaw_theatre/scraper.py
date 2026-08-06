import asyncio
from dataclasses import asdict
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import sys
import re
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import httpx
from playwright.async_api import async_playwright

DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")

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
DEFAULT_HEADERS = {
    "x-api-forward-to": "internal",
    "x-app": "PWSM",
    "Referer": f"{BASE_URL}/movie-details/",
    "Accept": "application/json, text/plain, */*",
}

SEM = asyncio.Semaphore(10)
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
# Scraper API Functions
# ============================================================
async def fetch_movie(client: httpx.AsyncClient, movie_id: str) -> Optional[Dict[str, Any]]:
    """Fetch complete movie information from Shaw internal API with retries."""
    async with SEM:
        for attempt in range(3):
            try:
                response = await client.get(FILM_INFO_API + str(movie_id), headers=DEFAULT_HEADERS)
                if response.status_code in (400, 404):
                    return None
                response.raise_for_status()
                data = response.json()
                if isinstance(data, dict) and data:
                    return data
                if attempt == 2:
                    return None
            except Exception as e:
                if attempt == 2:
                    return None
                await asyncio.sleep(0.5 * (attempt + 1))
    return None


async def fetch_schedules(context: Any, movie_id: str) -> List[Any]:
    """Fetch all available showtime schedules for a movie across valid dates."""
    all_schedules = []

    # 1. Fetch available showtime dates for this movie via get_date_selectors API
    dates = []
    async with SEM:
        try:
            response = await context.request.get(
                f"{BASE_URL}/internal/get_date_selectors?movieId={movie_id}",
                headers=DEFAULT_HEADERS,
            )
            if response.status == 200:
                data = await response.json()
                if isinstance(data, list):
                    dates = [d.get("code") for d in data if isinstance(d, dict) and d.get("code")]
        except Exception as e:
            print(f"[{movie_id}] Exception fetching date selectors: {e}")

    # Fallback to checking next 7 days if get_date_selectors returned no dates
    if not dates:
        start_date = datetime.now(SG_TZ).date()
        dates = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    # 2. Fetch showtimes for each date without early termination
    for date_str in dates:
        async with SEM:
            try:
                response = await context.request.get(
                    f"{BASE_URL}/internal/get_show_times?date={date_str}&movieId={movie_id}&locationId=0&promotionId=0",
                    headers=DEFAULT_HEADERS,
                )
                if response.status == 200:
                    data = await response.json()
                    if data:
                        if isinstance(data, list):
                            all_schedules.extend(data)
                        else:
                            all_schedules.append(data)
            except Exception as e:
                print(f"[{movie_id}] Exception fetching showtimes for date {date_str}: {e}")

    return all_schedules


# ============================================================
# Main Scraper Pipeline
# ============================================================
async def scrape_shaw_theatre() -> Tuple[List[Dict[str, Any]], List[Any]]:
    """Main async pipeline to scrape Shaw Theatre movies and showtimes."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=HEADLESS)
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
                    await page.goto(BASE_URL, wait_until="networkidle", timeout=45000)
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

        # 1. Discover release IDs from rendered DOM links
        dom_hrefs = await page.locator("a[href*='/movie-details/']").evaluate_all(
            """els => [...new Set(els.map(e => e.getAttribute('href')))]"""
        )
        dom_ids = [
            h.strip("/").split("?")[0].split("/")[-1]
            for h in dom_hrefs
            if h and "/movie-details/" in h and not DATE_REGEX.match(h.strip("/").split("?")[0].split("/")[-1])
        ]

        # 2. Discover movie codes from internal get_selectors API
        selector_ids = []
        try:
            sel_resp = await context.request.get(
                f"{BASE_URL}/internal/get_selectors?cache=no-cache",
                headers=DEFAULT_HEADERS,
            )
            if sel_resp.status == 200:
                sel_data = await sel_resp.json()
                if isinstance(sel_data, list):
                    selector_ids = [str(item.get("code")) for item in sel_data if isinstance(item, dict) and item.get("code")]
        except Exception as e:
            print(f"Warning fetching get_selectors API: {e}")

        # Combine and deduplicate discovered movie IDs
        combined_ids = list(dict.fromkeys([i for i in dom_ids + selector_ids if i]))
        print(f"Discovered {len(combined_ids)} movie IDs (DOM: {len(dom_ids)}, Selectors API: {len(selector_ids)}).")

        cookies = await context.cookies()
        cookie_dict = {c["name"]: c["value"] for c in cookies}

        user_agent = await page.evaluate("navigator.userAgent")
        headers = dict(DEFAULT_HEADERS)
        headers["User-Agent"] = user_agent

        async with httpx.AsyncClient(timeout=30, headers=headers, cookies=cookie_dict) as client:
            print(f"Fetching details for {len(combined_ids)} movies...")
            movies = await asyncio.gather(
                *(fetch_movie(client, m_id) for m_id in combined_ids),
                return_exceptions=True,
            )

            # Filter valid movie dictionaries and deduplicate by movieId
            seen_movie_ids = set()
            valid_movies = []
            for m in movies:
                if isinstance(m, dict) and "movieId" in m:
                    m_id = m["movieId"]
                    if m_id not in seen_movie_ids:
                        seen_movie_ids.add(m_id)
                        valid_movies.append(m)

            print(f"Successfully fetched {len(valid_movies)} unique movie details.")

            movie_ids = [m["movieId"] for m in valid_movies]

            print(f"Fetching schedules for {len(movie_ids)} movies...")
            schedules = await asyncio.gather(
                *(fetch_schedules(context, movie_id) for movie_id in movie_ids),
                return_exceptions=True,
            )

        await browser.close()

        valid_schedules = [s for s in schedules if isinstance(s, (dict, list)) and s]
        print(f"Successfully fetched schedules for {len(valid_schedules)} movies.")

        return valid_movies, valid_schedules


# ============================================================
# Entry Point
# ============================================================
if __name__ == "__main__":
    valid_movies, valid_schedules = asyncio.run(scrape_shaw_theatre())

    # Parse raw dictionaries into dataclasses
    parsed_movies = parse_movies(valid_movies)
    parsed_schedules = parse_schedules(valid_schedules)

    today = datetime.now(SG_TZ).date()
    showing_count = sum(1 for m in parsed_movies if m.release_date <= today)
    coming_count = len(parsed_movies) - showing_count
    sched_movies_count = len(set(s.movie_id for s in parsed_schedules))

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
    print(f"Showing now  : {showing_count}")
    print(f"Coming soon  : {coming_count}")
    print(f"Total movies : {len(parsed_movies)}")
    print(f"Schedules    : {len(parsed_schedules)} (across {sched_movies_count} movies)")
    print(f"Logged parsed JSONs to output folder: {OUTPUT_DIR}")
    print("=" * 50 + "\n")