import importlib.util
import os
from pathlib import Path
from dotenv import load_dotenv
from typing import List, Optional
import psycopg2
from psycopg2.extras import execute_values

# Dynamically import Cinema dataclass from types/cineams.py
_types_path = Path(__file__).resolve().parent.parent / "types" / "cineams.py"
_spec = importlib.util.spec_from_file_location("cineams", _types_path)
_cineams_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cineams_mod)
Cinema = _cineams_mod.Cinema

# Centralized SQL schema path
SCHEMA_FILE_PATH = Path(__file__).resolve().parent.parent / "schema" / "cinemas.sql"

load_dotenv()

DEFAULT_DB_URI = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/screenscout"
)


class DatabaseWriter:
    """Database writer for managing cinema schema and upserting scraped cinemas into PostgreSQL."""

    def __init__(self, db_uri: Optional[str] = None, schema_path: Optional[Path] = None):
        self.db_uri = db_uri or DEFAULT_DB_URI
        self.schema_path = schema_path or SCHEMA_FILE_PATH

    def _get_connection(self):
        return psycopg2.connect(self.db_uri)

    def create_tables(self) -> None:
        """Create cinemas table using central schema.sql."""
        if not self.schema_path.exists():
            raise FileNotFoundError(f"Schema SQL file not found at: {self.schema_path}")

        schema_sql = self.schema_path.read_text(encoding="utf-8")
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(schema_sql)
            conn.commit()

    def upsert_cinemas(self, cinemas: List[Cinema]) -> int:
        """Insert or update a list of parsed Cinema objects in the PostgreSQL cinemas table.

        Args:
            cinemas: List of Cinema dataclass instances.

        Returns:
            int: Number of cinemas processed.
        """
        if not cinemas:
            print("No cinemas provided to upsert.")
            return 0

        # Ensure table exists before upserting
        self.create_tables()

        # Cleanup legacy un-namespaced cinema IDs (id < 1000) if present
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM cinemas WHERE id < 1000;")
            conn.commit()

        upsert_query = """
        INSERT INTO cinemas (
            id,
            name,
            branch,
            postal_code,
            address
        ) VALUES %s
        ON CONFLICT (id) DO UPDATE SET
            name = EXCLUDED.name,
            branch = EXCLUDED.branch,
            postal_code = EXCLUDED.postal_code,
            address = EXCLUDED.address;
        """

        values = [
            (
                c.id,
                c.name,
                c.branch,
                c.postal_code,
                c.address,
            )
            for c in cinemas
        ]

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                execute_values(cur, upsert_query, values)
            conn.commit()

        print(f"Successfully upserted {len(cinemas)} cinemas into PostgreSQL database.")
        return len(cinemas)


def save_cinemas(cinemas: List[Cinema], db_uri: Optional[str] = None) -> int:
    """Helper function to insert or update parsed cinemas into PostgreSQL.

    Args:
        cinemas: List of parsed Cinema objects.
        db_uri: Optional database connection string.

    Returns:
        int: Number of cinemas upserted.
    """
    writer = DatabaseWriter(db_uri=db_uri)
    return writer.upsert_cinemas(cinemas)
