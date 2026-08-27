#!/usr/bin/env python3
"""
Seed Script: Populates high-variety authentic users and realistic, context-aware movie reviews
across movies in the ScreenScout database.

Key Features:
1. Context-Aware Content:
   - Reviews reference the movie's title, genre, synopsis / description premise, director, and cast members.
2. Varied Review Lengths:
   - Ultra-Short / One-Liners (15%): Punchy cinema reactions ("10/10 masterclass in sci-fi.", "Loved every minute!")
   - Short (35%): 1-2 sentence reactions referencing lead actors, sound mix, and cinema venues (GV, Shaw Lido, etc.).
   - Medium (35%): 2-4 sentences exploring the synopsis premise, acting dynamics, and thematic pacing.
   - Detailed In-Depth Critique (15%): Comprehensive cinephile analysis covering direction, score, and cinematography.
3. Release-Date Weighted Review Counts:
   - Opening Day (Today): 2–6 fresh reviews from earlier today.
   - Opening Weekend (1–2d): 6–12 reviews.
   - Week 1 (3–7d): 13–24 reviews.
   - Week 2–3 (8–21d): 25–42 reviews.
   - Established (1+ month): 45–75 reviews.
   - Coming Soon: 0 reviews (locked).
4. Multi-Archetype Usernames with Varied Casing:
   - PascalCase, FULL_CAPITAL, TitleCase with separators, Gamer/Stylized, and Lowercase.
"""

import os
import sys
import re
import json
import random
import argparse
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
import psycopg2
from psycopg2.extras import execute_values

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/screenscout")
CACHE_INVALIDATE_URL = os.getenv("CACHE_INVALIDATE_URL", "http://localhost:8080/api/cache/movies/invalidate")
BCRYPT_HASH = "$2a$10$E94AjriKZC2Jq3O/yuoS9eTFYEIqKHHH.umblOjp9WmO7E8oxzoTm"  # Password123!

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

