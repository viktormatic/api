"""
Shared utility functions for Südtirol Immobilien scrapers.
Handles deduplication, data normalization, rate limiting, and common parsing.
"""

import hashlib
import json
import math
import os
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class PropertyListing:
    """Standardized property listing data structure."""

    # Identifiers
    property_id: str = ""
    source: str = ""  # "immobiliare" or "idealista"
    url: str = ""

    # Basic info
    title: str = ""
    description: str = ""

    # Price
    price: float = 0.0
    price_per_sqm: float = 0.0
    price_history: list = field(default_factory=list)

    # Property details
    surface_area: float = 0.0
    rooms: int = 0
    bathrooms: int = 0
    floor: Optional[int] = None
    total_floors: Optional[int] = None
    elevator: Optional[bool] = None
    balcony: Optional[bool] = None
    terrace: Optional[bool] = None
    garden: Optional[bool] = None
    garage: Optional[bool] = None
    cellar: Optional[bool] = None

    # Condition & energy
    energy_class: str = ""
    heating_type: str = ""
    year_built: Optional[int] = None
    condition: str = ""  # "da_ristrutturare", "buono", "ristrutturato", "nuovo"
    condition_de: str = ""

    # Location
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: str = ""
    municipality: str = ""
    municipality_de: str = ""
    zone: str = ""
    province: str = "BZ"

    # Media
    images: list = field(default_factory=list)
    floor_plan_images: list = field(default_factory=list)

    # Agency
    agency_name: str = ""
    agency_phone: str = ""

    # Dates
    listing_date: str = ""
    last_updated: str = ""
    scrape_date: str = ""

    # Property type
    property_type: str = ""  # appartamento, villa, casa-indipendente, attico

    # Metadata
    raw_data: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.surface_area and self.price and not self.price_per_sqm:
            self.price_per_sqm = round(self.price / self.surface_area, 2)
        if not self.scrape_date:
            self.scrape_date = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return asdict(self)


# Municipality name mapping (Italian <-> German)
MUNICIPALITY_NAMES = {
    "bolzano": "Bozen",
    "merano": "Meran",
    "bressanone": "Brixen",
    "laives": "Leifers",
    "appiano-sulla-strada-del-vino": "Eppan",
    "appiano": "Eppan",
    "lana": "Lana",
    "brunico": "Bruneck",
    "egna": "Neumarkt",
    "silandro": "Schlanders",
    "vipiteno": "Sterzing",
    "caldaro-sulla-strada-del-vino": "Kaltern",
    "caldaro": "Kaltern",
    "renon": "Ritten",
    "tirolo": "Dorf Tirol",
    "franzensfeste": "Franzensfeste",
    "fortezza": "Franzensfeste",
}

# Reverse mapping
MUNICIPALITY_NAMES_DE_TO_IT = {v.lower(): k for k, v in MUNICIPALITY_NAMES.items()}

# Condition mapping from Italian/German keywords
CONDITION_KEYWORDS = {
    "da_ristrutturare": [
        "da ristrutturare",
        "zu renovieren",
        "renovierungsbedürftig",
        "sanierungsbedürftig",
        "da rifare",
        "da rinnovare",
    ],
    "buono": [
        "buono stato",
        "buone condizioni",
        "guter zustand",
        "gepflegt",
        "abitabile",
        "bewohnbar",
    ],
    "ristrutturato": [
        "ristrutturato",
        "renoviert",
        "saniert",
        "rinnovato",
        "recentemente ristrutturato",
        "frisch renoviert",
    ],
    "nuovo": [
        "nuovo",
        "nuova costruzione",
        "neubau",
        "erstbezug",
        "di nuova costruzione",
    ],
}


def load_config(config_name: str = "settings.yaml") -> dict:
    """Load a YAML configuration file."""
    config_dir = Path(__file__).parent.parent / "config"
    config_path = config_dir / config_name
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_market_data() -> dict:
    """Load market data configuration."""
    return load_config("market_data.yaml")


def detect_condition(text: str) -> tuple[str, str]:
    """
    Detect property condition from description text.
    Returns (condition_it, condition_de) tuple.
    """
    text_lower = text.lower()
    for condition, keywords in CONDITION_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                de_map = {
                    "da_ristrutturare": "renovierungsbedürftig",
                    "buono": "guter Zustand",
                    "ristrutturato": "renoviert",
                    "nuovo": "Neubau",
                }
                return condition, de_map.get(condition, condition)
    return "buono", "guter Zustand"  # Default assumption


def detect_red_flags(text: str, config: Optional[dict] = None) -> list[str]:
    """Check listing text for red flags that should exclude it."""
    if config is None:
        config = load_config()

    red_flags_found = []
    text_lower = text.lower()

    for keyword in config.get("red_flags", {}).get("keywords", []):
        if keyword.lower() in text_lower:
            red_flags_found.append(keyword)

    return red_flags_found


