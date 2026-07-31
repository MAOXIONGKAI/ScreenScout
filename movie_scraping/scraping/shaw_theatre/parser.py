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


def _parse_movie(raw: dict) -> Movie:
    """Convert a raw Shaw API dict into a Movie."""
    shaw = ShawMovie(**raw)

    return Movie(
        id=int(shaw.movieId),
        title=shaw.primaryTitle,
        secondary_title=shaw.secondaryTitle or None,
        description=shaw.fullSynopsis or None,
        poster_url=shaw.posterUrl,
        trailer_url=shaw.trailerUrl,
        website_url=shaw.websiteUrl,
        director=shaw.directors or None,
        casts=shaw.casts or None,
        genre=shaw.genre or None,
        provider="Shaw",
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