THEATRES = [
    "GV Max", "Shaw Lido IMAX", "GV Vivocity", "Shaw Theatres Jewel",
    "GV Plaza", "Shaw Paya Lebar", "GV Suntec City", "the big screen",
    "IMAX with Laser", "Dolby Atmos hall", "Shaw IMAX", "GV Gold Class"
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
    if roll < 0.25:  # 25% PascalCase
        cleaned = raw.replace(".", " ").replace("_", " ").replace("-", " ")
        parts = [p.capitalize() for p in cleaned.split()]
        return "".join(parts)[:40]
    elif roll < 0.40:  # 15% FULL CAPITAL CASE
        return raw.upper()[:40]
    elif roll < 0.55:  # 15% Title with separators
        sep_char = "_" if "_" in raw else "." if "." in raw else ""
        if sep_char:
            return sep_char.join(p.capitalize() for p in raw.split(sep_char))[:40]
        return raw.capitalize()[:40]

    # 45% Standard lowercase
    return raw.lower()[:40]


def extract_clean_movie_metadata(title: str, genre: str, director: str, casts: str, description: str):
    """Extracts cleaned entities and synopsis hook for contextual review writing."""
    clean_title = re.sub(r"\s*[\*]+\s*", "", title)
    clean_title = re.sub(r"\s*\((?:Reissue|25th Anniversary|M|PG13|NC16|R21|35mm|Live From [^)]+)\)", "", clean_title, flags=re.IGNORECASE).strip()
    if not clean_title:
        clean_title = title

    # Lead Actor / Duo
    lead_actor = ""
    if casts:
        actors = [a.strip() for a in re.split(r"[,/|]| and ", casts) if a.strip()]
        if actors:
            lead_actor = actors[0]
            if len(actors) > 1 and random.random() < 0.35:
                lead_actor = f"{actors[0]} and {actors[1]}"

    # Primary Genre
    primary_genre = (genre.split("/")[0].split(",")[0].strip().lower() if genre else "movie")
    if not primary_genre:
        primary_genre = "film"

    # Synopsis Premise / Hook
    plot_hook = ""
    if description:
        cleaned_desc = re.sub(r"\s+", " ", description).strip()
        sentences = [s.strip() for s in re.split(r'(?<!\b[A-Z])(?<=[.!?])\s+', cleaned_desc) if s.strip()]
        if sentences:
            s0 = sentences[0].rstrip(".")
            if len(s0) > 135:
                s0 = s0[:132] + "..."
            plot_hook = s0

    return clean_title, primary_genre, director or "", lead_actor, plot_hook


def generate_contextual_review(
    title: str,
    genre: str,
    director: str,
    casts: str,
    description: str,
    rating: int
) -> str:
    """Generates authentic reviews spanning 4 distinct length tiers with contextual references."""
    clean_title, primary_genre, dir_name, lead_actor, plot_hook = extract_clean_movie_metadata(
        title, genre, director, casts, description
    )
    theatre = random.choice(THEATRES)

    # Choose length tier:
    # Tier 1: One-liner / Ultra-short (15%)
    # Tier 2: Short (1-2 sentences) (35%)
    # Tier 3: Medium (2-4 sentences with synopsis/actors) (35%)
    # Tier 4: In-depth cinephile critique (15%)
    length_tier = random.random()

    # -------------------------------------------------------------
    # TIER 1: ULTRA-SHORT / ONE-LINERS (15%)
    # -------------------------------------------------------------
    if length_tier < 0.15:
        if rating == 5:
            return random.choice([
                f"Absolute masterpiece. 10/10.",
                f"Peak cinema! Loved every second of {clean_title}.",
                f"Best watch of the month. Must catch in {theatre}!",
                f"Flawless from start to finish.",
                f"10/10 masterclass in {primary_genre}.",
                f"Stunning visuals and emotional storytelling. Loved it!",
                f"Deserves all the awards. Incredible watch!",
                f"Pure cinematic perfection.",
                f"Hands down the best film I've watched all year."
            ])
        elif rating == 4:
            return random.choice([
                f"Solid 4/5! Really fun Friday night watch.",
                f"Super enjoyable film, {lead_actor or 'the cast'} did great.",
                f"Exceeded my expectations. Great crowd energy tonight.",
                f"Thoroughly entertaining {primary_genre} flick.",
                f"Very good movie! Soundtrack was on point.",
                f"4/5. Great visuals and solid pacing."
            ])
        elif rating == 3:
            return random.choice([
                f"Decent watch, good for a casual weekend afternoon.",
                f"Not bad, but nothing mindblowing.",
                f"Average {primary_genre} flick. Has some fun moments.",
                f"Okay watch if you don't overthink the plot.",
                f"A bit predictable, but still entertaining enough."
            ])
        elif rating == 2:
            return random.choice([
                f"Pretty underwhelming unfortunately.",
                f"Didn't live up to the trailer hype.",
                f"Pacing was way too slow in the middle.",
                f"Disappointing script despite a promising premise."
            ])
        else:
            return random.choice([
                f"Really struggled to sit through this. Skip it.",
                f"Waste of ticket money unfortunately.",
                f"Clunky dialogue and confusing plot. 1/5."
            ])

    # -------------------------------------------------------------
    # TIER 2: SHORT (1-2 sentences) (35%)
    # -------------------------------------------------------------
    elif length_tier < 0.50:
        if rating == 5:
            actor_shout = f"{lead_actor} was phenomenal." if lead_actor else "The entire cast was phenomenal."
            dir_shout = f" by {dir_name}" if dir_name else ""
            return random.choice([
                f"Caught {clean_title} at {theatre} tonight — the atmosphere was electric! {actor_shout}",
                f"One of the best {primary_genre} experiences I've had all year. The Dolby Atmos sound design made every sequence hit so much harder.",
                f"{clean_title} delivered on every single level. Stunning visual effects and an airtight screenplay that kept me on the edge of my seat.",
                f"Brilliant direction{dir_shout} and an unforgettable soundtrack. Don't leave before the credits finish!",
                f"Exceeded all expectations! The chemistry between the characters and the emotional climax were breathtaking."
            ])
        elif rating == 4:
            actor_intro = f"{lead_actor} shines in their role, and " if lead_actor else ""
            return random.choice([
                f"Really strong {primary_genre} release. {actor_intro}the pacing keeps you invested right until the final act.",
                f"Great movie for a night out with friends. A few predictable moments, but the climax more than made up for it!",
                f"Very stylish and well-acted. {clean_title} is definitely worth catching on the big screen for the sound design.",
                f"Solid 4 stars. Pacing dipped slightly in the middle, but the action and emotional beats landed nicely."
            ])
        elif rating == 3:
            return random.choice([
                f"Entertaining enough for a casual weekend watch. The visual effects were great, though the dialogue could have used some polish.",
                f"A bit of a mixed bag. {clean_title} started strong, but the second half felt somewhat rushed.",
                f"Good popcorn flick with some funny lines and nice cinematography, but it follows a pretty standard formula.",
                f"Decent watch overall. {lead_actor or 'The cast'} did what they could with a relatively predictable script."
            ])
        elif rating == 2:
            return random.choice([
                f"Had high expectations given the cast, but the script felt lackluster and the characters lacked real depth.",
                f"Felt overly long and struggled to find its footing. A few decent scenes couldn't rescue the convoluted plot.",
                f"The trailers made {clean_title} look much better than it actually was. Quite flat in execution."
            ])
        else:
            return random.choice([
                f"Way below expectations. Felt disjointed, poorly edited, and failed to connect emotionally.",
                f"Save your ticket money for something else. A frustrating watch from start to finish."
            ])

    # -------------------------------------------------------------
    # TIER 3: MEDIUM (2-4 sentences with synopsis context) (35%)
    # -------------------------------------------------------------
    elif length_tier < 0.85:
        if rating == 5:
            synopsis_part = f"The premise around {plot_hook.lower()} is handled with remarkable depth and suspense." if plot_hook else "The central storyline is captivating from the opening scene."
            actor_part = f"{lead_actor} gives an exceptional performance that grounds the entire film." if lead_actor else "The performances across the board are top tier."
            dir_part = f"Director {dir_name} created an airtight vision." if dir_name else "The visual direction is breathtaking."
            return f"{clean_title} is a standout achievement in the {primary_genre} genre. {synopsis_part} {actor_part} {dir_part} Easily one of my favorite cinema experiences this year in Singapore."

        elif rating == 4:
            synopsis_part = f"The way the story unfolds around {plot_hook.lower()} keeps you engaged throughout." if plot_hook else "The storyline moves at a brisk pace with great set pieces."
            actor_part = f"{lead_actor} brings great charisma to the screen." if lead_actor else "The lead acting is solid and authentic."
            return f"I had a great time watching {clean_title} at {theatre}. {synopsis_part} {actor_part} While the third act wrapped up slightly faster than expected, the overall journey was thoroughly entertaining and well worth the admission."

        elif rating == 3:
            synopsis_part = f"the plot regarding {plot_hook.lower()}" if plot_hook else "the main plot"
            return f"{clean_title} has plenty of enjoyable elements, especially the visual aesthetics and sound design. However, {synopsis_part} loses some momentum midway through. It's a fun popcorn watch for fans of {primary_genre}, but don't expect a groundbreaking narrative."

        elif rating == 2:
            actor_part = f"talented actors like {lead_actor}" if lead_actor else "a promising premise"
            return f"Unfortunately, {clean_title} didn't quite hit the mark for me. Despite {actor_part}, the screenplay felt underdeveloped and leaned too heavily on generic clichés. The visuals in {theatre} were nice, but the emotional core was lacking."

        else:
            return f"A disappointing execution all around. {clean_title} struggles with awkward dialogue, jarring tonal shifts, and repetitive sequences. Even the climax fell completely flat after two hours of buildup."

    # -------------------------------------------------------------
    # TIER 4: DETAILED / IN-DEPTH CINEPHILE CRITIQUE (15%)
    # -------------------------------------------------------------
    else:
        if rating == 5:
            dir_clause = f"Director {dir_name} demonstrates complete mastery over pacing and visual tone, " if dir_name else "The direction demonstrates remarkable poise and cinematic ambition, "
            plot_clause = f"exploring {plot_hook.lower()} with genuine nuance and emotional weight. " if plot_hook else "crafting a rich, immersive world from the very first frame. "
            actor_clause = f"The performance by {lead_actor} anchors the emotional stakes, " if lead_actor else "The lead performances anchor the emotional stakes, "
            return (
                f"As an avid filmgoer, {clean_title} was everything I hoped for and more on the big screen. "
                f"{dir_clause}{plot_clause}"
                f"{actor_clause}elevating what could have been a standard {primary_genre} into a deeply memorable cinematic experience. "
                f"The sound mix and cinematography in {theatre} were reference-quality. A must-watch in theatres — 5/5 stars without hesitation."
            )

        elif rating == 4:
            actor_clause = f"{lead_actor} delivers a compelling lead performance that drives the tension, " if lead_actor else "The cast delivers grounded, authentic performances that drive the tension, "
            return (
                f"A thoroughly crafted and entertaining entry in modern {primary_genre} cinema. "
                f"{clean_title} succeeds largely because of its sharp dialogue, atmospheric worldbuilding, and memorable set pieces. "
                f"{actor_clause}"
                f"especially during the high-stakes sequences in the second half. "
                f"While a few secondary subplots felt slightly compressed for runtime, the overarching story delivers solid emotional and visual payoff. Highly recommended for a weekend cinema session!"
            )

        elif rating == 3:
            plot_clause = f"the core narrative surrounding {plot_hook.lower()} takes a backseat to familiar tropes " if plot_hook else "the script relies somewhat heavily on predictable formulas "
            return (
                f"{clean_title} delivers plenty of visual spectacle, but leaves a bit to be desired on the narrative front. "
                f"The production values, practical effects, and audio mixing are undeniably high quality, creating a great sensory experience in {theatre}. "
                f"However, {plot_clause}during the middle hour. Still an enjoyable weekend movie if you're looking for slick entertainment with popcorn and drinks."
            )

        elif rating == 2:
            dir_clause = f"{dir_name}'s direction and " if dir_name else ""
            return (
                f"I really wanted to love {clean_title}, especially given {dir_clause}the intriguing setup. "
                f"Unfortunately, the execution falls victim to uneven pacing and uninspired character choices. "
                f"The visual effects are decent, but they can't compensate for a screenplay that drags without meaningful emotional stakes. "
                f"Worth waiting for streaming rather than paying full cinema ticket prices."
            )

        else:
            return (
                f"A deeply frustrating watch. {clean_title} suffers from wooden dialogue, disjointed editing, and a runtime that feels far longer than it should. "
                f"None of the character motivations feel earned, and the final revelation lands with a thud. Definitely one to skip."
            )


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


POPULAR_UPCOMING_TITLES = [
    "Avatar: Fire and Ash", "Avengers: Doomsday", "Spider-Man: Beyond the Spider-Verse",
    "Batman: Part II", "Wicked: For Good", "Toy Story 5", "Shrek 5", "Dune: Part Three",
    "Tron: Ares", "Zootopia 2", "Fantastic Four: First Steps", "Blade", "Superman",
    "Jurassic World Rebirth", "Fast XI", "Star Wars: New Jedi Order", "How to Train Your Dragon",
    "Captain America: Brave New World", "Moana 2", "Mufasa: The Lion King", "Kraven the Hunter",
    "Paddington in Peru", "Sonic the Hedgehog 3", "Nosferatu", "Mission: Impossible - The Final Reckoning",
    "Interstellar 10th Anniversary", "Demon Slayer: Infinity Castle", "Chainsaw Man - The Movie"
]

GENRE_THEME_QUERIES = [
    "IMAX 3D", "Anime", "Marvel", "DC Universe", "Studio Ghibli", "Disney Animation",
    "Christopher Nolan", "Horror Night", "Korean Cinema", "Japanese Film Festival"
]


def seed_tracking_tasks(cur, conn, all_users, all_movies_rows, incremental=False):
    print("\n🔔 Seeding realistic screening tracking tasks & notification channels across all users...")

    # 1. Ensure Schema
    cur.execute("""
    CREATE TABLE IF NOT EXISTS notification_channels (
        id                  BIGINT PRIMARY KEY,
        user_id             BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        channel_type        VARCHAR(20) NOT NULL CHECK (
                                channel_type IN ('TELEGRAM', 'WECHAT', 'WHATSAPP', 'EMAIL', 'DISCORD')
                            ),
        channel_user_id     VARCHAR(255) NOT NULL,
        is_enabled          BOOLEAN NOT NULL DEFAULT TRUE,
        created_at          TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Singapore'),
        updated_at          TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Singapore'),
        UNIQUE (user_id, channel_type)
    );
    CREATE SEQUENCE IF NOT EXISTS notification_channels_id_seq START WITH 1 INCREMENT BY 1;
    ALTER TABLE notification_channels ALTER COLUMN id SET DEFAULT nextval('notification_channels_id_seq');
    CREATE INDEX IF NOT EXISTS idx_notification_channels_user ON notification_channels(user_id);

    CREATE TABLE IF NOT EXISTS subscriptions (
        id                  BIGINT PRIMARY KEY,
        user_id             BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        movie_query         VARCHAR(255) NOT NULL,
        is_active           BOOLEAN NOT NULL DEFAULT TRUE,
        matched_movie_id    BIGINT REFERENCES movies(id) ON DELETE SET NULL,
        matched_movie_title VARCHAR(255),
        matched_movies      JSONB DEFAULT '[]'::jsonb,
        triggered_at        TIMESTAMPTZ,
        created_at          TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Singapore'),
        updated_at          TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Singapore')
    );
    CREATE SEQUENCE IF NOT EXISTS subscriptions_id_seq START WITH 1 INCREMENT BY 1;
    ALTER TABLE subscriptions ALTER COLUMN id SET DEFAULT nextval('subscriptions_id_seq');
    CREATE INDEX IF NOT EXISTS idx_subscriptions_user ON subscriptions(user_id);
    CREATE INDEX IF NOT EXISTS idx_subscriptions_active ON subscriptions(is_active);

    CREATE TABLE IF NOT EXISTS notification_logs (
        id                  BIGINT PRIMARY KEY,
        subscription_id     BIGINT REFERENCES subscriptions(id) ON DELETE CASCADE,
        user_id             BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        channel_type        VARCHAR(20) NOT NULL,
        recipient           VARCHAR(255) NOT NULL,
        message             TEXT NOT NULL,
        status              VARCHAR(20) NOT NULL DEFAULT 'SENT',
        created_at          TIMESTAMPTZ NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Singapore')
    );
    CREATE SEQUENCE IF NOT EXISTS notification_logs_id_seq START WITH 1 INCREMENT BY 1;
    ALTER TABLE notification_logs ALTER COLUMN id SET DEFAULT nextval('notification_logs_id_seq');
    CREATE INDEX IF NOT EXISTS idx_notification_logs_user ON notification_logs(user_id);
    """)
    conn.commit()

    if not incremental:
        cur.execute("TRUNCATE TABLE notification_logs, subscriptions, notification_channels RESTART IDENTITY CASCADE;")
        conn.commit()

    # 2. Build movie lookup map
    today = datetime.now(timezone.utc).date()
    movies_by_id = {}
    db_movie_titles = []
    for row in all_movies_rows:
        m_id, m_title, m_genre, m_rel_date, m_dir, m_casts, m_desc = row[:7]
        m_provider = row[7] if len(row) > 7 else "GV"
        m_poster = row[8] if len(row) > 8 else None

        status = "now_showing" if (m_rel_date is None or m_rel_date <= today) else "coming_soon"
        movies_by_id[m_id] = {
            "id": m_id,
            "title": m_title,
            "provider": m_provider,
            "status": status,
            "release_date": str(m_rel_date) if m_rel_date else None,
            "poster_url": m_poster or ""
        }
        db_movie_titles.append((m_id, m_title))

    clean_titles = [m_title for _, m_title in db_movie_titles]

    # 3. Notification Channels for users
    channels_to_insert = []
    for user_id, username, user_created_at in all_users:
        clean_handle = username.lower().replace(".", "_").replace("-", "_")
        tg_handle = f"@{clean_handle}"
        channels_to_insert.append((
            user_id,
            "TELEGRAM",
            tg_handle,
            True,
            user_created_at,
            user_created_at
        ))

    insert_channels_query = """
    INSERT INTO notification_channels (user_id, channel_type, channel_user_id, is_enabled, created_at, updated_at)
    VALUES %s
    ON CONFLICT (user_id, channel_type) DO UPDATE SET channel_user_id = EXCLUDED.channel_user_id, updated_at = EXCLUDED.updated_at;
    """
    execute_values(cur, insert_channels_query, channels_to_insert)
    conn.commit()
    print(f"✓ Provisioned {len(channels_to_insert):,} Telegram notification channels.")

    # 4. Subscriptions & Tracking Tasks
    subscriptions_to_insert = []
    now = datetime.now(timezone.utc)

    admin_user = next((u for u in all_users if u[1] == "admin"), None)
    admin_id = admin_user[0] if admin_user else None

    for user_id, username, user_created_at in all_users:
        if user_id == admin_id:
            task_specs = [
                ("Spider-Man", True),
                ("Harry Potter", True),
                ("Avatar: Fire and Ash", False),
                ("Wicked: For Good", False)
            ]
        else:
            num_tasks = random.choices([1, 2, 3, 4], weights=[40, 35, 18, 7])[0]
            pool = clean_titles + POPULAR_UPCOMING_TITLES + GENRE_THEME_QUERIES
            selected_queries = random.sample(pool, min(num_tasks, len(pool)))
            task_specs = [(q, None) for q in selected_queries]

        for query, force_trigger in task_specs:
            matched_items = []
            q_lower = query.lower()
            for m_id, m_data in movies_by_id.items():
                if q_lower in m_data["title"].lower() or any(w in m_data["title"].lower() for w in q_lower.split() if len(w) > 3):
                    matched_items.append(m_data)

            start_time = max(user_created_at, now - timedelta(days=60))
            task_created_at = start_time + timedelta(
                days=random.uniform(0, max(0.1, (now - start_time).days)),
                minutes=random.uniform(0, 1400)
            )
            if task_created_at > now:
                task_created_at = now - timedelta(minutes=random.randint(10, 180))

            if matched_items and (force_trigger is True or (force_trigger is None and random.random() < 0.65)):
                top_match = matched_items[0]
                matched_id = top_match["id"]
                matched_title = top_match["title"]
                matched_json = json.dumps(matched_items[:3])
                triggered_time = task_created_at + timedelta(
                    days=random.uniform(0, max(0.1, (now - task_created_at).days)),
                    minutes=random.uniform(10, 300)
                )
                if triggered_time > now:
                    triggered_time = now - timedelta(minutes=random.randint(5, 60))

                is_active = random.random() < 0.85
                subscriptions_to_insert.append((
                    user_id,
                    query,
                    is_active,
                    matched_id,
                    matched_title,
                    matched_json,
                    triggered_time,
                    task_created_at,
                    triggered_time
                ))
            else:
                subscriptions_to_insert.append((
                    user_id,
                    query,
                    True,
                    None,
                    None,
                    '[]',
                    None,
                    task_created_at,
                    task_created_at
                ))

    insert_sub_query = """
    INSERT INTO subscriptions (user_id, movie_query, is_active, matched_movie_id, matched_movie_title, matched_movies, triggered_at, created_at, updated_at)
    VALUES %s;
    """
    execute_values(cur, insert_sub_query, subscriptions_to_insert)
    conn.commit()
    print(f"✓ Created {len(subscriptions_to_insert):,} movie tracking tasks across all users.")

    # 5. Notification Logs for Triggered Subscriptions
    cur.execute("""
        SELECT s.id, s.user_id, s.movie_query, s.matched_movie_title, s.triggered_at, u.username, nc.channel_user_id
        FROM subscriptions s
        JOIN users u ON u.id = s.user_id
        LEFT JOIN notification_channels nc ON nc.user_id = s.user_id AND nc.channel_type = 'TELEGRAM'
        WHERE s.triggered_at IS NOT NULL;
    """)
    triggered_subs = cur.fetchall()

    logs_to_insert = []
    for sub_id, u_id, m_query, m_title, trig_at, uname, chan_id in triggered_subs:
        recipient = chan_id or f"@{uname}"
        msg = f"🎬 ScreenScout Screening Alert!\n\nHey {uname}! Screenings for your tracked movie \"{m_query}\" are now live in Singapore cinemas!\n\n📍 Matched: {m_title or m_query}\n🎟️ Bookings are now open across participating locations."
        logs_to_insert.append((
            sub_id,
            u_id,
            "TELEGRAM",
            recipient,
            msg,
            "SENT",
            trig_at
        ))

    if logs_to_insert:
        insert_logs_query = """
        INSERT INTO notification_logs (subscription_id, user_id, channel_type, recipient, message, status, created_at)
        VALUES %s;
        """
        execute_values(cur, insert_logs_query, logs_to_insert)
        conn.commit()
        print(f"✓ Generated {len(logs_to_insert):,} realistic Telegram notification alert logs.")


def main():
    parser = argparse.ArgumentParser(
        description="Populate rich-variety demo users, context-aware reviews, and tracking tasks."
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

    # 1. Fetch existing movies with full metadata (title, genre, release_date, director, casts, description, provider, poster_url)
    cur.execute("""
        SELECT id, title, genre, release_date, director, casts, description, provider, poster_url
        FROM movies
        ORDER BY id;
    """)
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
        # Ensure admin user has admin role, valid password, and exact requested 2024-08-23 15:23 SG join date
        cur.execute(
            "UPDATE users SET role = 'admin', hashed_password = %s, created_at = '2024-08-23 15:23:00+08:00', updated_at = '2024-08-23 15:23:00+08:00' WHERE username = 'admin';",
            (BCRYPT_HASH,)
        )
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
                    "user",
                    created_at,
                    created_at
                ))
            idx += 1

        insert_user_query = """
        INSERT INTO users (username, hashed_password, role, created_at, updated_at)
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
        target_movies = [m for m in now_showing_movies if m[0] not in reviewed_movie_ids]
        print(f"✓ Found {len(target_movies)} unreviewed movies to seed (incremental mode).")
    else:
        target_movies = now_showing_movies

    reviews_to_insert = []
    movie_review_stats = []

    print("\n📝 Generating realistic, context-aware reviews for now-showing movies...")
    for movie in target_movies:
        movie_id, title, genre, release_date, director, casts, description = movie[:7]

        # Calculate days since release
        if release_date:
            days_live = (today - release_date).days
        else:
            days_live = random.randint(14, 60)

        # Release-date weighted review distribution
        if days_live <= 0:
            num_reviews = random.randint(2, 6)
            stage_desc = f"Opening Day ({days_live}d)"
        elif days_live <= 2:
            num_reviews = random.randint(6, 12)
            stage_desc = f"Opening Weekend ({days_live}d ago)"
        elif days_live <= 7:
            num_reviews = random.randint(13, 24)
            stage_desc = f"Week 1 ({days_live}d ago)"
        elif days_live <= 21:
            num_reviews = random.randint(25, 42)
            stage_desc = f"Week 2-3 ({days_live}d ago)"
        else:
            num_reviews = random.randint(45, 75)
            stage_desc = f"Established ({days_live}d ago)"

        selected_users = random.sample(all_users, min(num_reviews, len(all_users)))
        movie_review_stats.append((title, str(release_date), stage_desc, len(selected_users)))

        for u in selected_users:
            user_id, username, user_created_at = u

            rand_val = random.random()
            if rand_val < 0.42:
                rating = 5
            elif rand_val < 0.78:
                rating = 4
            elif rand_val < 0.93:
                rating = 3
            elif rand_val < 0.98:
                rating = 2
            else:
                rating = 1

            content = generate_contextual_review(
                title=title,
                genre=genre or "",
                director=director or "",
                casts=casts or "",
                description=description or "",
                rating=rating
            )

            now = datetime.now(timezone.utc)
            if days_live <= 0:
                review_time = now - timedelta(minutes=random.randint(15, 600))
            else:
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

    print(f"💾 Inserting {len(reviews_to_insert):,} context-aware reviews into database...")
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

    # 4. Seed Subscriptions / Tracking Tasks
    seed_tracking_tasks(cur, conn, all_users, all_movies, args.incremental)

    # Invalidate cache
    invalidate_backend_cache()

    # Summary
    cur.execute("SELECT COUNT(*) FROM users;")
    total_users_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*), AVG(rating) FROM reviews;")
    total_reviews_count, avg_rating = cur.fetchone()
    cur.execute("SELECT COUNT(DISTINCT movie_id) FROM reviews;")
    movies_with_reviews_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*), COUNT(CASE WHEN is_active THEN 1 END), COUNT(CASE WHEN triggered_at IS NOT NULL THEN 1 END) FROM subscriptions;")
    total_subs, active_subs, triggered_subs_cnt = cur.fetchone()

    cur.execute("SELECT COUNT(*) FROM notification_logs;")
    total_notif_logs = cur.fetchone()[0]

    # Sample some generated usernames
    cur.execute("SELECT username FROM users ORDER BY RANDOM() LIMIT 10;")
    sample_users = [r[0] for r in cur.fetchall()]

    # Sample admin subscriptions
    cur.execute("""
        SELECT s.movie_query, s.is_active, s.matched_movie_title, s.triggered_at
        FROM subscriptions s
        JOIN users u ON u.id = s.user_id
        WHERE u.username = 'admin';
    """)
    admin_tasks = cur.fetchall()

    print("\n" + "=" * 70)
    print("🎉 SEED & REPOPULATE COMPLETE!")
    print(f"   • Total Active Users in DB:        {total_users_count:,}")
    print(f"   • Now Showing Movies with Reviews: {movies_with_reviews_count:,} / {len(now_showing_movies):,}")
    print(f"   • Coming Soon Movies (Locked):     {len(coming_soon_movies):,}")
    print(f"   • Total Movie Reviews in DB:       {total_reviews_count:,}")
    if avg_rating is not None:
        print(f"   • Average System Rating:           {avg_rating:.2f} / 5.0 ⭐")
    print(f"   • Total Screening Tracking Tasks:  {total_subs:,} ({active_subs:,} active, {triggered_subs_cnt:,} triggered)")
    print(f"   • Dispatched Notification Logs:    {total_notif_logs:,}")
    print(f"   • All users password:              Password123!")

    print("\n📊 Sample Movies Release Date vs Review Counts:")
    for title, rel_date, stage, cnt in sorted(movie_review_stats, key=lambda x: x[3])[:6]:
        print(f"   • {title[:32]:<32} | Rel: {rel_date} ({stage:<24}) -> {cnt:>2} reviews")
    if len(movie_review_stats) > 6:
        for title, rel_date, stage, cnt in sorted(movie_review_stats, key=lambda x: x[3])[-3:]:
            print(f"   • {title[:32]:<32} | Rel: {rel_date} ({stage:<24}) -> {cnt:>2} reviews")

    if admin_tasks:
        print("\n👑 Admin User Tracking Tasks:")
        for q, act, match_title, trig in admin_tasks:
            status_tag = "TRIGGERED" if trig else ("ACTIVE" if act else "PAUSED")
            match_desc = f" -> Matched '{match_title}'" if match_title else ""
            print(f"   • [{status_tag:<9}] Tracking: '{q}'{match_desc}")

    print("\n✨ Sample Varied Usernames:")
    for uname in sample_users:
        print(f"     - {uname}")
    print("=" * 70 + "\n")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
