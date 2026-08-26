#!/usr/bin/env python3
"""
ScreenScout Subscription & Notification Monitor
Matches active user movie subscriptions against latest database records (supporting multiple matches) and dispatches Telegram notifications.
"""

import os
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import urllib.request
import urllib.error

# Ensure db connection utils
MONITOR_DIR = Path(__file__).resolve().parent
ROOT_DIR = MONITOR_DIR.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/screenscout")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")


def get_db_connection():
    return psycopg2.connect(DATABASE_URL)


def send_telegram_alert(recipient: str, message: str) -> str:
    """Send notification to Telegram bot API or simulate locally."""
    if not TELEGRAM_BOT_TOKEN:
        print(f"\n[Telegram Simulation] Alert dispatched to {recipient}:\n{message}\n")
        return "SIMULATED"

    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": recipient,
        "text": message,
        "parse_mode": "Markdown",
    }).encode("utf-8")

    req = urllib.request.Request(api_url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                return "SENT"
            return "FAILED"
    except Exception as e:
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
                   COALESCE(nc.channel_user_id, '@' || u.username) AS recipient
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
                           WHEN release_date > CURRENT_DATE THEN 'coming_soon'
                           ELSE 'now_showing'
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
            if len(matched_movies) == 1:
                m = matched_movies[0]
                status_label = "Now Showing" if m["status"] == "now_showing" else "Coming Soon"
                provider_label = "Golden Village" if m["provider"] == "GV" else "Shaw Theatres"

                msg = (
                    f"🎬 *ScreenScout Movie Alert!*\n\n"
                    f"Hello {sub['recipient']},\n"
                    f"Your tracked movie keyword *\"{sub['movie_query']}\"* is now available!\n\n"
                    f"🎥 *{m['title']}*\n"
                    f"📌 Status: {status_label}\n"
                    f"🏢 Cinema: {provider_label}\n"
                    f"📅 Release Date: {m['release_date']}\n\n"
                    f"🔗 Check showtimes: http://localhost:3000/movies/{m['id']}"
                )
                summary_title = m["title"]
            else:
                msg_lines = [
                    f"🎬 *ScreenScout Movie Alert!*\n",
                    f"Hello {sub['recipient']},",
                    f"Your tracked movie keyword *\"{sub['movie_query']}\"* matched *{len(matched_movies)}* movies!\n",
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

            # Send Alert
            delivery_status = send_telegram_alert(sub["recipient"], msg)

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
