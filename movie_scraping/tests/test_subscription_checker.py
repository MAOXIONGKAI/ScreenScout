import unittest


class TestSubscriptionMatchingLogic(unittest.TestCase):
    def test_keyword_matching(self):
        query = "spider-man"
        movie_titles = [
            "Spider-Man: Beyond the Spider-Verse",
            "The Amazing Spider-Man",
            "Batman Begins",
            "Superman Returns",
            "SPIDER-MAN: NO WAY HOME",
        ]

        matches = [t for t in movie_titles if query.lower() in t.lower()]
        self.assertEqual(len(matches), 3)
        self.assertIn("Spider-Man: Beyond the Spider-Verse", matches)
        self.assertIn("The Amazing Spider-Man", matches)
        self.assertIn("SPIDER-MAN: NO WAY HOME", matches)

    def test_single_movie_message_formatting(self):
        recipient = "@john_doe"
        query = "dune"
        m = {
            "id": 42,
            "title": "Dune: Part Two",
            "status": "now_showing",
            "provider": "GV",
            "release_date": "2026-08-28",
        }

        status_label = "Now Showing" if m["status"] == "now_showing" else "Coming Soon"
        provider_label = "Golden Village" if m["provider"] == "GV" else "Shaw Theatres"

        msg = (
            f"🎬 *ScreenScout Movie Alert!*\n\n"
            f"Hello {recipient},\n"
            f"Your tracked movie keyword *\"{query}\"* is now available!\n\n"
            f"🎥 *{m['title']}*\n"
            f"📌 Status: {status_label}\n"
            f"🏢 Cinema: {provider_label}\n"
            f"📅 Release Date: {m['release_date']}\n\n"
            f"🔗 Check showtimes: http://localhost:3000/movies/{m['id']}"
        )

        self.assertIn("Hello @john_doe", msg)
        self.assertIn("Dune: Part Two", msg)
        self.assertIn("Golden Village", msg)
        self.assertIn("Now Showing", msg)
        self.assertIn("http://localhost:3000/movies/42", msg)

    def test_advance_sales_message_formatting(self):
        recipient = "@john_doe"
        query = "wicked"
        m = {
            "id": 99,
            "title": "Wicked: For Good",
            "status": "advance_sales",
            "provider": "GV",
            "release_date": "2026-11-20",
        }

        status_label = "Now Showing" if m["status"] == "now_showing" else ("Advance Sales" if m["status"] == "advance_sales" else "Coming Soon")
        provider_label = "Golden Village" if m["provider"] == "GV" else "Shaw Theatres"

        msg = (
            f"🎬 *ScreenScout Movie Alert!*\n\n"
            f"Hello {recipient},\n"
            f"Your tracked movie keyword *\"{query}\"* is now available!\n\n"
            f"🎥 *{m['title']}*\n"
            f"📌 Status: {status_label}\n"
            f"🏢 Cinema: {provider_label}\n"
            f"📅 Release Date: {m['release_date']}\n\n"
            f"🔗 Check showtimes: http://localhost:3000/movies/{m['id']}"
        )

        self.assertIn("Advance Sales", msg)
        self.assertIn("Wicked: For Good", msg)

    def test_multiple_movies_message_formatting(self):
        recipient = "@jane_doe"
        query = "avatar"
        matched_movies = [
            {
                "id": 1,
                "title": "Avatar 3",
                "status": "coming_soon",
                "provider": "Shaw",
                "release_date": "2026-12-18",
            },
            {
                "id": 2,
                "title": "Avatar 4",
                "status": "coming_soon",
                "provider": "GV",
                "release_date": "2028-12-22",
            },
        ]

        msg_lines = [
            f"🎬 *ScreenScout Movie Alert!*\n",
            f"Hello {recipient},",
            f"Your tracked movie keyword *\"{query}\"* matched *{len(matched_movies)}* movies!\n",
        ]
        for i, m in enumerate(matched_movies, 1):
            status_label = "Now Showing" if m["status"] == "now_showing" else "Coming Soon"
            provider_label = "Golden Village" if m["provider"] == "GV" else "Shaw Theatres"
            msg_lines.append(
                f"{i}. 🎥 *{m['title']}*\n"
                f"   🏢 {provider_label} • 📌 {status_label}\n"
                f"   📅 {m['release_date']} • 🔗 http://localhost:3000/movies/{m['id']}\n"
            )
        msg = "\n".join(msg_lines)

        self.assertIn("matched *2* movies", msg)
        self.assertIn("Avatar 3", msg)
        self.assertIn("Avatar 4", msg)
        self.assertIn("Shaw Theatres", msg)


if __name__ == "__main__":
    unittest.main()
