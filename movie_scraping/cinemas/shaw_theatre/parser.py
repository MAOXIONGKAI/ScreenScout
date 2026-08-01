import importlib.util
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

# Dynamically import Cinema dataclass from types/cineams.py
_types_path = Path(__file__).resolve().parent.parent.parent / "types" / "cineams.py"
_spec = importlib.util.spec_from_file_location("cineams", _types_path)
_cineams_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cineams_mod)
Cinema = _cineams_mod.Cinema


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
    raw_id = raw.get("id") or raw.get("locationId") or raw.get("code") or 0
    try:
        cinema_id = int(raw_id)
    except (ValueError, TypeError):
        cinema_id = hash(str(raw_id)) % (10 ** 8)

    full_name = raw.get("locationName") or raw.get("name") or raw.get("title") or "Shaw Theatres"
    
    # Separate brand name and branch name
    if "Shaw Theatres" in full_name:
        brand_name = "Shaw Theatres"
        branch_name = full_name.replace("Shaw Theatres", "").strip()
        if not branch_name:
            branch_name = full_name
    else:
        brand_name = "Shaw Theatres"
        branch_name = full_name

    address_str = raw.get("address") or raw.get("locationAddress")
    postal_code = extract_postal_code(address_str, raw.get("postalCode") or raw.get("postal_code"))

    return Cinema(
        id=cinema_id,
        name=brand_name,
        branch=branch_name,
        postal_code=postal_code,
        address=address_str.strip() if address_str else None,
        created_at=None
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
                print(f"Error parsing cinema item {raw}: {e}")
    return cinemas
