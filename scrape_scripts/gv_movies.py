import asyncio
from datetime import datetime, timezone
import httpx
import json
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
        await page.goto("https://www.gv.com.sg/GVMovies")        
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

        now_ms = int(datetime.now(SG_TZ).timestamp() * 1000)
        coming_soon = []
        showing_now = []
        for movie in valid_movies:
            if movie["releaseDate"] > now_ms:
                coming_soon.append(movie)
            else:
                showing_now.append(movie)  
        
        with open("coming_soon.json", "w") as f:
            f.write(json.dumps(coming_soon, indent=4))
        with open("showing_now.json", "w") as f:
            f.write(json.dumps(showing_now, indent=4))
        with open("gv_schedules.json", "w") as f:
            f.write(json.dumps(valid_schedules, indent=4))

        print(f"Scraped {len(valid_movies)} movies successfully!")
        total_showtimes = sum(len(s["data"]["locations"]) for s in valid_schedules if s.get("data"))
        print(f"Scraped {total_showtimes} schedules across {len(valid_schedules)} movies successfully!")

if __name__ == "__main__":
    asyncio.run(scrape_golden_village())

