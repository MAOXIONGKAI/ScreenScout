import html
import importlib.util
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import re
from typing import List, Dict, Any, Optional

# Import from types/movies.py
_movies_path = Path(__file__).resolve().parent.parent.parent / "types" / "movies.py"
_spec_movies = importlib.util.spec_from_file_location("movies", _movies_path)
_movies_mod = importlib.util.module_from_spec(_spec_movies)
_spec_movies.loader.exec_module(_movies_mod)
GVMovie = _movies_mod.GVMovie
Movie = _movies_mod.Movie

# Import from types/schedules.py
_schedules_path = Path(__file__).resolve().parent.parent.parent / "types" / "schedules.py"
_spec_sched = importlib.util.spec_from_file_location("schedules", _schedules_path)
_schedules_mod = importlib.util.module_from_spec(_spec_sched)
_spec_sched.loader.exec_module(_schedules_mod)
Schedule = _schedules_mod.Schedule

# Mapping for GV location IDs (including special hall codes) to primary cinema IDs
GV_LOCATION_ID_TO_CINEMA_ID = {
    "01": 2001,
    "02": 2002,
    "04": 2004,
    "05": 2005,
    "051": 2005,
    "051*": 2005,
    "50": 2005,
    "07": 2007,
    "70": 2007,
    "08": 2008,
    "09": 2009,
    "10": 2010,
    "60": 2010,
    "11": 2011,
    "114": 2011,
    "12": 2012,
    "80": 2012,
    "13": 2013,
    "131": 2013,
    "14": 2014,
    "15": 2015,
    "155": 2015,
    "15C": 2015,
    "15E": 2015,
    "17": 2017,
    "40": 2017,
    "18": 2018,
    "19": 2019,
    "22": 2022,
}


def _clean_html_text(text: Optional[str]) -> Optional[str]:
    """Strip HTML tags, unescape HTML entities, and normalize whitespace."""
    if not text:
        return None
    # Unescape HTML entities (e.g. &amp;, &nbsp;, &lt;, &gt;, &#39;)
    text = html.unescape(text)
    # Replace block / line break tags (both opening and closing) with spaces to prevent words merging
    text = re.sub(r"</?(br|p|div|li)[^>]*>", " ", text, flags=re.IGNORECASE)
    # Strip remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Normalize multiple whitespace into a single clean space
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned if cleaned else None


def _epoch_ms_to_date(epoch_ms: int) -> date:
    """Convert a millisecond epoch timestamp to a date."""
    return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).date()


def _format_time24(t24: str) -> str:
    """Convert a 4-digit 24h string like '1650' or '0940' to '16:50:00' or '09:40:00'."""
    t24 = str(t24).strip().zfill(4)
    return f"{t24[:2]}:{t24[2:]}:00"


def _parse_movie(raw: dict) -> Movie:
    """Convert a raw GV API dict into a Movie."""
    gv = GVMovie(**raw)

    return Movie(
        id=int(gv.filmCd),
        title=gv.filmTitle,
        description=_clean_html_text(gv.synopsis),
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
    """Parse a list of raw GV API dicts into Movie objects, keeping only current year and upcoming movies."""
    if not raw_movies:
        return []

    current_year = datetime.now(ZoneInfo("Asia/Singapore")).year
    parsed_movies = []
    for raw in raw_movies:
        try:
            m = _parse_movie(raw)
            if m.release_date and m.release_date.year < current_year:
                continue
            parsed_movies.append(m)
        except (KeyError, TypeError, ValueError) as e:
            title = raw.get("filmTitle", "unknown")
            print(f"Skipping movie '{title}': {e}")
    return parsed_movies


def parse_schedules(raw_schedules: List[Dict[str, Any]]) -> List[Schedule]:
    """Parse raw Golden Village schedule dicts into Schedule dataclass objects."""
    if not raw_schedules:
        return []

    now_sg = datetime.now(ZoneInfo("Asia/Singapore")).replace(tzinfo=None)
    parsed_schedules = []
    for item in raw_schedules:
        if not isinstance(item, dict):
            continue
        data = item.get("data")
        if not isinstance(data, dict):
            continue
        movie_id_str = data.get("filmCd")
        if not movie_id_str:
            continue
        try:
            movie_id = int(movie_id_str)
        except (ValueError, TypeError):
            continue

        locations = data.get("locations") or []
        for loc in locations:
            if not isinstance(loc, dict):
                continue
            loc_id = str(loc.get("id", ""))
            cinema_id = GV_LOCATION_ID_TO_CINEMA_ID.get(loc_id)
            if not cinema_id and loc_id.isdigit():
                cinema_id = 2000 + int(loc_id)
            if not cinema_id:
                continue

            dates = loc.get("dates") or []
            for date_item in dates:
                if not isinstance(date_item, dict):
                    continue
                times = date_item.get("times") or []
                for t_item in times:
                    if not isinstance(t_item, dict):
                        continue
                    show_date_ms = t_item.get("showDate") or date_item.get("date")
                    if not show_date_ms:
                        continue

                    start_date = datetime.fromtimestamp(show_date_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
                    time24 = t_item.get("time24") or ""
                    time12 = t_item.get("time12") or ""
                    start_time = _format_time24(time24) if time24 else str(time12).strip()
                    hall = t_item.get("hallNumber") or ""

                    # Filter out past showtimes
                    try:
                        norm_time = _format_time24(time24) if time24 else start_time
                        if len(norm_time) == 5:
                            norm_time += ":00"
                        sched_dt = datetime.strptime(f"{start_date} {norm_time}", "%Y-%m-%d %H:%M:%S")
                        if sched_dt < now_sg:
                            continue
                    except (ValueError, TypeError):
                        pass

                    # Generate deterministic integer schedule ID
                    import zlib
                    key_str = f"GV_{cinema_id}_{movie_id}_{start_date}_{start_time}_{hall}_{show_date_ms}"
                    sched_id = zlib.crc32(key_str.encode("utf-8"))

                    parsed_schedules.append(
                        Schedule(
                            id=sched_id,
                            cinema_id=cinema_id,
                            movie_id=movie_id,
                            start_date=start_date,
                            start_time=start_time,
                            created_at=None,
                        )
                    )
    return parsed_schedules