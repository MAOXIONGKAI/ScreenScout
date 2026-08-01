import importlib.util
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

# Dynamically import Cinema and GVCinema from types/cineams.py
_types_path = Path(__file__).resolve().parent.parent.parent / "types" / "cineams.py"
_spec = importlib.util.spec_from_file_location("cineams", _types_path)
_cineams_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cineams_mod)

GVCinema = _cineams_mod.GVCinema
Cinema = _cineams_mod.Cinema

# Standard Golden Village location address mapping for fallback enrichment
GV_LOCATION_ADDRESSES = {
    "01": ("15 Yishun Central 1, Yishun 10, Singapore 768740", "768740"),
    "02": ("9 Bishan Place, Junction 8, #04-03, Singapore 579837", "579837"),
    "04": ("63 Jurong West Central 3, Jurong Point 2, #03-25B, Singapore 648331", "648331"),
    "05": ("1 HarbourFront Walk, VivoCity, #02-30, Singapore 098585", "098585"),
    "07": ("1 Kim Seng Promenade, Great World, #03-125, Singapore 237994", "237994"),
    "08": ("68 Orchard Road, Plaza Singapura, #07-01, Singapore 238839", "238839"),
    "09": ("4 Tampines Central 5, Tampines Mall, #04-17/18, Singapore 529510", "529510"),
    "10": ("112 East Coast Road, i12 Katong, #05-01, Singapore 428802", "428802"),
    "11": ("180 Kitchener Road, City Square Mall, #05-02/03, Singapore 208539", "208539"),
    "12": ("3 Temasek Boulevard, Suntec City Mall, #03-373, Singapore 038983", "038983"),
    "13": ("10 Eunos Road 8, SingPost Centre, #03-107, Singapore 408600", "408600"),
    "14": ("208 New Upper Changi Road, Bedok Town Centre, #04-01, Singapore 460208", "460208"),
    "15": ("107 North Bridge Road, Funan, #05-01, Singapore 179105", "179105"),
    "17": ("201 Victoria Street, Bugis+, #05-01, Singapore 188067", "188067"),
    "18": ("8 Grange Road, Cathay Cineleisure Orchard, #04-01, Singapore 239695", "239695"),
    "19": ("1 Pasir Ris Close, E!Hub@Downtown East, #04-101, Singapore 519599", "519599"),
    "22": ("2 Tampines Central 5, Century Square, #05-11, Singapore 529509", "529509"),
}


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
    """Parse a single raw Golden Village location item into a Cinema dataclass object."""
    gv = GVCinema(
        id=str(raw.get("id", "")),
        name=str(raw.get("name", "")),
        sequence=int(raw.get("sequence", 0)),
        status=int(raw.get("status", 0)),
        type=str(raw.get("type", "")),
        locationCode=str(raw.get("locationCode", "")),
        statusMessage=raw.get("statusMessage"),
        colorCode=raw.get("colorCode"),
        cinemaCode=raw.get("cinemaCode"),
    )

    if raw.get("id") and str(raw["id"]).isdigit() and int(raw["id"]) >= 2000:
        cinema_id = int(raw["id"])
    else:
        try:
            cinema_id = 2000 + int(gv.id or gv.locationCode or 0)
        except (ValueError, TypeError):
            cinema_id = 2000 + (hash(gv.id) % 1000)

    if raw.get("branch"):
        brand_name = raw.get("name") or "Golden Village"
        branch_name = str(raw["branch"]).strip()
    else:
        full_name = gv.name or "Golden Village"
        if full_name.startswith("GV "):
            brand_name = "Golden Village"
            branch_name = full_name[3:].strip()
        elif full_name.startswith("Golden Village"):
            brand_name = "Golden Village"
            branch_name = full_name[14:].strip()
            if not branch_name:
                branch_name = full_name
        else:
            brand_name = "Golden Village"
            branch_name = full_name

    loc_code = (gv.locationCode or gv.id or "").zfill(2)
    fallback_addr, fallback_postal = GV_LOCATION_ADDRESSES.get(loc_code, (None, "000000"))

    raw_addr = raw.get("address") or raw.get("locationAddress") or fallback_addr
    address_str = clean_address(raw_addr)
    postal_code = extract_postal_code(address_str, raw.get("postalCode") or raw.get("postal_code") or fallback_postal)

    return Cinema(
        id=cinema_id,
        name=brand_name,
        branch=branch_name,
        postal_code=postal_code,
        address=address_str,
        created_at=None,
    )


def parse_cinemas(raw_locations: List[Dict[str, Any]]) -> List[Cinema]:
    """Parse a list of raw Golden Village location dicts."""
    if not raw_locations:
        return []

    cinemas = []
    for raw in raw_locations:
        if isinstance(raw, dict):
            try:
                cinemas.append(parse_cinema_item(raw))
            except Exception as e:
                name = raw.get("name", "unknown")
                print(f"Skipping Golden Village cinema item '{name}': {e}")
    return cinemas
