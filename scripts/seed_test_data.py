#!/usr/bin/env python3
"""
Seed Script: Populates high-variety authentic users and realistic movie reviews
across movies in the ScreenScout database.

User Archetypes Included:
1. Real Names & Initials (e.g. clara.lim94, marcus_tan, eugene.goh88, dr.wong)
2. Singapore Dialect & Local Names (e.g. tan_ah_teck, meiling.sg, ziyang_chen, quek_jun_jie)
3. Malay & Indian Cultural Names (e.g. farhan_rahman, nurfazira_98, priya_sharma, arun.kumar, syakir_ismail)
4. Cinephiles & Film Buffs (e.g. imax_junkie, ScreenJunkie99, gv_popcorn_fan, director_cut_only)
5. Casual Moviegoers & Snack Fans (e.g. popcorn_gobbler, sleeps_in_cinema, crying_at_gv, nacho_lover)
6. Aesthetic & Minimalist Handles (e.g. vibecheck.film, solocinema_, neon.reels, velvet_cinema)
7. Singapore Neighborhood Film Fans (e.g. kopitiam_critic, eastcoast_cinephile, jurong_filmgoer, vivocity_regular)
8. Gamer / Modern Social Handles (e.g. xX_MovieMaster_Xx, the_real_jason, CyberFlick)
9. Clean Short Handles & Initials (e.g. k.tan, j.lim_, wong.c, s.kumar)

Rules:
1. Status Rule:
   - "now_showing": release_date is null OR release_date <= CURRENT_DATE
   - "coming_soon": release_date > CURRENT_DATE
2. Reviews are ONLY seeded for movies that are "now_showing".
   "coming_soon" movies remain unreviewed and locked.
3. Repopulates database users and reviews with rich variety.
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
    "howard", "irene", "joel", "karen", "lawrence", "monica", "norman", "olivia",
    "patricia", "quentin", "rebecca", "simon", "tiffany", "ursula", "wendy", "xavier",
    "yvonne", "zachary", "ethan", "liam", "oliver", "noah", "emma", "ava", "sophia",
    "isabella", "mia", "charlotte", "amelia", "harper", "abigail", "elizabeth", "cynthia"
]

LAST_NAMES = [
    "tan", "lim", "lee", "ng", "ong", "wong", "goh", "chua", "chan", "koh",
    "teo", "chia", "tay", "ho", "low", "yeo", "sim", "chen", "soh", "seah",
    "phua", "neo", "kwok", "ang", "quek", "leong", "loo", "kuan", "choo", "kam",
    "kumar", "sharma", "nair", "singh", "patel", "menon", "fernandez", "rodrigues",
    "abdullah", "rahman", "ismail", "hassan", "yusof", "ibrahim", "osman", "daud",
    "hashim", "zulkifli", "mustafa", "razak", "anand", "pillai", "reddy", "iyer"
]

MALAY_FIRST = [
    "farhan", "amirul", "nurfazira", "haziq", "nurul", "syakir", "hafiz",
    "danish", "aiman", "farah", "aisyah", "harith", "firdaus", "nadia", "siti"
]

INDIAN_FIRST = [
    "priya", "arun", "rajesh", "deepa", "vikram", "ananya", "siddharth",
    "kavita", "rohit", "sneha", "rahul", "pooja", "arjun", "karan", "divya"
]

CHINESE_DIALECT_FIRST = [
    "ah_teck", "kian_seng", "meiling", "ziyang", "weiliang", "jiawei",
    "huiling", "jun_jie", "xin_yi", "zhi_hao", "shao_wei", "boon_heng", "kok_seng"
]

CINEPHILE_NOUNS = [
    "cinephile", "imax_junkie", "film_buff", "silver_screen", "reel_talk",
    "flick_finder", "cinema_goer", "movie_maverick", "boxoffice_fan", "celluloid_geek",
    "screen_scout", "director_cut", "4dx_addict", "dolby_enthusiast", "filmmaker_sg",
    "indie_reel", "midnight_watcher", "cinema_critic", "screen_junkie", "popcorn_critic"
]

CASUAL_FUN_HANDLES = [
    "popcorn_gobbler", "sleeps_in_cinema", "crying_at_gv", "nacho_lover", "trailer_addict",
    "midnight_snacker", "cinema_cat", "couch_potato_pro", "lazy_sunday_flicks", "coffee_and_movies",
    "plot_twist_hater", "noodlekid", "boba_and_film", "popcorn_fiend", "hall_hopper",
    "snoozing_in_goldclass", "candy_bar_regular", "front_row_regret"
]

AESTHETIC_HANDLES = [
    "vibecheck.film", "solocinema", "neon.reels", "velvet_cinema", "aurora_films",
    "mono_focus", "starlight_reel", "retro_cine", "echo_screen", "lunar_flicks",
    "cloud9_cinema", "noir_vibes", "prism_screen", "aesthetic_frames", "velvet_horizon",
    "ambient_cinema", "soft_focus_sg", "midnight_lumiere", "golden_hour_reels", "analog_flick"
]

SG_LOCAL_HANDLES = [
    "kopitiam_critic", "sg_moviefan", "eastcoast_cinephile", "jurong_filmgoer",
    "orchard_moviewatcher", "tampines_gv_regular", "singapore_filmfan", "shiok_movies",
    "lah_cinema", "bishan_movie_goer", "katong_flicker", "bugis_screenlover",
    "vivocity_regular", "bedok_movielover", "woodlands_filmbuff", "yishun_cinema_club"
]

REVIEW_TEMPLATES_5_STAR = [
    "Absolute masterpiece! The cinematography and pacing were on point from start to finish. A must-watch on the biggest cinema screen possible!",
    "One of the best cinematic experiences I've had in Singapore this year. The Dolby Atmos sound design made every scene hit so much harder.",
    "Exceeded all my expectations! The story was gripping, the acting was phenomenal, and the third act had the entire cinema hall holding their breath.",
    "Brilliant direction and worldbuilding. 10/10 would watch again at GV Max. Don't skip the post-credits!",
    "Flawless execution. The emotional beats resonated deeply and the visuals were breathtaking throughout. Deserves every award it gets.",
    "Incredible performance by the lead cast. Kept me on the edge of my seat the whole time. Best watch of the month!",
    "Stunning visuals and an airtight screenplay. Left the theatre completely blown away. Truly worth the ticket price!",
    "Caught the opening weekend screening at Shaw Lido — atmosphere was electric. This movie delivers on every single level.",
    "Such an immersive film! Took my friends to watch it and everyone agreed it's an easy 10/10. Great direction.",
    "Pure cinematic brilliance. The soundtrack and visual color palette alone were worth the admission ticket!"
]

REVIEW_TEMPLATES_4_STAR = [
    "Solid 4/5! Really engaging plot with great performances all around. Pacing dipped slightly in the middle, but the climax made up for it.",
    "Great movie for a Friday night out with friends. Visuals and soundtrack were stellar, just wished a few character arcs had more closure.",
    "Very entertaining watch. Kept me invested throughout. Definitely recommend watching it in cinema for the sound effects.",
    "Strong performances and slick direction. A few predictable tropes here and there, but overall a thoroughly enjoyable experience.",
    "Exceeded expectations! Fun, stylish, and well-acted. Would happily recommend to anyone looking for a good weekend flick.",
    "Really good film. The director did a fantastic job building tension. Popcorn was finished within 30 minutes because I couldn't look away!",
    "Engaging storyline and crisp cinematography. Just minor pacing hiccups, but overall high production quality.",
    "Super fun watch! Great crowd reactions in the hall tonight. Well worth catching on the big screen.",
    "Enjoyed it thoroughly! Solid character dynamics and impressive practical effects throughout the third act."
]

REVIEW_TEMPLATES_3_STAR = [
    "Decent watch overall. Good acting and decent action sequences, but the plot felt a bit generic and dragged in the second act.",
    "Average film. Had some great moments and funny lines, but nothing particularly groundbreaking. Good for casual watching.",
    "Not bad, but didn't quite live up to the hype. The visual effects were impressive, though the dialogue could have used some polish.",
    "A bit of a mixed bag. Strong first half, but the ending felt somewhat rushed. Still an okay weekend popcorn watch.",
    "Entertaining enough if you don't overthink the plot holes. Great sound design and solid lead performance saved it.",
    "Fun popcorn movie for a lazy afternoon. Nothing revolutionary, but it passes the time nicely."
]

REVIEW_TEMPLATES_2_STAR = [
    "Pretty underwhelming unfortunately. Had high expectations given the cast, but the script was lackluster and predictable.",
    "Disappointing pacing and weak character development. Visuals were nice, but the story lacked genuine substance.",
    "Felt overly long and struggled to find its footing. A few decent scenes couldn't rescue the convoluted plot.",
    "The trailers made it look much better than it actually was. Felt somewhat flat in the second half."
]

REVIEW_TEMPLATES_1_STAR = [
    "Really struggled to sit through this one. Clunky dialogue, confusing plot twists, and zero emotional connection to the characters.",
    "Way below expectations. Felt disjointed and poorly edited. Save your ticket money for something else."
]


def generate_varied_username(idx: int) -> str:
    """Generates authentic, diverse usernames across 9 distinct real-world styles with varied casing."""
    archetype = random.randint(1, 9)
    sep = random.choice(["_", ".", "", "_"])
    num = random.choice(["", str(random.randint(1, 99)), str(random.randint(80, 99)), str(random.randint(2000, 2024)), "88", "777", "99", ""])

    if archetype == 1:  # Real Full Names & Professional handles
        f, l = random.choice(FIRST_NAMES), random.choice(LAST_NAMES)
        prefix = random.choice(["", "", "", "dr.", "prof_", "hey.", "its_"])
        raw = f"{prefix}{f}{sep}{l}{num}"

    elif archetype == 2:  # Chinese & Dialect Names
        f = random.choice(CHINESE_DIALECT_FIRST)
        l = random.choice(LAST_NAMES[:25])
        raw = f"{f}{sep}{l}{num}" if random.random() < 0.6 else f"{l}_{f}{num}"

    elif archetype == 3:  # Malay & Indian Names
        is_malay = random.random() < 0.5
        f = random.choice(MALAY_FIRST if is_malay else INDIAN_FIRST)
        l = random.choice(LAST_NAMES[30:])
        raw = f"{f}{sep}{l}{num}"

    elif archetype == 4:  # Film Buffs & Cinephile handles
        noun = random.choice(CINEPHILE_NOUNS)
        tag = random.choice(["", "_sg", "_pro", ".sg", "_vip", str(random.randint(1, 999)), "_official"])
        raw = f"{noun}{tag}"

    elif archetype == 5:  # Casual / Fun / Popcorn Lovers
        h = random.choice(CASUAL_FUN_HANDLES)
        tag = random.choice(["", "_sg", "_", str(random.randint(1, 99)), "_real"])
        raw = f"{h}{tag}"

    elif archetype == 6:  # Aesthetic & Minimalist Social Handles
        h = random.choice(AESTHETIC_HANDLES)
        tag = random.choice(["", "_", ".sg", ".eth", "_x", str(random.randint(1, 99))])
        raw = f"{h}{tag}"

    elif archetype == 7:  # SG Local & Neighbourhood moviegoers
        h = random.choice(SG_LOCAL_HANDLES)
        tag = random.choice(["", "_", str(random.randint(1, 99)), "_club"])
        raw = f"{h}{tag}"

    elif archetype == 8:  # Gamer / Modern Social Handles
        f = random.choice(FIRST_NAMES)
        style = random.choice(["xx", "captain", "shadow", "cyber", "real"])
        if style == "xx":
            return f"xX_{f.title()}_Xx"[:40]
        elif style == "captain":
            return f"Captain{f.title()}"[:40]
        elif style == "shadow":
            return f"Shadow_{f}{num}"[:40]
        elif style == "cyber":
            return f"Cyber{f.title()}{num}"[:40]
        raw = f"the_real_{f}{num}"

    else:  # Short Initials & Modern Minimal Tags
        f = random.choice(FIRST_NAMES)
        l = random.choice(LAST_NAMES)
        raw = f"{f[0]}.{l}{num}" if random.random() < 0.5 else f"{f}_{l[0]}{num}"

    # Apply diverse casing styles: PascalCase, FULL_CAPITAL, Capitalized_Separators, or lowercase
    roll = random.random()
    if roll < 0.25:  # 25% PascalCase (e.g. MarcusTan, ClaraLim94, PopcornGobbler, TanAhTeck)
        cleaned = raw.replace(".", " ").replace("_", " ").replace("-", " ")
        parts = [p.capitalize() for p in cleaned.split()]
        return "".join(parts)[:40]
    elif roll < 0.40:  # 15% FULL CAPITAL CASE (e.g. MARCUS_TAN, CLARA_LIM, IMAX_SG, POPCORN_GOBBLER)
        return raw.upper()[:40]
    elif roll < 0.55:  # 15% Title with separators (e.g. Marcus_Tan, Clara.Lim94, Farhan_Rahman)
        sep_char = "_" if "_" in raw else "." if "." in raw else ""
        if sep_char:
            return sep_char.join(p.capitalize() for p in raw.split(sep_char))[:40]
        return raw.capitalize()[:40]

    # 45% Standard lowercase
    return raw.lower()[:40]


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
        description="Populate rich-variety demo users and reviews for now-showing movies."
    )
    parser.add_argument(
        "--incremental",
        dest="incremental",
        action="store_true",
        help="Only populate unreviewed now-showing movies without replacing existing users."
    )
    args = parser.parse_args()

    print("🎬 Connecting to ScreenScout PostgreSQL database...")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # 1. Fetch existing movies and classify by release date vs today
    cur.execute("SELECT id, title, genre, release_date FROM movies ORDER BY id;")
    all_movies = cur.fetchall()
    if not all_movies:
        print("❌ No movies found in database. Please scrape movies first.")
        cur.close()
        conn.close()
        return

    today = datetime.now(timezone.utc).date()
    now_showing_movies = [m for m in all_movies if m[3] is None or m[3] <= today]
    coming_soon_movies = [m for m in all_movies if m[3] is not None and m[3] > today]

    print(f"✓ Total movies in database:      {len(all_movies)}")
    print(f"   • Now Showing (<= {today}):    {len(now_showing_movies)} movies")
    print(f"   • Coming Soon (> {today}):     {len(coming_soon_movies)} movies (locked from reviews)")

    target_user_count = 1256

    if not args.incremental:
        print("\n✨ Repopulating database with fresh high-variety demo users and reviews...")
        # Clean reviews table
        cur.execute("TRUNCATE TABLE reviews RESTART IDENTITY CASCADE;")
        # Delete demo users (keeping any custom user ID <= 2 if needed)
        cur.execute("DELETE FROM users WHERE id > 2;")
        conn.commit()

        # Check remaining users
        cur.execute("SELECT username FROM users;")
        existing_names = set(r[0] for r in cur.fetchall())

        needed = target_user_count - len(existing_names)
        users_to_insert = []
        base_time = datetime.now(timezone.utc) - timedelta(days=120)

        idx = 1
        while len(users_to_insert) < needed:
            candidate = generate_varied_username(idx)
            if candidate not in existing_names and len(candidate) >= 3:
                existing_names.add(candidate)
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
        print(f"✓ Created {len(users_to_insert):,} high-variety demo users.")

    # Refresh user list
    cur.execute("SELECT id, username, created_at FROM users ORDER BY id;")
    all_users = cur.fetchall()
    print(f"✓ Total available users in DB:    {len(all_users):,}")

    # Determine which movies to populate
    if args.incremental:
        cur.execute("SELECT DISTINCT movie_id FROM reviews;")
        reviewed_movie_ids = set(row[0] for row in cur.fetchall())
        movies_to_populate = [m for m in now_showing_movies if m[0] not in reviewed_movie_ids]
        print(f"ℹ️  Incremental Mode: Populating {len(movies_to_populate)} unreviewed Now Showing movie(s)...")
    else:
        movies_to_populate = now_showing_movies
        print(f"🍿 Populating fresh reviews across all {len(movies_to_populate)} Now Showing movies...")

    # Generate Reviews for target Now Showing movies
    reviews_to_insert = []
    movie_review_stats = []

    for movie in movies_to_populate:
        movie_id, title, genre, release_date = movie

        # Determine realistic review count based on days since theatrical release
        if release_date is None:
            days_live = random.randint(14, 45)
        else:
            days_live = (today - release_date).days

        if days_live <= 0:
            # Released today (Opening Day): early audience & morning viewers
            num_reviews = random.randint(2, 6)
            stage_desc = "Released Today (Opening Day)"
        elif days_live <= 2:
            # Released 1-2 days ago (Opening Weekend)
            num_reviews = random.randint(6, 12)
            stage_desc = f"Opening Weekend ({days_live}d ago)"
        elif days_live <= 7:
            # 1st week in theatres
            num_reviews = random.randint(13, 24)
            stage_desc = f"Week 1 ({days_live}d ago)"
        elif days_live <= 21:
            # 2-3 weeks in theatres
            num_reviews = random.randint(25, 42)
            stage_desc = f"Week 2-3 ({days_live}d ago)"
        else:
            # Established / Seasoned run (1+ month)
            num_reviews = random.randint(45, 75)
            stage_desc = f"Established ({days_live}d ago)"

        selected_users = random.sample(all_users, min(num_reviews, len(all_users)))
        movie_review_stats.append((title, str(release_date), stage_desc, len(selected_users)))

        for u in selected_users:
            user_id, username, user_created_at = u

            # Realistic rating distribution: 5★ (42%), 4★ (36%), 3★ (15%), 2★ (5%), 1★ (2%)
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

            now = datetime.now(timezone.utc)
            if days_live <= 0:
                # Released today: reviews within the last few hours of today
                review_time = now - timedelta(minutes=random.randint(15, 600))
            else:
                # Distributed across release date up to now
                release_datetime = (
                    datetime(release_date.year, release_date.month, release_date.day, tzinfo=timezone.utc)
                    if release_date
                    else (now - timedelta(days=days_live))
                )
                start_datetime = max(user_created_at, release_datetime)
                if start_datetime < now:
                    review_time = start_datetime + timedelta(
                        days=random.uniform(0, max(0.1, (now - start_datetime).days)),
                        minutes=random.uniform(10, 1400)
                    )
                else:
                    review_time = now - timedelta(minutes=random.randint(15, 300))

            if review_time > now:
                review_time = now - timedelta(minutes=random.randint(5, 120))

            reviews_to_insert.append((
                movie_id,
                user_id,
                rating,
                content,
                review_time,
                review_time
            ))

    print(f"💾 Inserting {len(reviews_to_insert):,} reviews into database...")
    insert_reviews_query = """
    INSERT INTO reviews (movie_id, user_id, rating, content, created_at, updated_at)
    VALUES %s
    ON CONFLICT (movie_id, user_id) DO NOTHING;
    """
    execute_values(cur, insert_reviews_query, reviews_to_insert)
    conn.commit()

    # Clean any accidental coming-soon reviews
    cur.execute("DELETE FROM reviews WHERE movie_id IN (SELECT id FROM movies WHERE release_date > CURRENT_DATE);")
    conn.commit()

    # Invalidate cache
    invalidate_backend_cache()

    # Summary
    cur.execute("SELECT COUNT(*) FROM users;")
    total_users_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*), AVG(rating) FROM reviews;")
    total_reviews_count, avg_rating = cur.fetchone()
    cur.execute("SELECT COUNT(DISTINCT movie_id) FROM reviews;")
    movies_with_reviews_count = cur.fetchone()[0]

    # Sample some generated usernames
    cur.execute("SELECT username FROM users ORDER BY RANDOM() LIMIT 10;")
    sample_users = [r[0] for r in cur.fetchall()]

    print("\n" + "=" * 70)
    print("🎉 SEED & REPOPULATE COMPLETE!")
    print(f"   • Total Active Users in DB:        {total_users_count:,}")
    print(f"   • Now Showing Movies with Reviews: {movies_with_reviews_count:,} / {len(now_showing_movies):,}")
    print(f"   • Coming Soon Movies (Locked):     {len(coming_soon_movies):,}")
    print(f"   • Total Movie Reviews in DB:       {total_reviews_count:,}")
    if avg_rating is not None:
        print(f"   • Average System Rating:           {avg_rating:.2f} / 5.0 ⭐")
    print(f"   • All users password:              Password123!")

    print("\n📊 Sample Movies Release Date vs Review Counts:")
    # Sort sample by count ascending
    for title, rel_date, stage, cnt in sorted(movie_review_stats, key=lambda x: x[3])[:8]:
        print(f"   • {title[:32]:<32} | Rel: {rel_date} ({stage:<24}) -> {cnt:>2} reviews")
    if len(movie_review_stats) > 8:
        for title, rel_date, stage, cnt in sorted(movie_review_stats, key=lambda x: x[3])[-4:]:
            print(f"   • {title[:32]:<32} | Rel: {rel_date} ({stage:<24}) -> {cnt:>2} reviews")

    print("\n✨ Sample Varied Usernames:")
    for uname in sample_users:
        print(f"     - {uname}")
    print("=" * 70 + "\n")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
