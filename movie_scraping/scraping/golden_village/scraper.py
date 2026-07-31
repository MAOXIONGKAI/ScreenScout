import asyncio
from dataclasses import asdict
from datetime import datetime
import httpx
import json
from parser import parse_movies
from playwright.async_api import async_playwright
from zoneinfo import ZoneInfo

SG_TZ = ZoneInfo("Asia/Singapore")

sem = asyncio.Semaphore(5)
film_info_api = "https://www.gv.com.sg/.gv-api/filminfo"
async def fetch_movie(client: httpx.AsyncClient, movie_id: str):
    async with sem:
        try:
            response = await client.post(
                film_info_api,
                json={"filmCode": movie_id},
            )
            response.raise_for_status()

            data = response.json()

            if not data.get("success"):
                print(f"{movie_id}: {data.get('errorMessage')}")
                return None

            return data["data"]

        except Exception as e:
            print(f"{movie_id}: {e}")
            return None

schedule_info_api = "https://www.gv.com.sg/.gv-api/sessionforfilm"
async def fetch_schedules(client: httpx.AsyncClient, movie_id: str):
    async with sem:
        try:
            response = await client.post(
                schedule_info_api,
                json={"filmCode": movie_id},
            )
            response.raise_for_status()

            data = response.json()

            if not data:
                print(f"{movie_id}: Failed to retrieve schedule info.")
                return None

            return data

        except Exception as e:
            print(f"{movie_id} schedule: {e}")
            return None

async def scrape_golden_village():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            channel="chrome"
        )
        context = await browser.new_context()

        page = await context.new_page()
        await page.goto("https://www.gv.com.sg/GVMovies", wait_until="domcontentloaded", timeout=60000)        
        movie_ids = await page.locator("a[href^='GVMovieDetails/movie/']").evaluate_all(
                """
                    els => els.map(e => e.getAttribute('href').split('/').pop())
                """
            )

        cookies = await context.cookies()
        cookie_dict = {
            c["name"]: c["value"]
            for c in cookies
        }
        headers = {
            "x_developer": "ENOVAX",
            "Origin": "https://www.gv.com.sg",
            "Referer": "https://www.gv.com.sg/GVMovieDetails",
            "User-Agent": await page.evaluate("navigator.userAgent"),
        }
        
        async with httpx.AsyncClient(
            timeout=30,
            cookies=cookie_dict,
            headers=headers
            ) as client:
            movies = await asyncio.gather(
                *(fetch_movie(client, movie_id) for movie_id in movie_ids),
                return_exceptions=True
            )

        async with httpx.AsyncClient(
            timeout=30,
            cookies=cookie_dict,
            headers=headers
            ) as client:
            schedules = await asyncio.gather(
                *(fetch_schedules(client, movie_id) for movie_id in movie_ids),
                return_exceptions=True
            )
        
        
        await browser.close()
        valid_movies = [m for m in movies if isinstance(m, dict)]
        valid_schedules = [s for s in schedules if isinstance(s, dict)]

        with open("gv_schedules.json", "w") as f:
            f.write(json.dumps(valid_schedules, indent=4))

        now_ms = int(datetime.now(SG_TZ).timestamp() * 1000)
        showing_now = sum(1 for m in valid_movies if m["releaseDate"] <= now_ms)
        coming_soon = len(valid_movies) - showing_now
        print(f"Scraped {len(valid_movies)} movies ({showing_now} showing now, {coming_soon} coming soon)")
        total_showtimes = sum(len(s["data"]["locations"]) for s in valid_schedules if s.get("data"))
        print(f"Scraped {total_showtimes} schedules across {len(valid_schedules)} movies successfully!")

        return valid_movies, valid_schedules

if __name__ == "__main__":
    movies, schedules = asyncio.run(scrape_golden_village())
    parsed_movies = parse_movies(movies)

    with open("gv_movies.json", "w") as f:
        f.write(json.dumps(
            [asdict(m) for m in parsed_movies],
            indent=4,
            default=str,
        ))

