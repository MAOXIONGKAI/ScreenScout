#!/usr/bin/env python3
"""
Seed Script: Populates authentic users and realistic movie reviews
across movies in the ScreenScout database.

Incremental Behavior (Default):
- Only populates reviews for new movies that currently have 0 reviews.
- Existing movies with user reviews remain completely intact.
- Ensures at least 1,256 active demo users in the database.

Full Reset:
- Pass `--reset` or `--force` to wipe and re-seed all reviews from scratch.
"""

import os
import sys
import random
import argparse
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
import psycopg2
from psycopg2.extras import execute_values

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/screenscout")
CACHE_INVALIDATE_URL = os.getenv("CACHE_INVALIDATE_URL", "http://localhost:8080/api/cache/movies/invalidate")
BCRYPT_HASH = "$2a$10$FdySvp.Q17iF/Eq.xIhyJOG2/4fh0fVgO1nGzME6Ir8x2Rd.znhYC"  # Password123!

FIRST_NAMES = [
    "marcus", "clara", "weiliang", "ziyang", "chloe", "rachel", "aaron", "daniel",
    "nat", "eugene", "priya", "farhan", "clarence", "amanda", "gabriel", "valerie",
    "kevin", "stephanie", "benjamin", "denise", "justin", "meiling", "jason", "fiona",
    "leon", "hannah", "ryan", "hazel", "samuel", "carol", "dominic", "grace", "jun",
    "alicia", "bryan", "sheryl", "ian", "kelly", "jeremy", "celeste", "darren", "jasmine",
    "kenneth", "joanne", "lucas", "bernice", "nicholas", "evelyn", "vincent", "crystal",
    "gordon", "kayla", "desmond", "elaine", "edwin", "gillian", "victor", "michelle",
    "melvin", "audrey", "bernard", "charlene", "clifford", "daphne", "felix", "gemma",
    "howard", "irene", "joel", "karen", "lawrence", "monica", "norman", "olivia"
]

LAST_NAMES = [
    "tan", "lim", "lee", "ng", "ong", "wong", "goh", "chua", "chan", "koh",
    "teo", "chia", "tay", "ho", "low", "yeo", "sim", "chen", "soh", "seah",
    "phua", "neo", "kwok", "ang", "quek", "leong", "loo", "kuan", "choo", "kam",
    "kumar", "sharma", "nair", "singh", "patel", "menon", "fernandez", "rodrigues",
    "abdullah", "rahman", "ismail", "hassan", "yusof", "ibrahim", "osman", "daud"
]

INTEREST_PREFIXES = [
    "cinephile", "imax_junkie", "popcorn_critic", "reel_talk", "screen_scout",
    "midnight_movier", "sg_film_buff", "silver_screen", "cinema_goer", "indie_reel",
    "box_office_watcher", "film_fanatic", "movie_maverick", "flick_finder", "movielover"
]

REVIEW_TEMPLATES_5_STAR = [
    "Absolute masterpiece! The cinematography and pacing were on point from start to finish. A must-watch on the biggest cinema screen possible!",
    "One of the best cinematic experiences I've had in Singapore this year. The Dolby Atmos sound design made every scene hit so much harder.",
    "Exceeded all my expectations! The story was gripping, the acting was phenomenal, and the third act had the entire cinema hall holding their breath.",
    "Brilliant direction and worldbuilding. 10/10 would watch again at GV Max. Don't skip the post-credits!",
    "Flawless execution. The emotional beats resonated deeply and the visuals were breathtaking throughout. Deserves every award it gets.",
    "Incredible performance by the lead cast. Kept me on the edge of my seat the whole time. Best watch of the month!",
    "Stunning visuals and an airtight screenplay. Left the theatre completely blown away. Truly worth the ticket price!",
    "Caught the opening weekend screening at Shaw Lido — atmosphere was electric. This movie delivers on every single level."
]

REVIEW_TEMPLATES_4_STAR = [
    "Solid 4/5! Really engaging plot with great performances all around. Pacing dipped slightly in the middle, but the climax made up for it.",
    "Great movie for a Friday night out with friends. Visuals and soundtrack were stellar, just wished a few character arcs had more closure.",
    "Very entertaining watch. Kept me invested throughout. Definitely recommend watching it in cinema for the sound effects.",
    "Strong performances and slick direction. A few predictable tropes here and there, but overall a thoroughly enjoyable experience.",
    "Exceeded expectations! Fun, stylish, and well-acted. Would happily recommend to anyone looking for a good weekend flick.",
    "Really good film. The director did a fantastic job building tension. Popcorn was finished within 30 minutes because I couldn't look away!",
    "Engaging storyline and crisp cinematography. Just minor pacing hiccups, but overall high production quality.",
    "Super fun watch! Great crowd reactions in the hall tonight. Well worth catching on the big screen."
]

