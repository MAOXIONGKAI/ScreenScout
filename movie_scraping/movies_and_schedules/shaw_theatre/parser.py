import importlib.util
from datetime import date, datetime
from pathlib import Path
from typing import List, Dict, Any, Union

# Import from types/movies.py
_movies_path = Path(__file__).resolve().parent.parent.parent / "types" / "movies.py"
_spec_movies = importlib.util.spec_from_file_location("movies", _movies_path)
_movies_mod = importlib.util.module_from_spec(_spec_movies)
_spec_movies.loader.exec_module(_movies_mod)
ShawMovie = _movies_mod.ShawMovie
Movie = _movies_mod.Movie

# Import from types/schedules.py
_schedules_path = Path(__file__).resolve().parent.parent.parent / "types" / "schedules.py"
_spec_sched = importlib.util.spec_from_file_location("schedules", _schedules_path)
_schedules_mod = importlib.util.module_from_spec(_spec_sched)
_spec_sched.loader.exec_module(_schedules_mod)
Schedule = _schedules_mod.Schedule


def _iso_to_date(iso_str: str) -> date:
    """Convert an ISO date string (e.g. '2026-07-22T00:00:00') to a date."""
    return datetime.fromisoformat(iso_str).date()


def _format_time_24h(time_str: str) -> str:
    """Normalize time strings like '4:30 PM' or '16:30' to 'HH:MM:SS'."""
    s = str(time_str).strip()
    try:
        dt = datetime.strptime(s, "%I:%M %p")
        return dt.strftime("%H:%M:%S")
    except ValueError:
        pass
    try:
        dt = datetime.strptime(s, "%H:%M")
        return dt.strftime("%H:%M:%S")
    except ValueError:
        pass
    try:
        dt = datetime.strptime(s, "%H:%M:%S")
        return dt.strftime("%H:%M:%S")
    except ValueError:
        pass
    return s


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


def parse_schedules(raw_schedules: List[Union[Dict[str, Any], List[Dict[str, Any]]]]) -> List[Schedule]:
    """Parse raw Shaw showtimes schedules into Schedule dataclass objects."""
    if not raw_schedules:
        return []

    parsed_schedules = []
    for item in raw_schedules:
        movie_list = item if isinstance(item, list) else [item]
        for movie_obj in movie_list:
            if not isinstance(movie_obj, dict):
                continue
            parent_movie_id = movie_obj.get("movieId")
            show_times = movie_obj.get("showTimes") or []
            for st in show_times:
                if not isinstance(st, dict):
                    continue
                perf_id = st.get("performanceId")
                loc_id = st.get("locationId")
                m_id = st.get("movieId") or parent_movie_id
                disp_date = st.get("displayDate")
                disp_time = st.get("displayTime")
                if perf_id and loc_id and m_id and disp_date and disp_time:
                    try:
                        time_24h = _format_time_24h(disp_time)
                        parsed_schedules.append(
                            Schedule(
                                id=int(perf_id),
                                cinema_id=1000 + int(loc_id),
                                movie_id=int(m_id),
                                start_date=str(disp_date).strip(),
                                start_time=time_24h,
                                created_at=None,
                            )
                        )
                    except (ValueError, TypeError) as e:
                        print(f"Error parsing Shaw schedule item: {e}")
    return parsed_schedules
