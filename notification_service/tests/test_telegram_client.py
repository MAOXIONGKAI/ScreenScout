import json
import tempfile
import unittest
from pathlib import Path
from notification_service.telegram_client import TelegramClient


class TestTelegramClient(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_file = Path(self.temp_dir.name) / "test_cache.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_cache_save_and_load(self):
        # Create client with no token (simulation mode)
        client = TelegramClient(token="", cache_file=self.cache_file)
        client.username_to_chat_id = {"alice": 12345, "bob": 67890}
        client.last_update_id = 100
        client._save_cache()

        # Load into a new client instance
        client2 = TelegramClient(token="", cache_file=self.cache_file)
        self.assertEqual(client2.username_to_chat_id.get("alice"), 12345)
        self.assertEqual(client2.username_to_chat_id.get("bob"), 67890)
        self.assertEqual(client2.last_update_id, 100)

    def test_resolve_chat_id_username(self):
        client = TelegramClient(token="", cache_file=self.cache_file)
        client.username_to_chat_id = {"filmfan": 998877}

        # Case-insensitive resolution with or without '@'
        self.assertEqual(client.resolve_chat_id("@FilmFan"), 998877)
        self.assertEqual(client.resolve_chat_id("filmfan"), 998877)
        self.assertEqual(client.resolve_chat_id("@FILMFAN"), 998877)

    def test_resolve_chat_id_direct_numeric(self):
        client = TelegramClient(token="", cache_file=self.cache_file)
        # Direct numeric chat id
        self.assertEqual(client.resolve_chat_id("123456789"), 123456789)
        self.assertEqual(client.resolve_chat_id("-100123456789"), -100123456789)

    def test_simulation_mode_send_message(self):
        # Empty token activates simulation mode without network calls
        client = TelegramClient(token="", cache_file=self.cache_file)
        res = client.send_message("@sample_user", "Test message content")
        self.assertTrue(res.get("success"))
        self.assertEqual(res.get("status"), "SIMULATED")
        self.assertEqual(res.get("recipient"), "@sample_user")

    def test_deduplication_send_message(self):
        # Consecutive sends with identical recipient and content should be deduplicated
        client = TelegramClient(token="", cache_file=self.cache_file)
        res1 = client.send_message("@dup_user", "Movie alert text")
        self.assertEqual(res1.get("status"), "SIMULATED")
        self.assertFalse(res1.get("duplicate", False))

        res2 = client.send_message("@dup_user", "Movie alert text")
        self.assertEqual(res2.get("status"), "DEDUPLICATED")
        self.assertTrue(res2.get("duplicate"))


if __name__ == "__main__":
    unittest.main()
