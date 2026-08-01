import importlib.util
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import psycopg2
from psycopg2.extras import execute_values

# Dynamically import Movie dataclass from types/movies.py
_movies_path = Path(__file__).resolve().parent.parent / "types" / "movies.py"
_spec_movies = importlib.util.spec_from_file_location("movies", _movies_path)
_movies_mod = importlib.util.module_from_spec(_spec_movies)
_spec_movies.loader.exec_module(_movies_mod)
Movie = _movies_mod.Movie

# Dynamically import Schedule dataclass from types/schedules.py
_schedules_path = Path(__file__).resolve().parent.parent / "types" / "schedules.py"
_spec_sched = importlib.util.spec_from_file_location("schedules", _schedules_path)
_schedules_mod = importlib.util.module_from_spec(_spec_sched)
_spec_sched.loader.exec_module(_schedules_mod)
Schedule = _schedules_mod.Schedule

# Centralized SQL schema paths
MOVIES_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema" / "movies.sql"
SCHEDULES_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema" / "schedules.sql"

DEFAULT_DB_URI = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/screenscout"
)


def _parse_start_time(start_time: str) -> str:
    """Parse and normalize start_time string into 'HH:MM:SS' format for PostgreSQL TIME column."""
    s = str(start_time).strip()

    # 1. 12-hour format: "4:30 PM"
    try:
        return datetime.strptime(s, "%I:%M %p").strftime("%H:%M:%S")
    except ValueError:
        pass

    try:
        return datetime.strptime(s, "%I:%M%p").strftime("%H:%M:%S")
    except ValueError:
        pass

    # 2. 24-hour format: "16:50" or "16:50:00"
    try:
        return datetime.strptime(s, "%H:%M").strftime("%H:%M:%S")
    except ValueError:
        pass

    try:
        return datetime.strptime(s, "%H:%M:%S").strftime("%H:%M:%S")
    except ValueError:
        pass

    return s


class DatabaseWriter:
    """Database writer for managing movie & schedule schemas and upserting into PostgreSQL."""

    def __init__(
        self,
        db_uri: Optional[str] = None,
        movies_schema_path: Optional[Path] = None,
        schedules_schema_path: Optional[Path] = None,
    ):
        self.db_uri = db_uri or DEFAULT_DB_URI
        self.movies_schema_path = movies_schema_path or MOVIES_SCHEMA_PATH
        self.schedules_schema_path = schedules_schema_path or SCHEDULES_SCHEMA_PATH

    def _get_connection(self):
        return psycopg2.connect(self.db_uri)

    def create_tables(self) -> None:
        """Create movies and schedules tables and indexes using central schema SQL files."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                if self.movies_schema_path.exists():
                    cur.execute(self.movies_schema_path.read_text(encoding="utf-8"))
                if self.schedules_schema_path.exists():
                    cur.execute(self.schedules_schema_path.read_text(encoding="utf-8"))
            conn.commit()

    def upsert_movies(self, movies: List[Movie]) -> int:
        """Insert or update a list of parsed Movie objects in the PostgreSQL movies table.

        Args:
            movies: List of Movie dataclass instances.

        Returns:
            int: Number of movies processed.
        """
        if not movies:
            print("No movies provided to upsert.")
            return 0

        self.create_tables()

        upsert_query = """
        INSERT INTO movies (
            id,
            title,
            secondary_title,
            description,
            embedding,
            poster_url,
            trailer_url,
            website_url,
            director,
            casts,
            genre,
            provider,
            provider_movie_id,
            release_date,
            duration
        ) VALUES %s
        ON CONFLICT (provider, provider_movie_id) DO UPDATE SET
            title = EXCLUDED.title,
            secondary_title = EXCLUDED.secondary_title,
            description = EXCLUDED.description,
            embedding = EXCLUDED.embedding,
            poster_url = EXCLUDED.poster_url,
            trailer_url = EXCLUDED.trailer_url,
            website_url = EXCLUDED.website_url,
            director = EXCLUDED.director,
            casts = EXCLUDED.casts,
            genre = EXCLUDED.genre,
            release_date = EXCLUDED.release_date,
            duration = EXCLUDED.duration;
        """

        values = []
        for m in movies:
            embedding_val = str(m.embedding) if m.embedding is not None else None

            if m.provider == "SHAW":
                sec_title = m.secondary_title if m.secondary_title is not None else ""
                poster = m.poster_url if m.poster_url is not None else ""
                trailer = m.trailer_url if m.trailer_url is not None else ""
                website = m.website_url if m.website_url is not None else ""
            else:
                sec_title = m.secondary_title
                poster = m.poster_url
                trailer = m.trailer_url
                website = m.website_url

            values.append(
                (
                    m.id,
                    m.title,
                    sec_title,
                    m.description,
                    embedding_val,
                    poster,
                    trailer,
                    website,
                    m.director,
                    m.casts,
                    m.genre,
                    m.provider,
                    m.provider_movie_id,
                    m.release_date,
                    m.duration,
                )
            )

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                execute_values(cur, upsert_query, values)
            conn.commit()

        print(f"Successfully upserted {len(movies)} movies into PostgreSQL database.")
        return len(movies)

    def upsert_schedules(self, schedules: List[Schedule]) -> int:
        """Insert or update a list of parsed Schedule objects in the PostgreSQL schedules table.

        Args:
            schedules: List of Schedule dataclass instances.

        Returns:
            int: Number of schedules processed.
        """
        if not schedules:
            print("No schedules provided to upsert.")
            return 0

        self.create_tables()

        upsert_query = """
        INSERT INTO schedules (
            id,
            movie_id,
            cinema_id,
            start_date,
            start_time
        ) VALUES %s
        ON CONFLICT (movie_id, cinema_id, start_date, start_time) DO UPDATE SET
            id = EXCLUDED.id;
        """

        unique_schedules = {}
        for s in schedules:
            try:
                time_val = _parse_start_time(s.start_time)
                key = (s.movie_id, s.cinema_id, s.start_date, time_val)
                unique_schedules[key] = (
                    s.id,
                    s.movie_id,
                    s.cinema_id,
                    s.start_date,
                    time_val,
                )
            except Exception as e:
                print(f"Skipping schedule item (id={s.id}): {e}")

        values = list(unique_schedules.values())

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                execute_values(cur, upsert_query, values)
            conn.commit()

        print(f"Successfully upserted {len(schedules)} schedules into PostgreSQL database.")
        return len(schedules)


def save_movies(movies: List[Movie], db_uri: Optional[str] = None) -> int:
    """Helper function to insert or update parsed movies into PostgreSQL.

    Args:
        movies: List of parsed Movie objects.
        db_uri: Optional database connection string.

    Returns:
        int: Number of movies upserted.
    """
    writer = DatabaseWriter(db_uri=db_uri)
    return writer.upsert_movies(movies)


def save_schedules(schedules: List[Schedule], db_uri: Optional[str] = None) -> int:
    """Helper function to insert or update parsed schedules into PostgreSQL.

    Args:
        schedules: List of parsed Schedule objects.
        db_uri: Optional database connection string.

    Returns:
        int: Number of schedules upserted.
    """
    writer = DatabaseWriter(db_uri=db_uri)
    return writer.upsert_schedules(schedules)
