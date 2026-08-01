from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(slots=True)
class GVCinema:
    """Golden Village raw cinema structure."""
    id: str
    name: str
    sequence: int
    status: int
    type: str
    locationCode: str
    statusMessage: Optional[str] = None
    colorCode: Optional[str] = None
    cinemaCode: Optional[str] = None


@dataclass(slots=True)
class ShawCinema:
    """Shaw Theatre raw cinema structure."""
    id: int
    code: str
    name: str
    brands: int
    address: str
    poster: Optional[str] = None


@dataclass(slots=True)
class Cinema:
    """Database Cinema Schema."""
    id: int
    name: str
    branch: str
    postal_code: str
    address: Optional[str] = None
    created_at: Optional[datetime] = None