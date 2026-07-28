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
        
        
        await browser.close()
        valid = [m for m in movies if isinstance(m, dict)]

        now_ms = int(datetime.now(SG_TZ).timestamp() * 1000)
        coming_soon = []
        showing_now = []
        for movie in valid:
            if movie["releaseDate"] > now_ms:
                coming_soon.append(movie)
            else:
                showing_now.append(movie)  
        
        with open("coming_soon.json", "w") as f:
            f.write(json.dumps(coming_soon, indent=4))
        with open("showing_now.json", "w") as f:
            f.write(json.dumps(showing_now, indent=4))

        print(f"Scraped {len(valid)} movies successfully!")


if __name__ == "__main__":
    asyncio.run(scrape_golden_village())

