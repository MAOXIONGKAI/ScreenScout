import asyncio
from dataclasses import asdict
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import urllib.request
import urllib.error

from .parser import parse_cinemas

OUTPUT_DIR = Path(__file__).resolve().parent.parent.parent / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SHAW_SIMPLE_LOCATIONS_API = "https://shaw.sg/internal/get_simple_locations"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://shaw.sg/theaters",
    "x-api-forward-to": "internal",
    "x-app": "PWSM",
}


def fetch_shaw_cinemas_sync() -> Optional[List[Dict[str, Any]]]:
    """Fetch simple cinema locations from Shaw internal API using HTTP GET via urllib."""
    req = urllib.request.Request(SHAW_SIMPLE_LOCATIONS_API, headers=DEFAULT_HEADERS, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    return [data]
    except Exception as e:
        print(f"Direct GET request via urllib failed: {e}")
    return None


async def fetch_shaw_cinemas() -> Optional[List[Dict[str, Any]]]:
    """Fetch simple cinema locations asynchronously."""
    return await asyncio.to_thread(fetch_shaw_cinemas_sync)


async def fetch_shaw_cinemas_playwright() -> Optional[List[Dict[str, Any]]]:
    """Fallback fetch for simple cinema locations using Playwright context request (GET method)."""
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
            await page.goto("https://shaw.sg", wait_until="domcontentloaded", timeout=45000)
            response = await context.request.get(
                SHAW_SIMPLE_LOCATIONS_API,
                headers=DEFAULT_HEADERS,
            )
            if response.status == 200:
                data = await response.json()
                if isinstance(data, list):
                    await browser.close()
                    return data
                elif isinstance(data, dict):
                    await browser.close()
                    return [data]
        except Exception as e:
            print(f"GET request via Playwright failed: {e}")
        finally:
            await browser.close()
    return None


async def scrape_shaw_cinemas() -> List[Dict[str, Any]]:
    """Scrape Shaw cinema location information from endpoint using GET method."""
    print(f"Scraping Shaw cinemas from {SHAW_SIMPLE_LOCATIONS_API} via GET method...")
    
    # Try direct HTTP GET request first
    data = await fetch_shaw_cinemas()
    
    # Fallback to Playwright browser context GET request if direct request fails
    if not data:
        print("Retrying via Playwright context GET request...")
        data = await fetch_shaw_cinemas_playwright()

    if not data:
        print("Failed to scrape Shaw cinema locations.")
        return []

    # Parse raw cinemas into Cinema dataclass objects
    parsed = parse_cinemas(data)

    # Save parsed cinema details to outputs
    output_file = OUTPUT_DIR / "shaw_cinemas.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump([asdict(c) for c in parsed], f, indent=4, default=str, ensure_ascii=False)
        
    print(f"Successfully scraped and parsed {len(parsed)} Shaw cinema locations. Saved to {output_file}")
    return data


if __name__ == "__main__":
    raw_cinemas = asyncio.run(scrape_shaw_cinemas())
    if raw_cinemas:
        parsed_cinemas = parse_cinemas(raw_cinemas)
        parsed_output_file = OUTPUT_DIR / "shaw_cinemas_parsed.json"
        with open(parsed_output_file, "w", encoding="utf-8") as f:
            json.dump([asdict(c) for c in parsed_cinemas], f, indent=4, default=str, ensure_ascii=False)
        print(f"Parsed {len(parsed_cinemas)} Shaw cinema locations. Saved to {parsed_output_file}")
