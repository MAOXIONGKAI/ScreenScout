import importlib.util
from datetime import date, datetime
from pathlib import Path
from typing import List

# Import from types/movies.py (can't use 'from types.movies' due to stdlib conflict)
_movies_path = Path(__file__).resolve().parent.parent.parent / "types" / "movies.py"
_spec = importlib.util.spec_from_file_location("movies", _movies_path)
_movies_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_movies_mod)
ShawMovie = _movies_mod.ShawMovie
Movie = _movies_mod.Movie


def _iso_to_date(iso_str: str) -> date:
    """Convert an ISO date string (e.g. '2026-07-22T00:00:00') to a date."""
    return datetime.fromisoformat(iso_str).date()


def _clean_url_or_title(val):
    if val is None:
        return ""

    if isinstance(val, list):
        if len(val) == 0:
            return ""
        if all(v is None for v in val):
            return ""
        return ""

    cleaned = str(val).strip()

    if cleaned.lower() in {"", "-", "null", "none"}:
        return ""

    return cleaned


def _clean_str(val: str | None) -> str | None:
    if not val:
        return None
    cleaned = str(val).strip()
    return cleaned if cleaned else None


def _parse_movie(raw: dict) -> Movie:
    """Convert a raw Shaw API dict into a Movie."""
    shaw = ShawMovie(**raw)

    return Movie(
        id=int(shaw.movieId),
        title=shaw.primaryTitle,
        secondary_title=_clean_url_or_title(raw.get("secondaryTitle") or getattr(shaw, "secondaryTitle", None)),
        description=_clean_str(raw.get("fullSynopsis") or getattr(shaw, "fullSynopsis", None)),
        poster_url=_clean_url_or_title(raw.get("posterUrl") or getattr(shaw, "posterUrl", None)),
        trailer_url=_clean_url_or_title(raw.get("trailerUrl") or getattr(shaw, "trailerUrl", None)),
        website_url=_clean_url_or_title(raw.get("websiteUrl") or getattr(shaw, "websiteUrl", None)),
        director=_clean_str(raw.get("directors") or getattr(shaw, "directors", None)),
        casts=_clean_str(raw.get("casts") or getattr(shaw, "casts", None)),
        genre=_clean_str(raw.get("genre") or getattr(shaw, "genre", None)),
        provider="SHAW",
        provider_movie_id=int(shaw.movieId),
        release_date=_iso_to_date(shaw.releaseDate),
        duration=shaw.duration,
    )


def parse_movies(raw_movies: List[dict]) -> List[Movie]:
    """Parse a list of raw Shaw API dicts into Movie objects."""
    if not raw_movies:
        return []

    parsed_movies = []
    for raw in raw_movies:
        try:
            parsed_movies.append(_parse_movie(raw))
        except (KeyError, TypeError, ValueError) as e:
            title = raw.get("primaryTitle", "unknown")
            print(f"Skipping Shaw movie '{title}': {e}")
    return parsed_movies
