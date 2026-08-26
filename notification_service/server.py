import json
import logging
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict

from . import config
from .telegram_client import TelegramClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("notification_service.server")

# Global Telegram client instance
telegram_client = TelegramClient()


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
            self._send_json(200, {
                "status": "healthy",
                "service": "ScreenScout Notification Service",
                "version": "1.0.0",
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

        self._send_json(404, {"error": "Not Found", "path": path})

    def log_message(self, format, *args):
        # Override to use standard logger instead of stderr
        logger.info("%s - - [%s] %s" % (self.client_address[0], self.log_date_time_string(), format % args))


import threading
import time


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

    # Start background polling thread
    poller = threading.Thread(target=_poll_telegram_updates_loop, daemon=True)
    poller.start()

    print("=" * 60)
    print(f"🚀 ScreenScout Notification Service running on http://{host}:{port}")
    print(f"🤖 Telegram Bot Status: {bot_display}")
    print(f"📡 API Endpoints:")
    print(f"   - POST http://localhost:{port}/api/notify")
    print(f"   - GET  http://localhost:{port}/api/status")
    print(f"   - GET  http://localhost:{port}/health")
    print("=" * 60)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Notification Service...")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
