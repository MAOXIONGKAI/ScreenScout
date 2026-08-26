import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional, Union

from . import config

logger = logging.getLogger("notification_service.telegram")


class TelegramClient:
    """Handles Telegram Bot API communications, user resolution, and message delivery."""

    def __init__(self, token: Optional[str] = None, cache_file: Optional[Path] = None):
        self.token = (token if token is not None else config.TELEGRAM_BOT_TOKEN).strip()
        self.cache_file = cache_file or config.CACHE_FILE
        self.bot_info: Optional[Dict[str, Any]] = None
        self.username_to_chat_id: Dict[str, int] = {}
        self.last_update_id = 0

        self._load_cache()
        if self.token:
            self._fetch_bot_info()
            self.sync_updates()

    def _load_cache(self) -> None:
        """Load cached username -> chat_id mappings from disk."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.username_to_chat_id = {k.lower(): v for k, v in data.get("users", {}).items()}
                    self.last_update_id = data.get("last_update_id", 0)
                    logger.info(f"Loaded {len(self.username_to_chat_id)} cached Telegram users")
            except Exception as e:
                logger.warning(f"Could not load cache file: {e}")

    def _save_cache(self) -> None:
        """Persist username mappings to disk."""
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump({
                    "users": self.username_to_chat_id,
                    "last_update_id": self.last_update_id,
                }, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save cache file: {e}")

    def _fetch_bot_info(self) -> Optional[Dict[str, Any]]:
        """Call Telegram getMe to verify bot token and get bot username."""
        if not self.token:
            return None
        url = f"https://api.telegram.org/bot{self.token}/getMe"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ScreenScoutNotificationService/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("ok"):
                    self.bot_info = data.get("result")
                    logger.info(f"Telegram Bot connected: @{self.bot_info.get('username')} (ID: {self.bot_info.get('id')})")
                    return self.bot_info
        except Exception as e:
            logger.error(f"Failed to fetch Telegram bot info: {e}")
        return None

    def get_bot_username(self) -> Optional[str]:
        if self.bot_info:
            return self.bot_info.get("username")
        return None

    def register_user(self, username: str, chat_id: int) -> None:
        """Manually map a Telegram username to a chat ID."""
        clean_user = username.lstrip("@").strip().lower()
        if clean_user and chat_id:
            self.username_to_chat_id[clean_user] = int(chat_id)
            self._save_cache()
            logger.info(f"Registered Telegram mapping: @{clean_user} -> {chat_id}")

    def sync_updates(self) -> int:
        """
        Query Telegram getUpdates to extract user chat IDs from /start or any interactions.
        Returns number of newly discovered users.
        """
        if not self.token:
            return 0

        url = f"https://api.telegram.org/bot{self.token}/getUpdates"
        params = {"timeout": 0}
        if self.last_update_id > 0:
            params["offset"] = self.last_update_id + 1

        url_with_params = f"{url}?{urllib.parse.urlencode(params)}"
        new_users_count = 0

        try:
            req = urllib.request.Request(url_with_params, headers={"User-Agent": "ScreenScoutNotificationService/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("ok"):
                    updates = data.get("result", [])
                    for update in updates:
                        up_id = update.get("update_id", 0)
                        if up_id > self.last_update_id:
                            self.last_update_id = up_id

                        msg = update.get("message") or update.get("channel_post") or update.get("my_chat_member")
                        if not msg:
                            continue

                        chat = msg.get("chat", {})
                        chat_id = chat.get("id")
                        from_user = msg.get("from", {})
                        text = msg.get("text", "").strip()

                        # Check username in from or chat
                        username = from_user.get("username") or chat.get("username")
                        first_name = from_user.get("first_name") or chat.get("first_name", "Movie Buff")

                        if username and chat_id:
                            clean_name = username.lstrip("@").strip().lower()
                            is_new = clean_name not in self.username_to_chat_id
                            if is_new:
                                new_users_count += 1
                                logger.info(f"Discovered user @{clean_name} (chat_id: {chat_id})")

                            self.username_to_chat_id[clean_name] = chat_id

                            # If user sent /start, send a confirmation welcome message
                            if text.startswith("/start"):
                                self._send_welcome(chat_id, clean_name, first_name)

                        elif chat_id and text.startswith("/start"):
                            # If user has no public @username, map by first_name or numeric ID
                            self._send_welcome(chat_id, str(chat_id), first_name)

                    if updates:
                        self._save_cache()
                        logger.info(f"Synced {len(updates)} Telegram updates, {new_users_count} new users mapped")
        except Exception as e:
            logger.warning(f"Error syncing Telegram updates: {e}")

        return new_users_count

    def _send_welcome(self, chat_id: int, handle: str, first_name: str) -> None:
        """Send welcome confirmation when a user presses /start."""
        welcome_text = (
            f"🎬 *Welcome to ScreenScout, {first_name}!*\n\n"
            f"✅ Your Telegram account (`@{handle}`) is now linked for real-time movie notifications!\n\n"
            f"You will automatically receive alerts here the moment showtimes or new screenings "
            f"for your subscribed movies are published across Singapore cinemas (Golden Village & Shaw Theatres).\n\n"
            f"Happy movie hunting! 🍿"
        )
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": welcome_text,
            "parse_mode": "Markdown",
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception as e:
            logger.debug(f"Could not send welcome message to {chat_id}: {e}")

    def resolve_chat_id(self, recipient: str) -> Optional[Union[int, str]]:
        """
        Resolve a recipient (e.g. '@john_doe', 'john_doe', '12345678', or '@mychannel')
        to a valid Telegram chat_id.
        """
        raw = str(recipient).strip()
        if not raw:
            return None

        # If already numeric (user ID or channel ID like -100...)
        if re.match(r"^-?\d+$", raw):
            return int(raw)

        clean = raw.lstrip("@").strip().lower()

        # Check in memory cache
        if clean in self.username_to_chat_id:
            return self.username_to_chat_id[clean]

        # Try to sync latest updates in case the user just sent /start
        self.sync_updates()
        if clean in self.username_to_chat_id:
            return self.username_to_chat_id[clean]

        # If it's a public channel username like @channelname
        if raw.startswith("@"):
            return raw

        return None

    def send_message(self, recipient: str, text: str, parse_mode: str = "Markdown") -> Dict[str, Any]:
        """
        Send a notification to a Telegram handle or chat ID.
        If no token is configured, operates in Simulation Mode and logs message cleanly.
        """
        clean_recipient = recipient.strip()

        # 1. Simulation Mode if no bot token
        if not self.token:
            print("\n" + "=" * 55)
            print(f"[Notification Service] (Telegram Simulation Mode)")
            print(f"Recipient: {clean_recipient}")
            print("-" * 55)
            print(text)
            print("=" * 55 + "\n")
            return {
                "success": True,
                "status": "SIMULATED",
                "recipient": clean_recipient,
                "channel": "TELEGRAM",
                "message": "Notification logged in simulation mode (set TELEGRAM_BOT_TOKEN for real Telegram delivery)",
            }

        # 2. Resolve chat ID
        chat_id = self.resolve_chat_id(clean_recipient)
        target = chat_id if chat_id is not None else clean_recipient

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": target,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": False,
        }

        # First attempt with requested parse_mode
        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=req_data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=12) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                if resp_data.get("ok"):
                    result = resp_data.get("result", {})
                    logger.info(f"Telegram notification delivered to {clean_recipient} (message_id: {result.get('message_id')})")
                    return {
                        "success": True,
                        "status": "SENT",
                        "recipient": clean_recipient,
                        "chat_id": target,
                        "channel": "TELEGRAM",
                        "telegram_message_id": result.get("message_id"),
                    }
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            logger.warning(f"Telegram API HTTP error {e.code} for {clean_recipient}: {err_body}")

            # If markdown parse error, retry without parse_mode
            if "can't parse entities" in err_body or "entity" in err_body:
                try:
                    payload.pop("parse_mode", None)
                    req_data = json.dumps(payload).encode("utf-8")
                    req = urllib.request.Request(url, data=req_data, headers={"Content-Type": "application/json"})
                    with urllib.request.urlopen(req, timeout=12) as resp:
                        resp_data = json.loads(resp.read().decode("utf-8"))
                        if resp_data.get("ok"):
                            result = resp_data.get("result", {})
                            return {
                                "success": True,
                                "status": "SENT",
                                "recipient": clean_recipient,
                                "chat_id": target,
                                "channel": "TELEGRAM",
                                "telegram_message_id": result.get("message_id"),
                                "fallback": "plain_text",
                            }
                except Exception as retry_err:
                    logger.error(f"Telegram plain text retry failed: {retry_err}")

            bot_name = self.get_bot_username() or "your bot"
            error_hint = ""
            if "chat not found" in err_body or chat_id is None:
                error_hint = f"User '{clean_recipient}' has not started the Telegram bot yet. Please send /start to @{bot_name} first."

            return {
                "success": False,
                "status": "FAILED",
                "recipient": clean_recipient,
                "channel": "TELEGRAM",
                "error": err_body,
                "hint": error_hint,
            }
        except Exception as e:
            logger.error(f"Unexpected error dispatching Telegram alert to {clean_recipient}: {e}")
            return {
                "success": False,
                "status": "FAILED",
                "recipient": clean_recipient,
                "channel": "TELEGRAM",
                "error": str(e),
            }
