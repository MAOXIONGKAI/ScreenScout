import asyncio
from dataclasses import asdict
from datetime import datetime, timedelta
import httpx
import json
from pathlib import Path
from .parser import parse_movies
from playwright.async_api import async_playwright
from zoneinfo import ZoneInfo

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
            bypass_csp=True
        )
        page = await context.new_page()
        try:
            for attempt in range(3):
                try:
                    await page.goto("https://shaw.sg", wait_until="domcontentloaded", timeout=45000)
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
        
        from .parser import parse_schedules
        parsed_schedules = parse_schedules(valid_schedules)
        with open(OUTPUT_DIR / "shaw_schedules.json", "w", encoding="utf-8") as f:
            json.dump([asdict(s) for s in parsed_schedules], f, indent=4, default=str, ensure_ascii=False)

        now = datetime.now(SG_TZ)
        showing_now = sum(1 for m in valid_movies if datetime.fromisoformat(m["releaseDate"]).replace(tzinfo=SG_TZ) <= now)
        coming_soon = len(valid_movies) - showing_now
        print(f"Scraped {len(valid_movies)} movies ({showing_now} showing now, {coming_soon} coming soon)")
        total_showtimes = sum(len(s) if isinstance(s, list) else 1 for s in valid_schedules)
        print(f"Scraped {total_showtimes} schedules across {len(valid_schedules)} movies successfully!")

        return valid_movies, valid_schedules

if __name__ == "__main__":
    movies, schedules = asyncio.run(scrape_shaw_theatre())
    parsed_movies = parse_movies(movies)

    with open(OUTPUT_DIR / "shaw_movies.json", "w") as f:
        f.write(json.dumps(
            [asdict(m) for m in parsed_movies],
            indent=4,
            default=str,
        ))

        