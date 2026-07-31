from dataclasses import dataclass
from typing import  Optional, List
from datetime import date, datetime

@dataclass(slots=True)
class GVMovie:
    """Golden Village movie structure."""
    id: str
    type: str
    filmCd: str
    filmTitle: str
    exclusive: bool
    mPassMovie: bool
    frameDescription: str
    colorCode: str
    specialEvent: bool
    eventTicker: bool
    rating: str
    ratingImgUrl: str
    movieKindCd: str
    language: str
    mainCast: str
    director: str
    duration: int
    synopsis: str
    genre: str
    imgLink: str
    subTitles: List[str]
    priorityBkgFlg: bool
    superSneaks: bool
    reviewRating: float
    dateToReach: int
    releaseDate: int
    # Optional fields
    consumerAdvise: Optional[str] = None
    distributor: Optional[str] = None
    trailerLink: Optional[str] = None
    websiteLink: Optional[str] = None
    partnerLinks: Optional[str] = None
    partnerImages: Optional[str] = None
    content: Optional[str] = None
    groupImageLink: Optional[str] = None
    movieImages: Optional[List[str]] = None
    promotions: Optional[List[dict]] = None
    movieKinds: List[dict] = None
    tnc: Optional[str] = None


@dataclass(slots=True)
class Movie:
    """Database Movie Schema."""
    id: int

    title: str
    secondary_title: Optional[str] = None

    description: Optional[str] = None
    embedding: Optional[list[float]] = None

    poster_url: Optional[str] = None
    trailer_url: Optional[str] = None
    website_url: Optional[str] = None

    director: Optional[str] = None
    casts: Optional[str] = None
    genre: Optional[str] = None

    provider: str = ""
    provider_movie_id: int = 0

    release_date: date = date.min
    duration: int = 0

    created_at: Optional[datetime] = None