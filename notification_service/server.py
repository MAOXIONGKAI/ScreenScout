import json
import logging
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict

from . import config
from .telegram_client import TelegramClient
from .stream_consumer import NotificationStreamConsumer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("notification_service.server")

# Global Telegram client instance
telegram_client = TelegramClient()

# Global Redis Stream consumer instance
stream_consumer = NotificationStreamConsumer(telegram_client=telegram_client)


class NotificationRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the ScreenScout Notification Service."""

    def _set_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def _send_json(self, status_code: int, data: Dict[str, Any]):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(204)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]

        if path in ("/health", "/api/health"):
            stream_stats = stream_consumer.get_stats()
            self._send_json(200, {
                "status": "healthy",
                "service": "ScreenScout Notification Service",
                "version": "1.0.0",
                "redis_stream": {
                    "connected": stream_stats.get("connected", False),
                    "running": stream_stats.get("running", False),
                },
            })
            return

        if path in ("/status", "/api/status"):
            bot_username = telegram_client.get_bot_username()
            self._send_json(200, {
                "status": "healthy",
                "service": "ScreenScout Notification Service",
                "port": config.PORT,
                "telegram": {
                    "configured": bool(telegram_client.token),
                    "bot_username": f"@{bot_username}" if bot_username else None,
                    "cached_users_count": len(telegram_client.username_to_chat_id),
                    "cached_users": list(telegram_client.username_to_chat_id.keys()),
                },
                "redis_stream": stream_consumer.get_stats(),
            })
            return

        if path in ("/api/telegram/bot-info", "/bot-info"):
            bot_username = telegram_client.get_bot_username()
            self._send_json(200, {
                "configured": bool(telegram_client.token),
                "bot_username": f"@{bot_username}" if bot_username else None,
                "bot_info": telegram_client.bot_info,
            })
            return

        self._send_json(404, {"error": "Not Found", "path": path})

    def do_POST(self):
        path = self.path.split("?")[0]

        # Read JSON body
        content_length = int(self.headers.get("Content-Length", 0))
        body = b""
        if content_length > 0:
            body = self.rfile.read(content_length)

        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception as e:
            self._send_json(400, {"error": f"Invalid JSON payload: {e}"})
            return

        # 1. Main Notification Endpoint: POST /api/notify or /notify
        if path in ("/api/notify", "/notify"):
            recipient = payload.get("recipient", "").strip()
            message = payload.get("message", "").strip()
            channel_type = payload.get("channel_type", "TELEGRAM").upper()
            parse_mode = payload.get("parse_mode", "Markdown")

            if not recipient:
                self._send_json(400, {"error": "Missing required field: 'recipient'"})
                return
            if not message:
                self._send_json(400, {"error": "Missing required field: 'message'"})
                return

            if channel_type == "TELEGRAM":
                result = telegram_client.send_message(recipient, message, parse_mode=parse_mode)
                status_code = 200 if result.get("success") else 502
                self._send_json(status_code, result)
            else:
                self._send_json(400, {"error": f"Unsupported channel_type: '{channel_type}'. Supported: 'TELEGRAM'"})
            return

        # 2. Sync updates from Telegram: POST /api/telegram/sync
        if path in ("/api/telegram/sync", "/sync"):
            new_count = telegram_client.sync_updates()
            self._send_json(200, {
                "success": True,
                "new_users_discovered": new_count,
                "total_cached_users": len(telegram_client.username_to_chat_id),
                "cached_users": list(telegram_client.username_to_chat_id.keys()),
            })
            return

        # 3. Manual user registration: POST /api/telegram/register
        if path in ("/api/telegram/register", "/register"):
            username = payload.get("username", "").strip()
            chat_id = payload.get("chat_id")
            if not username or not chat_id:
                self._send_json(400, {"error": "Missing 'username' or 'chat_id'"})
                return
            telegram_client.register_user(username, chat_id)
            self._send_json(200, {
                "success": True,
                "registered": {"username": username, "chat_id": chat_id},
            })
            return

        # 4. Webhook handler: POST /webhook/telegram
        if path in ("/webhook/telegram", "/api/webhook/telegram"):
            # Update cache with webhook message if available
            msg = payload.get("message", {})
            from_user = msg.get("from", {})
            chat = msg.get("chat", {})
            username = from_user.get("username") or chat.get("username")
            chat_id = chat.get("id")
            if username and chat_id:
                telegram_client.register_user(username, chat_id)
            self._send_json(200, {"ok": True})
            return

        # 5. On-Demand Scraper Pipeline Trigger: POST /api/scrape or /scrape
        if path in ("/api/scrape", "/scrape"):
            provider = payload.get("provider", "all").lower()
            try:
                import subprocess

                # 1. Scrape Cinemas
                cinemas_script = config.ROOT_DIR / "movie_scraping" / "cinemas" / "main.py"
                p1 = subprocess.run(
                    [sys.executable, str(cinemas_script), "--provider", provider],
                    capture_output=True,
                    text=True,
                    timeout=180,
                    cwd=str(config.ROOT_DIR),
                )
                if p1.returncode != 0:
                    self._send_json(500, {
                        "error": f"Cinema scraper failed: {p1.stderr or p1.stdout}",
                        "details": p1.stdout,
                    })
                    return

                # 2. Scrape Movies and Schedules
                movies_script = config.ROOT_DIR / "movie_scraping" / "movies_and_schedules" / "main.py"
                p2 = subprocess.run(
                    [sys.executable, str(movies_script), "--provider", provider],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=str(config.ROOT_DIR),
                )
                if p2.returncode != 0:
                    self._send_json(500, {
                        "error": f"Movie scraper failed: {p2.stderr or p2.stdout}",
                        "details": p2.stdout,
                    })
                    return

                # 3. Clean database (purge past schedules and ended movie runs)
                clean_script = config.ROOT_DIR / "movie_scraping" / "clean" / "main.py"
                if clean_script.exists():
                    try:
                        subprocess.run(
                            [sys.executable, str(clean_script)],
                            capture_output=True,
                            text=True,
                            timeout=60,
                            cwd=str(config.ROOT_DIR),
                        )
                    except Exception as clean_err:
                        logger.warning(f"Database cleanup warning: {clean_err}")

                # 4. Check subscriptions and trigger notification alerts
                sub_script = config.ROOT_DIR / "movie_scraping" / "monitor" / "subscription_checker.py"
                if sub_script.exists():
                    try:
                        subprocess.run(
                            [sys.executable, str(sub_script)],
                            capture_output=True,
                            text=True,
                            timeout=60,
                            cwd=str(config.ROOT_DIR),
                        )
                    except Exception as sub_err:
                        logger.warning(f"Subscription checker warning: {sub_err}")

                self._send_json(200, {
                    "success": True,
                    "message": "Full fetch of cinemas, movies, and showtimes completed successfully.",
                    "details": p2.stdout,
                })
        # 6. Database Cleanup Trigger: POST /api/clean or /clean
        if path in ("/api/clean", "/clean"):
            try:
                import subprocess
                clean_script = config.ROOT_DIR / "movie_scraping" / "clean" / "main.py"
                p = subprocess.run(
                    [sys.executable, str(clean_script)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=str(config.ROOT_DIR),
                )
                if p.returncode != 0:
                    self._send_json(500, {
                        "error": f"Database cleaner failed: {p.stderr or p.stdout}",
                        "details": p.stdout,
                    })
                    return

                self._send_json(200, {
                    "success": True,
                    "message": "Database cleanup completed successfully. Outdated schedules and past-year movies removed.",
                    "details": p.stdout,
                })
            except Exception as e:
                self._send_json(500, {"error": f"Failed to execute database cleaner: {str(e)}"})
            return

        self._send_json(404, {"error": "Not Found", "path": path})

    def log_message(self, format, *args):
        # Override to use standard logger instead of stderr
        logger.info("%s - - [%s] %s" % (self.client_address[0], self.log_date_time_string(), format % args))


def _poll_telegram_updates_loop():
    """Background daemon thread to poll /start messages from Telegram."""
    while True:
        try:
            if telegram_client.token:
                telegram_client.sync_updates()
        except Exception:
            pass
        time.sleep(3)


def run_server(host: str = config.HOST, port: int = config.PORT):
    server_address = (host, port)
    ThreadingHTTPServer.allow_reuse_address = True
    httpd = ThreadingHTTPServer(server_address, NotificationRequestHandler)

    bot_name = telegram_client.get_bot_username()
    bot_display = f"@{bot_name}" if bot_name else "(Simulation Mode - No Token)"

    # Start background Telegram update polling thread
    poller = threading.Thread(target=_poll_telegram_updates_loop, daemon=True, name="TelegramUpdatePoller")
    poller.start()

    # Start background Redis Stream consumer
    stream_consumer.start()

    print("=" * 60)
    print(f"🚀 ScreenScout Notification Service running on http://{host}:{port}")
    print(f"🤖 Telegram Bot Status: {bot_display}")
    print(f"⚡ Redis Stream Worker: {stream_consumer.stream_name} (Group: {stream_consumer.group_name})")
    print(f"📡 API Endpoints:")
    print(f"   - POST http://localhost:{port}/api/notify")
    print(f"   - GET  http://localhost:{port}/api/status")
    print(f"   - GET  http://localhost:{port}/health")
    print("=" * 60)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Notification Service...")
        stream_consumer.stop()
        httpd.server_close()


if __name__ == "__main__":
    run_server()
