import os
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from typing import Optional, Dict, Any
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

    def get_database_stats(self) -> Dict[str, Any]:
        """Fetch current database snapshot statistics post-cleanup."""
        stats = {
            "total_movies": 0,
            "now_showing_movies": 0,
            "coming_soon_movies": 0,
            "total_schedules": 0,
            "total_cinemas": 0,
        }
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM cinemas;")
                    row = cur.fetchone()
                    if row:
                        stats["total_cinemas"] = row[0]

                    cur.execute("""
                        SELECT 
                            COUNT(*),
                            COUNT(*) FILTER (WHERE release_date <= CURRENT_DATE),
                            COUNT(*) FILTER (WHERE release_date > CURRENT_DATE)
                        FROM movies;
                    """)
                    row = cur.fetchone()
                    if row:
                        stats["total_movies"] = row[0]
                        stats["now_showing_movies"] = row[1]
                        stats["coming_soon_movies"] = row[2]

                    cur.execute("SELECT COUNT(*) FROM schedules;")
                    row = cur.fetchone()
                    if row:
                        stats["total_schedules"] = row[0]
        except Exception as e:
            stats["error"] = str(e)
        return stats

    def clean_all(self) -> Dict[str, Any]:
        """Perform full database cleanup for both outdated schedules and movies, returning detailed stats."""
        deleted_schedules = self.clean_outdated_schedules()
        deleted_movies = self.clean_outdated_movies()
        db_stats = self.get_database_stats()
        return {
            "deleted_schedules": deleted_schedules,
            "deleted_movies": deleted_movies,
            "db_stats": db_stats,
        }


def clean_database(db_uri: Optional[str] = None) -> Dict[str, Any]:
    """Helper function to execute database cleanup."""
    cleaner = DBCleaner(db_uri=db_uri)
    return cleaner.clean_all()
