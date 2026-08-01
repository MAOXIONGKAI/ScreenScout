from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(slots=True)
class GVShowTime:
    """Golden Village raw showtime structure."""
    showDate: int
    time12: str
    time24: str
    hallNumber: Optional[str] = None


@dataclass(slots=True)
class ShawShowTime:
    """Shaw Theatre raw showtime structure."""
    performanceId: int
    displayDate: str
    displayTime: str
    locationId: int
    locationVenueId: int
    locationVenueName: str
    movieReleaseId: int
    movieId: Optional[int] = None


@dataclass(slots=True)
class Schedule:
    """Represents a movie showtime schedule for a specific cinema hall and date."""
    id: int
    cinema_id: int
    movie_id: int
    start_date: str
    start_time: str
    created_at: Optional[datetime] = None