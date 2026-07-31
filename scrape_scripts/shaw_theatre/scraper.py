import asyncio
from datetime import datetime, timedelta, timezone
import httpx
import json
from playwright.async_api import async_playwright
from zoneinfo import ZoneInfo

SG_TZ = ZoneInfo("Asia/Singapore")

sem = asyncio.Semaphore(5)
film_info_api = "https://shaw.sg/internal/get_movie_release?id="
async def fetch_movie(client: httpx.AsyncClient, movie_id: str):
    async with sem:
        try:
            response = await client.get(film_info_api + movie_id)
            response.raise_for_status()

            data = response.json()

            if not data:
                print(f"{movie_id}: Failed to retrieve movie info.")
                return None

            return data

        except Exception as e:
            print(f"{movie_id}: {e}")
            return None

async def fetch_schedules(context, movie_id: str):
    all_schedules = []
    current_date = datetime.now(SG_TZ).date()

    while True:
        date_str = current_date.strftime("%Y-%m-%d")
        async with sem:
            response = await context.request.get(
                f"https://shaw.sg/internal/get_show_times"
                f"?date={date_str}"
                f"&movieId={movie_id}"
                f"&locationId=0"
                f"&promotionId=0",
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

async def scrape_shaw_theatre():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            channel="chrome"
        )
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto("https://shaw.sg/")
        release_ids = await page.locator("a[href^='/movie-details/']").evaluate_all(
                """
                    els => [...new Set(els.map(e => e.getAttribute('href').split('/').pop()))]
                """
            )

        cookies = await context.cookies()

        cookie_dict = {
            c["name"]: c["value"]
            for c in cookies
        }

        headers = {
            "User-Agent": await page.evaluate("navigator.userAgent"),
            "Referer": f"https://shaw.sg/movie-details/",
            "Accept": "application/json, text/plain, */*",
            "x-api-forward-to": "internal",
            "x-app": "PWSM",
        }

        async with httpx.AsyncClient(
            timeout=30,
            headers=headers,
            cookies=cookie_dict
        ) as client:
            movies = await asyncio.gather(
                *(fetch_movie(client, release_id) for release_id in release_ids),
                return_exceptions=True
            )
            
            movie_ids = [m["movieId"] for m in movies if isinstance(m, dict)]

            schedules = await asyncio.gather(
                *(fetch_schedules(context, movie_id) for movie_id in movie_ids),
                return_exceptions=True
            )

        await browser.close()
        valid_movies = [m for m in movies if isinstance(m, dict)]
        valid_schedules = [s for s in schedules if isinstance(s, (dict, list)) and s]

        now = datetime.now(SG_TZ)
        coming_soon = []
        showing_now = []
        for movie in valid_movies:
            release = datetime.fromisoformat(movie["releaseDate"]).replace(tzinfo=SG_TZ)
            if release > now:
                coming_soon.append(movie)
            else:
                showing_now.append(movie)
        
        with open("coming_soon.json", "w") as f:
            f.write(json.dumps(coming_soon, indent=4))
        with open("showing_now.json", "w") as f:
            f.write(json.dumps(showing_now, indent=4))
        with open("shaw_schedules.json", "w") as f:
            f.write(json.dumps(valid_schedules, indent=4))

        print(f"Scraped {len(valid_movies)} movies successfully!")
        total_showtimes = sum(len(s) if isinstance(s, list) else 1 for s in valid_schedules)
        print(f"Scraped {total_showtimes} schedules across {len(valid_schedules)} movies successfully!")

if __name__ == "__main__":
    asyncio.run(scrape_shaw_theatre())
        