REVIEW_TEMPLATES_3_STAR = [
    "Decent watch overall. Good acting and decent action sequences, but the plot felt a bit generic and dragged in the second act.",
    "Average film. Had some great moments and funny lines, but nothing particularly groundbreaking. Good for casual watching.",
    "Not bad, but didn't quite live up to the hype. The visual effects were impressive, though the dialogue could have used some polish.",
    "A bit of a mixed bag. Strong first half, but the ending felt somewhat rushed. Still an okay weekend popcorn watch.",
    "Entertaining enough if you don't overthink the plot holes. Great sound design and solid lead performance saved it."
]

REVIEW_TEMPLATES_2_STAR = [
    "Pretty underwhelming unfortunately. Had high expectations given the cast, but the script was lackluster and predictable.",
    "Disappointing pacing and weak character development. Visuals were nice, but the story lacked genuine substance.",
    "Felt overly long and struggled to find its footing. A few decent scenes couldn't rescue the convoluted plot."
]

REVIEW_TEMPLATES_1_STAR = [
    "Really struggled to sit through this one. Clunky dialogue, confusing plot twists, and zero emotional connection to the characters.",
    "Way below expectations. Felt disjointed and poorly edited. Save your ticket money for something else."
]


def generate_username(index: int) -> str:
    r = random.random()
    if r < 0.55:
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        num = random.choice(["", str(random.randint(1, 99)), str(random.randint(80, 99)), str(random.randint(2000, 2024))])
        sep = random.choice(["_", ".", ""])
        return f"{first}{sep}{last}{num}"[:50]
    elif r < 0.85:
        prefix = random.choice(INTEREST_PREFIXES)
        suffix = random.choice(["sg", "singapore", "fan", "critic", "pro", str(random.randint(1, 999))])
        return f"{prefix}_{suffix}"[:50]
    else:
        first = random.choice(FIRST_NAMES)
        suffix = random.choice(["movies", "films", "cinema", "watcher", "fanatic", "sg"])
        return f"{first}_{suffix}"[:50]


