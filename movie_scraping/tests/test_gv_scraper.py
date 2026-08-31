import unittest
from unittest.mock import AsyncMock, patch

from movie_scraping.movies_and_schedules.golden_village.scraper import (
    ADVANCE_SALES_API,
    SHOWING_NOW_API,
    COMING_SOON_API,
    extract_film_codes,
    fetch_movie_ids,
)


class TestGVAdvanceSalesScraper(unittest.TestCase):
    def test_endpoints(self):
        self.assertEqual(ADVANCE_SALES_API, "https://www.gv.com.sg/.gv-api/homeadvancesales")
        self.assertEqual(SHOWING_NOW_API, "https://www.gv.com.sg/.gv-api/homenowshowing")
        self.assertEqual(COMING_SOON_API, "https://www.gv.com.sg/.gv-api/homecomingsoon")

    def test_extract_film_codes_advance_sales(self):
        sample_payload = {
            "success": True,
            "data": [
                {"filmCd": "9101", "filmTitle": "Upcoming Blockbuster 1"},
                {"filmCd": "9102", "filmTitle": "Upcoming Blockbuster 2"},
            ],
            "nested": {
                "items": [
                    {"filmCd": "9103"}
                ]
            }
        }
        codes = extract_film_codes(sample_payload)
        self.assertEqual(codes, {"9101", "9102", "9103"})

    def test_fetch_movie_ids_with_advance_sales(self):
        import asyncio

        mock_client = AsyncMock()

        async def run():
            with patch("movie_scraping.movies_and_schedules.golden_village.scraper.post_json") as mock_post:
                def post_side_effect(client, url, payload=None):
                    if url == SHOWING_NOW_API:
                        return {"data": [{"filmCd": "1001"}]}
                    elif url == COMING_SOON_API:
                        return {"data": [{"filmCd": "2001"}]}
                    elif url == ADVANCE_SALES_API:
                        return {"data": [{"filmCd": "3001"}]}
                    return {}

                mock_post.side_effect = post_side_effect

                res = await fetch_movie_ids(mock_client)
                self.assertIn("showing_now", res)
                self.assertIn("coming_soon", res)
                self.assertIn("advance_sales", res)
                self.assertEqual(res["showing_now"], {"1001"})
                self.assertEqual(res["coming_soon"], {"2001"})
                self.assertEqual(res["advance_sales"], {"3001"})
                self.assertEqual(res["all"], {"1001", "2001", "3001"})

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
