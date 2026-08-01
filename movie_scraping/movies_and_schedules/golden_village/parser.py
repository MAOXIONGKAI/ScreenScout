import importlib.util
from datetime import date, datetime, timezone
from pathlib import Path
from typing import List

# Import from types/movies.py (can't use 'from types.movies' due to stdlib conflict)
_movies_path = Path(__file__).resolve().parent.parent / "types" / "movies.py"
_spec = importlib.util.spec_from_file_location("movies", _movies_path)
_movies_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_movies_mod)

GVMovie = _movies_mod.GVMovie
Movie = _movies_mod.Movie


def _epoch_ms_to_date(epoch_ms: int) -> date:
    """Convert a millisecond epoch timestamp to a date."""
    return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).date()


def _parse_movie(raw: dict) -> Movie:
    """Convert a raw GV API dict into a Movie."""
    gv = GVMovie(**raw)

    return Movie(
        id=int(gv.filmCd),
        title=gv.filmTitle,
        description=gv.synopsis or None,
        poster_url=gv.imgLink or None,
        trailer_url=gv.trailerLink,
        website_url=gv.websiteLink,
        director=gv.director or None,
        casts=gv.mainCast or None,
        genre=gv.genre or None,
        provider="GV",
        provider_movie_id=int(gv.filmCd),
        release_date=_epoch_ms_to_date(gv.releaseDate),
        duration=gv.duration,
    )


def parse_movies(raw_movies: List[dict]) -> List[Movie]:
    """Parse a list of raw GV API dicts into Movie objects."""
    if not raw_movies:
        return []

    parsed_movies = []
    for raw in raw_movies:
        try:
            parsed_movies.append(_parse_movie(raw))
        except (KeyError, TypeError, ValueError) as e:
            title = raw.get("filmTitle", "unknown")
            print(f"Skipping movie '{title}': {e}")
    return parsed_movies