def invalidate_backend_cache():
    try:
        req = urllib.request.Request(
            CACHE_INVALIDATE_URL,
            data=b"{}",
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                print("✓ Successfully invalidated movie cache in Go backend.")
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(
        description="Populate demo users and movie reviews in ScreenScout database."
    )
    parser.add_argument(
        "--reset",
        "--force",
        dest="reset",
        action="store_true",
        help="Wipe existing reviews and re-seed all movies from scratch."
    )
    args = parser.parse_args()

    print("🎬 Connecting to ScreenScout PostgreSQL database...")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # 1. Fetch existing movies
    cur.execute("SELECT id, title, genre FROM movies ORDER BY id;")
    all_movies = cur.fetchall()
    if not all_movies:
        print("❌ No movies found in database. Please scrape movies first.")
        cur.close()
        conn.close()
        return

    print(f"✓ Found {len(all_movies)} total movies in database.")

    # 2. Check existing users & ensure 1,256 users exist
    cur.execute("SELECT id, username FROM users;")
    existing_users = cur.fetchall()
    existing_usernames = set(u[1] for u in existing_users)
    print(f"✓ Current registered users: {len(existing_users)}")

    target_user_count = 1256
    needed_users = target_user_count - len(existing_users)

    if needed_users > 0:
        print(f"🌱 Generating {needed_users} realistic users to reach target {target_user_count:,}...")
        users_to_insert = []
        generated_names = set(existing_usernames)
        base_time = datetime.now(timezone.utc) - timedelta(days=120)

        idx = 1
        while len(users_to_insert) < needed_users:
            candidate = generate_username(idx)
            if candidate not in generated_names and len(candidate) >= 3:
                generated_names.add(candidate)
                created_at = base_time + timedelta(
                    days=random.uniform(0, 110),
                    minutes=random.uniform(0, 1440)
                )
                users_to_insert.append((
                    candidate,
                    BCRYPT_HASH,
                    created_at,
                    created_at
                ))
            idx += 1

        insert_user_query = """
        INSERT INTO users (username, hashed_password, created_at, updated_at)
        VALUES %s
        ON CONFLICT (username) DO NOTHING;
        """
        execute_values(cur, insert_user_query, users_to_insert)
        conn.commit()
        print(f"✓ Successfully added {needed_users} new users.")

    # Refresh all user list
    cur.execute("SELECT id, username, created_at FROM users ORDER BY id;")
    all_users = cur.fetchall()
    print(f"✓ Total available users in database: {len(all_users)}")

    # 3. Determine which movies to populate
    if args.reset:
        print("⚠️  --reset flag specified: Wiping existing reviews table...")
        cur.execute("TRUNCATE TABLE reviews RESTART IDENTITY CASCADE;")
        conn.commit()
        movies_to_populate = all_movies
        print(f"🍿 Seeding fresh reviews for all {len(movies_to_populate)} movies...")
    else:
        # Incremental mode: check which movies already have reviews
        cur.execute("SELECT DISTINCT movie_id FROM reviews;")
        reviewed_movie_ids = set(row[0] for row in cur.fetchall())

        movies_to_populate = [m for m in all_movies if m[0] not in reviewed_movie_ids]
        already_reviewed_count = len(all_movies) - len(movies_to_populate)

        print(f"ℹ️  Incremental Mode: {already_reviewed_count} movies already have reviews (kept intact).")
        if not movies_to_populate:
            print("✨ All movies in the database already have reviews! Nothing to populate.")
            print("   (To force a complete re-seed, run: python scripts/seed_demo_data.py --reset)")
            cur.close()
            conn.close()
            return

        print(f"🍿 Populating reviews for {len(movies_to_populate)} new unreviewed movie(s)...")

    # 4. Generate Reviews for the target movies
    reviews_to_insert = []

    for movie in movies_to_populate:
        movie_id, title, genre = movie

        # Random review count per movie (12 to 38 reviews)
        num_reviews = random.randint(12, 38)
        selected_users = random.sample(all_users, min(num_reviews, len(all_users)))

        for u in selected_users:
            user_id, username, user_created_at = u

            # Realistic rating probability distribution:
            # 5-star: 42%, 4-star: 36%, 3-star: 15%, 2-star: 5%, 1-star: 2%
            rand_val = random.random()
            if rand_val < 0.42:
                rating = 5
                content = random.choice(REVIEW_TEMPLATES_5_STAR)
            elif rand_val < 0.78:
                rating = 4
                content = random.choice(REVIEW_TEMPLATES_4_STAR)
            elif rand_val < 0.93:
                rating = 3
                content = random.choice(REVIEW_TEMPLATES_3_STAR)
            elif rand_val < 0.98:
                rating = 2
                content = random.choice(REVIEW_TEMPLATES_2_STAR)
            else:
                rating = 1
                content = random.choice(REVIEW_TEMPLATES_1_STAR)

            # Review timestamp must be after user registration
            review_time = user_created_at + timedelta(
                days=random.uniform(0, max(1, (datetime.now(timezone.utc) - user_created_at).days)),
                minutes=random.uniform(10, 1400)
            )
            if review_time > datetime.now(timezone.utc):
                review_time = datetime.now(timezone.utc) - timedelta(minutes=random.randint(5, 300))

            reviews_to_insert.append((
                movie_id,
                user_id,
                rating,
                content,
                review_time,
                review_time
            ))

    print(f"💾 Inserting {len(reviews_to_insert)} reviews into database...")
    insert_reviews_query = """
    INSERT INTO reviews (movie_id, user_id, rating, content, created_at, updated_at)
    VALUES %s
    ON CONFLICT (movie_id, user_id) DO NOTHING;
    """
    execute_values(cur, insert_reviews_query, reviews_to_insert)
    conn.commit()

    # Invalidate cache if backend is running
    invalidate_backend_cache()

    # 5. Summary & Verification
    cur.execute("SELECT COUNT(*) FROM users;")
    total_users_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*), AVG(rating) FROM reviews;")
    total_reviews_count, avg_rating = cur.fetchone()
    cur.execute("SELECT COUNT(DISTINCT movie_id) FROM reviews;")
    movies_with_reviews_count = cur.fetchone()[0]

    print("\n" + "=" * 60)
    print("🎉 SEED OPERATION COMPLETE!")
    print(f"   • Total Active Users in DB:     {total_users_count:,}")
    print(f"   • Movies with Reviews:          {movies_with_reviews_count:,} / {len(all_movies):,}")
    print(f"   • Total Movie Reviews in DB:    {total_reviews_count:,}")
    if avg_rating is not None:
        print(f"   • Average System Rating:        {avg_rating:.2f} / 5.0 ⭐")
    print(f"   • All users password:           Password123!")
    print("=" * 60 + "\n")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
