#!/usr/bin/env python3
"""
ScreenScout Subscription & Notification Monitor
Matches active user movie subscriptions against latest database records (supporting multiple matches) and dispatches Telegram notifications.
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import urllib.request
import urllib.error

# Ensure db connection utils and root path
MONITOR_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MONITOR_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/screenscout")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://localhost:8085/api/notify")
DEFAULT_BOT_TOKEN = "8741735560:AAHEXG5BgqrDFZmPHd4ADL54P_O-RGt6unQ"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "8741735560:AAFa9GjTfZf2u11aZ9oK8L7M6N5P4Q3R2S1":
    TELEGRAM_BOT_TOKEN = DEFAULT_BOT_TOKEN


def get_db_connection():
    return psycopg2.connect(DATABASE_URL)


def send_telegram_alert(recipient: str, message: str) -> str:
    """
    Dispatches a Telegram alert.
    Prioritizes publishing to the Redis Stream (asynchronous, non-blocking queue),
    falling back to the HTTP notification service, and finally direct Telegram client.
    """
    # 1. Primary: Publish to Redis Stream
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    stream_name = os.getenv("NOTIFICATION_STREAM_NAME", "screenscout:notifications:stream")
    try:
        import redis
        r = redis.from_url(redis_url, decode_responses=True, socket_timeout=2)
        r.xadd(stream_name, {
            "recipient": recipient,
            "channel_type": "TELEGRAM",
            "message": message,
            "parse_mode": "Markdown",
            "created_at": str(time.time()),
            "retry_count": "0",
        })
        print(f"[Redis Stream] Queued alert to {recipient} on stream '{stream_name}'")
        return "QUEUED"
    except Exception:
        pass

    payload_data = {
        "recipient": recipient,
        "channel_type": "TELEGRAM",
        "message": message,
        "parse_mode": "Markdown",
    }
    json_bytes = json.dumps(payload_data).encode("utf-8")

    # 2. Secondary: Try Notification Service HTTP
    try:
        req = urllib.request.Request(
            NOTIFICATION_SERVICE_URL,
            data=json_bytes,
            headers={"Content-Type": "application/json", "User-Agent": "ScreenScoutMonitor/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp_body = json.loads(resp.read().decode("utf-8"))
            status = resp_body.get("status", "SENT")
            if resp_body.get("success"):
                print(f"[Notification Service] Delivered alert to {recipient} (Status: {status})")
                return status
            else:
                print(f"[Notification Service Notice] Service returned: {resp_body.get('error')}. Falling back to direct Telegram client...")
    except Exception as e:
        # Fallback to direct client
        pass

    # 2. Resilient Direct Telegram Client Fallback
    try:
        from notification_service.telegram_client import TelegramClient
        client = TelegramClient()
        res = client.send_message(recipient, message)
        if res.get("success"):
            status = res.get("status", "SENT")
            print(f"[Direct Telegram Client] Delivered alert to {recipient} (Status: {status})")
            return status
        print(f"[Direct Telegram Alert Error] {res.get('error')}")
        if res.get("hint"):
            print(f"💡 Hint: {res.get('hint')}")
        return "FAILED"
    except Exception as e:
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            print(f"\n[Telegram Simulation] Alert dispatched to {recipient}:\n{message}\n")
            return "SIMULATED"
        print(f"[Telegram Alert Error] Could not deliver to {recipient}: {e}")
        return "FAILED"


def check_and_trigger_subscriptions() -> int:
    """
    Scans all active subscriptions in PostgreSQL, matches them against current movies,
    sends notifications (supporting multiple matches), and toggles matched subscriptions to triggered (is_active = FALSE).
    """
    print("\n" + "=" * 50)
    print("ScreenScout Subscription Monitor")
    print("=" * 50)

    conn = None
    triggered_count = 0

    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # 0. Ensure tables exist with matched_movies JSONB column
        cur.execute("""
            CREATE TABLE IF NOT EXISTS notification_channels (
                id                  BIGINT PRIMARY KEY,
                user_id             BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                channel_type        VARCHAR(20) NOT NULL,
                channel_user_id     VARCHAR(255) NOT NULL,
                is_enabled          BOOLEAN NOT NULL DEFAULT TRUE,
                created_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (user_id, channel_type)
            );

            CREATE SEQUENCE IF NOT EXISTS notification_channels_id_seq START WITH 1 INCREMENT BY 1;
            ALTER TABLE notification_channels ALTER COLUMN id SET DEFAULT nextval('notification_channels_id_seq');

            CREATE TABLE IF NOT EXISTS subscriptions (
                id                  BIGINT PRIMARY KEY,
                user_id             BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                movie_query         VARCHAR(255) NOT NULL,
                is_active           BOOLEAN NOT NULL DEFAULT TRUE,
                matched_movie_id    BIGINT REFERENCES movies(id) ON DELETE SET NULL,
                matched_movie_title VARCHAR(255),
                matched_movies      JSONB DEFAULT '[]'::jsonb,
                triggered_at        TIMESTAMPTZ,
                created_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            ALTER TABLE subscriptions ADD COLUMN IF NOT EXISTS matched_movies JSONB DEFAULT '[]'::jsonb;

            CREATE SEQUENCE IF NOT EXISTS subscriptions_id_seq START WITH 1 INCREMENT BY 1;
            ALTER TABLE subscriptions ALTER COLUMN id SET DEFAULT nextval('subscriptions_id_seq');

            CREATE TABLE IF NOT EXISTS notification_logs (
                id                  BIGINT PRIMARY KEY,
                subscription_id     BIGINT REFERENCES subscriptions(id) ON DELETE CASCADE,
                user_id             BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                channel_type        VARCHAR(20) NOT NULL,
                recipient           VARCHAR(255) NOT NULL,
                message             TEXT NOT NULL,
                status              VARCHAR(20) NOT NULL DEFAULT 'SENT',
                created_at          TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE SEQUENCE IF NOT EXISTS notification_logs_id_seq START WITH 1 INCREMENT BY 1;
            ALTER TABLE notification_logs ALTER COLUMN id SET DEFAULT nextval('notification_logs_id_seq');
        """)
        conn.commit()

        # 1. Fetch all active subscriptions
        cur.execute("""
            SELECT s.id, s.user_id, s.movie_query, s.is_active, u.username,
                   COALESCE(nc.channel_user_id, '@' || u.username) AS recipient,
                   COALESCE(nc.is_enabled, TRUE) AS is_enabled
            FROM subscriptions s
            JOIN users u ON s.user_id = u.id
            LEFT JOIN notification_channels nc ON s.user_id = nc.user_id AND nc.channel_type = 'TELEGRAM'
            WHERE s.is_active = TRUE
            ORDER BY s.created_at ASC
        """)
        active_subs = cur.fetchall()

        if not active_subs:
            print("No active subscriptions to monitor.")
            print("=" * 50 + "\n")
            return 0

        print(f"Checking {len(active_subs)} active subscription(s)...")

        for sub in active_subs:
            query_pattern = f"%{sub['movie_query'].strip().lower()}%"

            # Search matching movies (up to 10)
            cur.execute("""
                SELECT id, title, release_date, provider, poster_url,
                       CASE
                           WHEN EXISTS (
                               SELECT 1 FROM schedules s
                               WHERE s.movie_id = movies.id
                                 AND (s.start_date > CURRENT_DATE OR (s.start_date = CURRENT_DATE AND s.start_time >= CURRENT_TIME))
                           ) AND release_date > CURRENT_DATE THEN 'advance_sales'
                           WHEN EXISTS (
                               SELECT 1 FROM schedules s
                               WHERE s.movie_id = movies.id
                                 AND (s.start_date > CURRENT_DATE OR (s.start_date = CURRENT_DATE AND s.start_time >= CURRENT_TIME))
                           ) THEN 'now_showing'
                           ELSE 'coming_soon'
                       END AS status
                FROM movies
                WHERE LOWER(title) LIKE %s OR LOWER(COALESCE(secondary_title, '')) LIKE %s
                ORDER BY release_date DESC
                LIMIT 10
            """, (query_pattern, query_pattern))

            matched_movies = cur.fetchall()
            if not matched_movies:
                continue

            # Format Telegram Alert Message
            escaped_handle = sub['recipient'].replace('_', '\\_')
            escaped_query = sub['movie_query'].replace('*', '').replace('_', '\\_')
            frontend_base = os.getenv("FRONTEND_URL", os.getenv("NEXT_PUBLIC_API_URL", "https://screenscout.live")).rstrip("/")

            if len(matched_movies) == 1:
                m = matched_movies[0]
                status_label = "Now Showing" if m["status"] == "now_showing" else ("Advance Sales" if m["status"] == "advance_sales" else "Coming Soon")
                provider_label = "Golden Village" if m["provider"] == "GV" else "Shaw Theatres"
                clean_title = m["title"].replace('*', '').replace('_', '\\_').strip()

                msg = (
                    f"🎬 *ScreenScout Movie Alert!*\n\n"
                    f"Hello {escaped_handle},\n"
                    f"Your tracked movie keyword *\"{escaped_query}\"* is now available!\n\n"
                    f"🎥 *{clean_title}*\n"
                    f"📌 Status: {status_label}\n"
                    f"🏢 Cinema: {provider_label}\n"
                    f"📅 Release Date: {m['release_date']}\n\n"
                    f"🔗 Check showtimes: {frontend_base}/movies/{m['id']}"
                )
                summary_title = m["title"]
            else:
                msg_lines = [
                    f"🎬 *ScreenScout Movie Alert!*\n",
                    f"Hello {escaped_handle},",
                    f"Your tracked movie keyword *\"{escaped_query}\"* matched *{len(matched_movies)}* movies!\n",
                ]
                for i, m in enumerate(matched_movies, 1):
                    status_label = "Now Showing" if m["status"] == "now_showing" else ("Advance Sales" if m["status"] == "advance_sales" else "Coming Soon")
                    provider_label = "Golden Village" if m["provider"] == "GV" else "Shaw Theatres"
                    clean_title = m["title"].replace('*', '').replace('_', '\\_').strip()
                    msg_lines.append(
                        f"{i}. 🎥 *{clean_title}*\n"
                        f"   🏢 {provider_label} • 📌 {status_label}\n"
                        f"   📅 {m['release_date']} • 🔗 {frontend_base}/movies/{m['id']}\n"
                    )
                msg = "\n".join(msg_lines)
                summary_title = f"{matched_movies[0]['title']} (+{len(matched_movies)-1} more)"

            # Build JSON array of matched movies
            matched_items = [
                {
                    "id": m["id"],
                    "title": m["title"],
                    "provider": m["provider"],
                    "status": m["status"],
                    "release_date": str(m["release_date"]),
                    "poster_url": m.get("poster_url") or "",
                }
                for m in matched_movies
            ]

            # Send Alert if enabled
            if sub.get("is_enabled", True):
                delivery_status = send_telegram_alert(sub["recipient"], msg)
            else:
                delivery_status = "SKIPPED_DISABLED"
                print(f"[Subscription Notice] Notifications disabled for {sub['recipient']}. Skipping alert.")

            # Mark subscription as triggered and log notification
            cur.execute("""
                UPDATE subscriptions
                SET is_active = FALSE,
                    matched_movie_id = %s,
                    matched_movie_title = %s,
                    matched_movies = %s,
                    triggered_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (matched_movies[0]["id"], summary_title, json.dumps(matched_items), sub["id"]))

            cur.execute("""
                INSERT INTO notification_logs (subscription_id, user_id, channel_type, recipient, message, status)
                VALUES (%s, %s, 'TELEGRAM', %s, %s, %s)
            """, (sub["id"], sub["user_id"], sub["recipient"], msg, delivery_status))

            conn.commit()
            triggered_count += 1
            print(f"✓ Matched '{sub['movie_query']}' -> {len(matched_movies)} movie(s) (Notified {sub['recipient']})")

        print(f"\nMonitoring complete: {triggered_count} subscription(s) triggered.")
        print("=" * 50 + "\n")

    except Exception as e:
        print(f"[Monitor Error] {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

    return triggered_count


if __name__ == "__main__":
    check_and_trigger_subscriptions()
