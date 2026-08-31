"""
ScreenScout Notification Stream Consumer
Consumes notification events from Redis Streams with consumer groups, automated retries, and acknowledgments.
"""

import logging
import os
import socket
import threading
import time
from typing import Any, Dict, Optional

import redis
from .telegram_client import TelegramClient

logger = logging.getLogger("notification_service.stream_consumer")

DEFAULT_STREAM_NAME = "screenscout:notifications:stream"
DEFAULT_GROUP_NAME = "notification_workers"


class NotificationStreamConsumer:
    """Consumes notification jobs from a Redis Stream and dispatches them via TelegramClient."""

    def __init__(
        self,
        redis_url: Optional[str] = None,
        stream_name: Optional[str] = None,
        group_name: Optional[str] = None,
        consumer_id: Optional[str] = None,
        telegram_client: Optional[TelegramClient] = None,
        max_retries: int = 3,
    ):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.stream_name = stream_name or os.getenv("NOTIFICATION_STREAM_NAME", DEFAULT_STREAM_NAME)
        self.group_name = group_name or os.getenv("NOTIFICATION_CONSUMER_GROUP", DEFAULT_GROUP_NAME)
        
        hostname = socket.gethostname()
        pid = os.getpid()
        self.consumer_id = consumer_id or f"worker-{hostname}-{pid}"

        self.telegram_client = telegram_client or TelegramClient()
        self.max_retries = max_retries

        self.r: Optional[redis.Redis] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Metrics
        self.processed_count = 0
        self.failed_count = 0
        self.connected = False
        self.last_active: Optional[float] = None

    def connect(self) -> bool:
        """Establishes connection to Redis and creates the consumer group."""
        try:
            self.r = redis.from_url(self.redis_url, decode_responses=True, socket_timeout=5)
            self.r.ping()
            self.connected = True
            logger.info(f"✓ Connected to Redis at {self.redis_url}")

            # Ensure stream and consumer group exist
            try:
                self.r.xgroup_create(
                    name=self.stream_name,
                    groupname=self.group_name,
                    id="0",
                    mkstream=True,
                )
                logger.info(f"✓ Created consumer group '{self.group_name}' on stream '{self.stream_name}'")
            except redis.exceptions.ResponseError as e:
                if "BUSYGROUP" in str(e):
                    logger.debug(f"Consumer group '{self.group_name}' already exists.")
                else:
                    logger.warning(f"Could not create consumer group: {e}")

            return True
        except Exception as e:
            self.connected = False
            logger.warning(f"⚠️ Redis connection failed ({e}). Stream consumer will attempt reconnecting.")
            return False

    def start(self):
        """Starts the stream consumer in a background daemon thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="NotificationStreamWorker")
        self._thread.start()
        logger.info(f"🚀 Notification Stream Consumer started (Consumer ID: {self.consumer_id})")

    def stop(self):
        """Stops the consumer loop."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        logger.info("Notification Stream Consumer stopped.")

    def _run_loop(self):
        """Main event loop processing both pending and newly arrived stream messages."""
        while self._running:
            if not self.connected or not self.r:
                if not self.connect():
                    time.sleep(3.0)
                    continue

            try:
                # 1. First process any pending/unacknowledged messages from past crashes
                self._process_pending_messages()

                # 2. Read new messages arriving on the stream
                entries = self.r.xreadgroup(
                    groupname=self.group_name,
                    consumername=self.consumer_id,
                    streams={self.stream_name: ">"},
                    count=10,
                    block=2000,
                )

                if entries:
                    for stream, messages in entries:
                        for msg_id, fields in messages:
                            self._handle_message(msg_id, fields)

            except redis.exceptions.ConnectionError as e:
                self.connected = False
                logger.warning(f"Redis connection dropped ({e}), reconnecting in 3s...")
                time.sleep(3.0)
            except Exception as e:
                logger.error(f"Unexpected error in stream consumer loop: {e}", exc_info=True)
                time.sleep(1.0)

    def _process_pending_messages(self):
        """Checks for messages assigned to this group that were not acknowledged."""
        try:
            pending_entries = self.r.xreadgroup(
                groupname=self.group_name,
                consumername=self.consumer_id,
                streams={self.stream_name: "0"},
                count=10,
            )
            if pending_entries:
                for stream, messages in pending_entries:
                    for msg_id, fields in messages:
                        self._handle_message(msg_id, fields, is_retry=True)
        except Exception as e:
            logger.debug(f"Pending message check note: {e}")

    def _handle_message(self, msg_id: str, fields: Dict[str, Any], is_retry: bool = False):
        """Processes an individual message and dispatches it via TelegramClient."""
        self.last_active = time.time()

        recipient = fields.get("recipient", "").strip()
        message_text = fields.get("message", "").strip()
        channel_type = fields.get("channel_type", "TELEGRAM").upper()
        parse_mode = fields.get("parse_mode", "HTML")
        retry_count = int(fields.get("retry_count", 0))

        if is_retry:
            retry_count += 1

        if not recipient or not message_text:
            logger.warning(f"Malformed message {msg_id}: missing recipient or message. Acknowledging to discard.")
            if self.r:
                self.r.xack(self.stream_name, self.group_name, msg_id)
            return

        logger.info(f"📨 Processing notification {msg_id} -> {recipient} ({channel_type})")

        # Dispatch
        try:
            if channel_type == "TELEGRAM":
                result = self.telegram_client.send_message(recipient, message_text, parse_mode=parse_mode)
            else:
                result = {"success": False, "error": f"Unsupported channel {channel_type}"}

            if result.get("success"):
                logger.info(f"✅ Delivered notification {msg_id} to {recipient} (Status: {result.get('status')})")
                if self.r:
                    self.r.xack(self.stream_name, self.group_name, msg_id)
                self.processed_count += 1
            else:
                error_msg = result.get("error", "unknown error")
                logger.warning(f"⚠️ Failed to deliver notification {msg_id} to {recipient}: {error_msg}")

                if retry_count >= self.max_retries:
                    logger.error(f"❌ Notification {msg_id} exceeded max retries ({self.max_retries}). Discarding.")
                    if self.r:
                        self.r.xack(self.stream_name, self.group_name, msg_id)
                    self.failed_count += 1
                else:
                    # Allow message to be picked up on next retry pass
                    pass

        except Exception as e:
            logger.error(f"Error dispatching notification {msg_id}: {e}", exc_info=True)
            if retry_count >= self.max_retries:
                if self.r:
                    self.r.xack(self.stream_name, self.group_name, msg_id)
                self.failed_count += 1

    def get_stats(self) -> Dict[str, Any]:
        """Returns live metrics and status of the stream consumer."""
        stream_len = 0
        pending_count = 0

        if self.connected and self.r:
            try:
                stream_len = self.r.xlen(self.stream_name)
                pending_info = self.r.xpending(self.stream_name, self.group_name)
                if isinstance(pending_info, dict):
                    pending_count = pending_info.get("pending", 0)
            except Exception:
                pass

        return {
            "running": self._running,
            "connected": self.connected,
            "consumer_id": self.consumer_id,
            "stream_name": self.stream_name,
            "group_name": self.group_name,
            "stream_length": stream_len,
            "pending_count": pending_count,
            "messages_processed": self.processed_count,
            "messages_failed": self.failed_count,
            "last_active": self.last_active,
        }