def normalize_municipality(name: str) -> tuple[str, str]:
    """
    Normalize municipality name and return (italian_name, german_name).
    """
    name_lower = name.lower().strip()

    # Direct Italian lookup
    if name_lower in MUNICIPALITY_NAMES:
        return name_lower, MUNICIPALITY_NAMES[name_lower]

    # German to Italian lookup
    if name_lower in MUNICIPALITY_NAMES_DE_TO_IT:
        it_name = MUNICIPALITY_NAMES_DE_TO_IT[name_lower]
        return it_name, name.strip()

    # Partial match
    for it_name, de_name in MUNICIPALITY_NAMES.items():
        if name_lower in it_name or it_name in name_lower:
            return it_name, de_name
        if name_lower in de_name.lower() or de_name.lower() in name_lower:
            return it_name, de_name

    return name_lower, name.strip()


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in meters between two GPS coordinates."""
    R = 6371000  # Earth's radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def is_duplicate(
    listing_a: PropertyListing,
    listing_b: PropertyListing,
    config: Optional[dict] = None,
) -> bool:
    """
    Check if two listings are duplicates using GPS, area, rooms, and price.
    """
    if config is None:
        config = load_config()

    dedup_config = config.get("scraping", {}).get("deduplication", {})
    gps_radius = dedup_config.get("gps_radius_meters", 50)
    area_tolerance = dedup_config.get("area_tolerance_pct", 5) / 100
    price_tolerance = dedup_config.get("price_tolerance_pct", 10) / 100

    # GPS check
    if all(
        [
            listing_a.latitude,
            listing_a.longitude,
            listing_b.latitude,
            listing_b.longitude,
        ]
    ):
        distance = haversine_distance(
            listing_a.latitude,
            listing_a.longitude,
            listing_b.latitude,
            listing_b.longitude,
        )
        if distance > gps_radius:
            return False
        # Within GPS radius, check other factors
        gps_match = True
    else:
        gps_match = False

    # Area check
    if listing_a.surface_area and listing_b.surface_area:
        area_diff = abs(listing_a.surface_area - listing_b.surface_area)
        avg_area = (listing_a.surface_area + listing_b.surface_area) / 2
        area_match = (area_diff / avg_area) <= area_tolerance
    else:
        area_match = False

    # Rooms check
    rooms_match = listing_a.rooms == listing_b.rooms and listing_a.rooms > 0

    # Price check
    if listing_a.price and listing_b.price:
        price_diff = abs(listing_a.price - listing_b.price)
        avg_price = (listing_a.price + listing_b.price) / 2
        price_match = (price_diff / avg_price) <= price_tolerance
    else:
        price_match = False

    # Decision logic
    if gps_match and area_match:
        return True
    if area_match and rooms_match and price_match:
        return True

    return False


def deduplicate_listings(listings: list[PropertyListing]) -> list[PropertyListing]:
    """
    Remove duplicate listings, preferring immobiliare.it data (generally more complete).
    """
    unique = []
    for listing in listings:
        is_dup = False
        for i, existing in enumerate(unique):
            if is_duplicate(listing, existing):
                is_dup = True
                # Prefer immobiliare.it listing, or the one with more data
                if listing.source == "immobiliare" and existing.source == "idealista":
                    unique[i] = listing
                elif listing.source == existing.source:
                    # Keep the one with more images/data
                    if len(listing.images) > len(existing.images):
                        unique[i] = listing
                break
        if not is_dup:
            unique.append(listing)
    return unique


def save_listings(listings: list[PropertyListing], filename: str = "listings.json"):
    """Save listings to JSON file in output/data/."""
    output_dir = Path(__file__).parent.parent / "output" / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename

    data = [listing.to_dict() for listing in listings]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    return output_path


def load_listings(filename: str = "listings.json") -> list[PropertyListing]:
    """Load listings from JSON file."""
    output_dir = Path(__file__).parent.parent / "output" / "data"
    output_path = output_dir / filename

    if not output_path.exists():
        return []

    with open(output_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    listings = []
    for item in data:
        # Remove fields not in dataclass
        raw = item.pop("raw_data", {})
        listing = PropertyListing(**{k: v for k, v in item.items() if hasattr(PropertyListing, k)})
        listing.raw_data = raw
        listings.append(listing)
    return listings


def extract_number(text: str) -> Optional[float]:
    """Extract first number from text, handling Italian/German formatting."""
    if not text:
        return None
    # Remove currency symbols and common separators
    text = text.replace("€", "").replace("EUR", "").strip()
    # Handle Italian number format: 1.234.567,89
    match = re.search(r"([\d.]+,\d+|[\d.]+)", text)
    if match:
        num_str = match.group(1)
        # Convert Italian format to float
        num_str = num_str.replace(".", "").replace(",", ".")
        try:
            return float(num_str)
        except ValueError:
            return None
    return None


class RateLimiter:
    """Simple rate limiter for scraping."""

    def __init__(self, min_delay: float = 2.0):
        self.min_delay = min_delay
        self.last_request_time = 0.0

    def wait(self):
        """Wait until enough time has passed since the last request."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        self.last_request_time = time.time()
