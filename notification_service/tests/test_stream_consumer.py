import os
import tempfile
import time
import unittest
from pathlib import Path
import redis

from notification_service.telegram_client import TelegramClient
from notification_service.stream_consumer import NotificationStreamConsumer


class TestStreamConsumer(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_file = Path(self.temp_dir.name) / "test_cache.json"
        self.telegram_client = TelegramClient(token="", cache_file=self.cache_file)
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        self.test_stream = f"test:notifications:{int(time.time() * 1000)}"
        self.test_group = "test_workers"

    def tearDown(self):
        self.temp_dir.cleanup()
        # Clean up test stream
        try:
            r = redis.from_url(self.redis_url, decode_responses=True)
            r.delete(self.test_stream)
        except Exception:
            pass

    def test_consumer_lifecycle_and_processing(self):
        try:
            r = redis.from_url(self.redis_url, decode_responses=True, socket_timeout=2)
            r.ping()
        except Exception:
            self.skipTest("Redis not available for integration test")

        consumer = NotificationStreamConsumer(
            redis_url=self.redis_url,
            stream_name=self.test_stream,
            group_name=self.test_group,
            consumer_id="test-worker-1",
            telegram_client=self.telegram_client,
        )

        connected = consumer.connect()
        self.assertTrue(connected)

        # 1. Publish a test notification to the stream
        msg_id = r.xadd(self.test_stream, {
            "recipient": "@sample_user",
            "message": "Stream notification test payload",
            "channel_type": "TELEGRAM",
            "parse_mode": "Markdown",
        })
        self.assertIsNotNone(msg_id)

        # 2. Start consumer
        consumer.start()
        time.sleep(0.5)

        # 3. Verify message was processed
        consumer.stop()
        self.assertGreaterEqual(consumer.processed_count, 1)

        # 4. Check stream stats
        stats = consumer.get_stats()
        self.assertEqual(stats["stream_name"], self.test_stream)
        self.assertEqual(stats["group_name"], self.test_group)
        self.assertEqual(stats["pending_count"], 0)  # Should be acknowledged

    def test_consumer_handles_malformed_message(self):
        try:
            r = redis.from_url(self.redis_url, decode_responses=True, socket_timeout=2)
            r.ping()
        except Exception:
            self.skipTest("Redis not available for integration test")

        consumer = NotificationStreamConsumer(
            redis_url=self.redis_url,
            stream_name=self.test_stream,
            group_name=self.test_group,
            consumer_id="test-worker-2",
            telegram_client=self.telegram_client,
        )
        consumer.connect()

        # Publish malformed message (missing message text)
        r.xadd(self.test_stream, {"recipient": "@only_recipient"})

        consumer.start()
        time.sleep(0.5)
        consumer.stop()

        # Malformed message acknowledged to prevent blocking
        stats = consumer.get_stats()
        self.assertEqual(stats["pending_count"], 0)


if __name__ == "__main__":
    unittest.main()
