import os
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from typing import Optional, Dict
import psycopg2

DEFAULT_DB_URI = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/screenscout"
)


class DBCleaner:
    """Cleaner for managing database maintenance and removing outdated schedules and movies."""

    def __init__(self, db_uri: Optional[str] = None):
        self.db_uri = db_uri or DEFAULT_DB_URI

    def _get_connection(self):
        return psycopg2.connect(self.db_uri)

    def clean_outdated_schedules(self) -> int:
        """Delete schedules whose start_date + start_time is in the past."""
        delete_query = """
        DELETE FROM schedules
        WHERE (start_date + start_time) < (NOW() AT TIME ZONE 'Asia/Singapore');
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(delete_query)
                count = cur.rowcount
            conn.commit()
        return count

    def clean_outdated_movies(self) -> int:
        """Delete movies whose release_date is in the past and have no remaining schedules in the database."""
        delete_query = """
        DELETE FROM movies
        WHERE release_date < (CURRENT_DATE AT TIME ZONE 'Asia/Singapore')::date
          AND NOT EXISTS (
              SELECT 1 FROM schedules WHERE schedules.movie_id = movies.id
          );
        """
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(delete_query)
                count = cur.rowcount
            conn.commit()
        return count

    def clean_all(self) -> Dict[str, int]:
        """Perform full database cleanup for both outdated schedules and movies."""
        deleted_schedules = self.clean_outdated_schedules()
        deleted_movies = self.clean_outdated_movies()
        print(f"Database cleanup: Deleted {deleted_schedules} expired schedules and {deleted_movies} outdated movies.")
        return {
            "deleted_schedules": deleted_schedules,
            "deleted_movies": deleted_movies,
        }


def clean_database(db_uri: Optional[str] = None) -> Dict[str, int]:
    """Helper function to execute database cleanup."""
    cleaner = DBCleaner(db_uri=db_uri)
    return cleaner.clean_all()
