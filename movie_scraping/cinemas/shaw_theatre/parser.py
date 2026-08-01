import importlib.util
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

# Dynamically import Cinema and ShawCinema from types/cineams.py
_types_path = Path(__file__).resolve().parent.parent.parent / "types" / "cineams.py"
_spec = importlib.util.spec_from_file_location("cineams", _types_path)
_cineams_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cineams_mod)

ShawCinema = _cineams_mod.ShawCinema
Cinema = _cineams_mod.Cinema


def clean_address(address: Optional[str]) -> Optional[str]:
    """Clean and normalize address string by replacing newlines/tabs and collapsing whitespace."""
    if not address:
        return None
    cleaned = re.sub(r"[\r\n\t]+", " ", str(address))
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned if cleaned else None


def extract_postal_code(address: Optional[str], default_postal: Optional[str] = None) -> str:
    """Extract a 6-digit Singapore postal code from text or return default."""
    if default_postal:
        cleaned = str(default_postal).strip()
        if re.fullmatch(r"\d{6}", cleaned):
            return cleaned

    if address:
        match = re.search(r"\b(\d{6})\b", address)
        if match:
            return match.group(1)

    return "000000"


def parse_cinema_item(raw: Dict[str, Any]) -> Cinema:
    """Parse a single raw location item from Shaw API into a Cinema dataclass object."""
    shaw = ShawCinema(
        id=int(raw.get("id", 0)),
        code=str(raw.get("code", "")),
        name=str(raw.get("name", "")),
        brands=int(raw.get("brands", 0)),
        address=str(raw.get("address", "")),
        poster=raw.get("poster"),
    )

    full_name = shaw.name or "Shaw Theatre"
    
    # Separate brand name and branch name
    if "Shaw Theatres" in full_name:
        brand_name = "Shaw Theatre"
        branch_name = full_name.replace("Shaw Theatres", "").strip()
        if not branch_name:
            branch_name = full_name
    elif "Shaw Theatre" in full_name:
        brand_name = "Shaw Theatre"
        branch_name = full_name.replace("Shaw Theatre", "").strip()
        if not branch_name:
            branch_name = full_name
    else:
        brand_name = "Shaw Theatre"
        branch_name = full_name

    address_str = clean_address(shaw.address)
    postal_code = extract_postal_code(address_str, raw.get("postalCode") or raw.get("postal_code"))

    cinema_id = 1000 + int(shaw.id) if shaw.id else 1000

    return Cinema(
        id=cinema_id,
        name=brand_name,
        branch=branch_name,
        postal_code=postal_code,
        address=address_str,
        created_at=None,
    )


def parse_cinemas(raw_locations: List[Dict[str, Any]]) -> List[Cinema]:
    """Parse a list of raw location dicts from Shaw internal API."""
    if not raw_locations:
        return []

    cinemas = []
    for raw in raw_locations:
        if isinstance(raw, dict):
            try:
                cinemas.append(parse_cinema_item(raw))
            except Exception as e:
                name = raw.get("name", "unknown")
                print(f"Skipping Shaw cinema item '{name}': {e}")
    return cinemas
