import asyncio
from dataclasses import asdict
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import urllib.request
import urllib.error

try:
    from .parser import parse_cinemas
except ImportError:
    from parser import parse_cinemas

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

GV_CINEMAS_BY_TYPE_API = "https://www.gv.com.sg/.gv-api/cinemasbytype?t=912_1785570201995"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "x_developer": "ENOVAX",
    "Origin": "https://www.gv.com.sg",
    "Referer": "https://www.gv.com.sg/GVCinemas",
}

POST_PAYLOAD = {"type": "T"}


def fetch_gv_cinemas_sync() -> Optional[List[Dict[str, Any]]]:
    """Fetch cinema locations from Golden Village internal API using HTTP POST via urllib."""
    data_bytes = json.dumps(POST_PAYLOAD).encode("utf-8")
    req = urllib.request.Request(
        GV_CINEMAS_BY_TYPE_API,
        data=data_bytes,
        headers=DEFAULT_HEADERS,
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status == 200:
                res_json = json.loads(resp.read().decode("utf-8"))
                if isinstance(res_json, dict) and res_json.get("success"):
                    return res_json.get("data", [])
                elif isinstance(res_json, list):
                    return res_json
    except Exception as e:
        print(f"Direct POST request via urllib failed: {e}")
    return None


async def fetch_gv_cinemas() -> Optional[List[Dict[str, Any]]]:
    """Fetch Golden Village cinema locations asynchronously."""
    return await asyncio.to_thread(fetch_gv_cinemas_sync)


async def fetch_gv_cinemas_playwright() -> Optional[List[Dict[str, Any]]]:
    """Fallback fetch for Golden Village cinema locations using Playwright context request (POST method)."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("Playwright not installed, skipping browser fallback.")
        return None

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=DEFAULT_HEADERS["User-Agent"],
            bypass_csp=True,
        )
        page = await context.new_page()
        try:
            await page.goto("https://www.gv.com.sg/GVCinemas", wait_until="domcontentloaded", timeout=45000)
            response = await context.request.post(
                GV_CINEMAS_BY_TYPE_API,
                headers=DEFAULT_HEADERS,
                data=POST_PAYLOAD,
            )
            if response.status == 200:
                res_json = await response.json()
                if isinstance(res_json, dict) and res_json.get("success"):
                    await browser.close()
                    return res_json.get("data", [])
                elif isinstance(res_json, list):
                    await browser.close()
                    return res_json
        except Exception as e:
            print(f"POST request via Playwright failed: {e}")
        finally:
            await browser.close()
    return None


async def scrape_golden_village_cinemas() -> List[Dict[str, Any]]:
    """Scrape Golden Village cinema locations from endpoint using POST method."""
    print(f"Scraping Golden Village cinemas from {GV_CINEMAS_BY_TYPE_API} via POST method...")
    
    # Try direct HTTP POST request first
    data = await fetch_gv_cinemas()
    
    # Fallback to Playwright browser context POST request if direct request fails
    if not data:
        print("Retrying via Playwright context POST request...")
        data = await fetch_gv_cinemas_playwright()

    if not data:
        print("Failed to scrape Golden Village cinema locations.")
        return []

    # Parse raw cinemas into Cinema dataclass objects
    parsed = parse_cinemas(data)

    # Save parsed cinema details to outputs
    output_file = OUTPUT_DIR / "gv_cinemas.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump([asdict(c) for c in parsed], f, indent=4, default=str, ensure_ascii=False)
        
    print(f"Successfully scraped and parsed {len(parsed)} Golden Village cinema locations. Saved to {output_file}")
    return data


if __name__ == "__main__":
    raw_cinemas = asyncio.run(scrape_golden_village_cinemas())
    if raw_cinemas:
        parsed_cinemas = parse_cinemas(raw_cinemas)
        parsed_output_file = OUTPUT_DIR / "gv_cinemas_parsed.json"
        with open(parsed_output_file, "w", encoding="utf-8") as f:
            json.dump([asdict(c) for c in parsed_cinemas], f, indent=4, default=str, ensure_ascii=False)
        print(f"Parsed {len(parsed_cinemas)} Golden Village cinema locations. Saved to {parsed_output_file}")
