import importlib.util
import os
from pathlib import Path
from typing import List, Optional
import psycopg2
from psycopg2.extras import execute_values

# Dynamically import Movie dataclass from types/movies.py
_movies_path = Path(__file__).resolve().parent.parent / "types" / "movies.py"
_spec = importlib.util.spec_from_file_location("movies", _movies_path)
_movies_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_movies_mod)
Movie = _movies_mod.Movie

# Centralized SQL schema path
SCHEMA_FILE_PATH = Path(__file__).resolve().parent.parent / "schema" / "movies.sql"

DEFAULT_DB_URI = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/screenscout"
)


class DatabaseWriter:
    """Database writer for managing movie schema and upserting scraped movies into PostgreSQL."""

    def __init__(self, db_uri: Optional[str] = None, schema_path: Optional[Path] = None):
        self.db_uri = db_uri or DEFAULT_DB_URI
        self.schema_path = schema_path or SCHEMA_FILE_PATH

    def _get_connection(self):
        return psycopg2.connect(self.db_uri)

    def create_tables(self) -> None:
        """Create extensions, movies table, and indexes using central schema.sql."""
        if not self.schema_path.exists():
            raise FileNotFoundError(f"Schema SQL file not found at: {self.schema_path}")

        schema_sql = self.schema_path.read_text(encoding="utf-8")
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(schema_sql)
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

        # Ensure table exists before upserting
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
            # Format vector embedding to string representation for pgvector if present
            embedding_val = (
                str(m.embedding) if m.embedding is not None else None
            )

            # For SHAW provider, ensure text fields default to empty string '' if None
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
