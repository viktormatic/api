"""
Scraper for Facebook Marketplace and Groups - South Tyrol property listings.

Strategy:
- Facebook Marketplace: Use Apify actor for structured scraping
- Facebook Groups: Monitor known South Tyrol real estate groups
- Direct API: Facebook Graph API (limited for marketplace)

Known South Tyrol real estate Facebook groups:
- "Immobilien Südtirol / Alto Adige"
- "Wohnungen & Häuser Südtirol"
- "Immobilien Bozen / Bolzano"
- "Wohnung mieten/kaufen Südtirol"
- "Immobiliare Alto Adige / Südtirol Immobilien"

Apify actors for Facebook:
- "apify/facebook-marketplace-scraper" (Marketplace listings)
- "apify/facebook-groups-scraper" (Group posts)
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus

from .utils import (
    PropertyListing,
    RateLimiter,
    detect_condition,
    detect_red_flags,
    extract_number,
    load_config,
    normalize_municipality,
    save_listings,
)

logger = logging.getLogger(__name__)

# Known Facebook groups for South Tyrol real estate
SUEDTIROL_FB_GROUPS = [
    {
        "name": "Immobilien Südtirol / Alto Adige",
        "url": "https://www.facebook.com/groups/immobilien.suedtirol",
        "language": "de",
    },
    {
        "name": "Wohnungen & Häuser Südtirol",
        "url": "https://www.facebook.com/groups/wohnungen.suedtirol",
        "language": "de",
    },
    {
        "name": "Immobilien Bozen / Bolzano",
        "url": "https://www.facebook.com/groups/immobilien.bozen",
        "language": "de/it",
    },
    {
        "name": "Wohnung mieten/kaufen Südtirol",
        "url": "https://www.facebook.com/groups/wohnung.suedtirol",
        "language": "de",
    },
    {
        "name": "Immobiliare Alto Adige",
        "url": "https://www.facebook.com/groups/immobiliare.altoadige",
        "language": "it",
    },
    {
        "name": "Case in vendita Alto Adige - Südtirol",
        "url": "https://www.facebook.com/groups/case.altoadige",
        "language": "it",
    },
]

# South Tyrol Marketplace location parameters
MARKETPLACE_LOCATIONS = {
    "bolzano": {"lat": 46.4983, "lng": 11.3548, "radius_km": 15},
    "merano": {"lat": 46.6713, "lng": 11.1594, "radius_km": 15},
    "bressanone": {"lat": 46.7154, "lng": 11.6563, "radius_km": 20},
    "brunico": {"lat": 46.7962, "lng": 11.9365, "radius_km": 20},
    "all_suedtirol": {"lat": 46.6, "lng": 11.4, "radius_km": 60},
}


class FacebookMarketplaceScraper:
    """Scraper for Facebook Marketplace real estate listings in South Tyrol."""

    def __init__(self, config: Optional[dict] = None):
        self.config = config or load_config()
        self.filters = self.config.get("search_config", {}).get("filters", {})

    def scrape_via_apify(
        self,
        location: str = "all_suedtirol",
        max_items: int = 100,
    ) -> list[PropertyListing]:
        """
        Use Apify actor to scrape Facebook Marketplace.

        Requires APIFY_API_TOKEN environment variable.
        """
        try:
            from apify_client import ApifyClient
        except ImportError:
            logger.warning("apify-client not installed.")
            return []

        api_token = os.environ.get("APIFY_API_TOKEN", "")
        if not api_token:
            logger.warning("APIFY_API_TOKEN not set. Cannot scrape Facebook Marketplace.")
            return []

        client = ApifyClient(api_token)
        loc = MARKETPLACE_LOCATIONS.get(location, MARKETPLACE_LOCATIONS["all_suedtirol"])

        actor_input = {
            "searchQuery": "Wohnung kaufen",
            "location": {
                "latitude": loc["lat"],
                "longitude": loc["lng"],
            },
            "radiusKm": loc["radius_km"],
            "category": "propertyrentals",  # Also covers sales
            "maxItems": max_items,
            "priceMin": self.filters.get("price_min", 100000),
            "priceMax": self.filters.get("price_max", 800000),
            "proxyConfiguration": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"],
            },
        }

        logger.info(f"Running Facebook Marketplace scraper for {location}")

        try:
            # Try common actor names for FB Marketplace
            for actor_name in [
                "apify/facebook-marketplace-scraper",
                "curious_coder/facebook-marketplace-scraper",
                "lexis-solutions/facebook-marketplace-scraper",
            ]:
                try:
                    run = client.actor(actor_name).call(
                        run_input=actor_input,
                        timeout_secs=300,
                    )
                    items = list(
                        client.dataset(run["defaultDatasetId"]).iterate_items()
                    )
                    if items:
                        logger.info(f"Got {len(items)} items from {actor_name}")
                        break
                except Exception:
                    continue
            else:
                logger.warning("No working Facebook Marketplace actor found.")
                return []

        except Exception as e:
            logger.error(f"Facebook Marketplace scraping failed: {e}")
            return []

        return self._convert_marketplace_items(items)

    def _convert_marketplace_items(
        self, items: list[dict]
    ) -> list[PropertyListing]:
        """Convert Facebook Marketplace items to PropertyListing."""
        listings = []

        for item in items:
            try:
                # Extract price
                price_str = item.get("price", item.get("listing_price", ""))
                price = extract_number(str(price_str)) or 0

                # Filter by price range
                if price < self.filters.get("price_min", 0):
                    continue
                if price > self.filters.get("price_max", float("inf")):
                    continue

                # Extract details from title and description
                title = item.get("title", item.get("name", ""))
                description = item.get("description", "")
                full_text = f"{title} {description}"

                # Try to extract surface area
                surface = 0
                surface_match = re.search(r"(\d+)\s*m[²2]", full_text)
                if surface_match:
                    surface = float(surface_match.group(1))

                if surface < self.filters.get("surface_min", 0):
                    continue

                # Try to extract rooms
                rooms = 0
                rooms_match = re.search(
                    r"(\d+)\s*(?:Zimmer|Zi\.|locali|camere|Räume|rooms)", full_text, re.IGNORECASE
                )
                if rooms_match:
                    rooms = int(rooms_match.group(1))

                # Check red flags
                red_flags = detect_red_flags(full_text, self.config)
                if red_flags:
                    continue

                # Filter out rentals
                rental_keywords = [
                    "zu vermieten", "affitto", "miete", "monatlich",
                    "mensile", "al mese", "/monat",
                ]
                if any(kw in full_text.lower() for kw in rental_keywords):
                    continue

                # Must contain sale keywords
                sale_keywords = [
                    "zu verkaufen", "vendita", "verkauf", "kaufen",
                    "acquisto", "€", "eur",
                ]
                if not any(kw in full_text.lower() for kw in sale_keywords):
                    # Price alone might indicate sale
                    if price < 50000:
                        continue

                condition, condition_de = detect_condition(full_text)

                # Location
                location_str = item.get("location", item.get("address", ""))
                lat = item.get("latitude")
                lng = item.get("longitude")

                # Try to identify municipality
                municipality = ""
                municipality_de = ""
                location_lower = f"{location_str} {title}".lower()
                for it_name, de_name in [
                    ("bolzano", "Bozen"), ("merano", "Meran"),
                    ("bressanone", "Brixen"), ("brunico", "Bruneck"),
                    ("laives", "Leifers"), ("lana", "Lana"),
                    ("egna", "Neumarkt"), ("silandro", "Schlanders"),
                    ("vipiteno", "Sterzing"),
                ]:
                    if it_name in location_lower or de_name.lower() in location_lower:
                        municipality = it_name
                        municipality_de = de_name
                        break

                # Images
                images = item.get("images", item.get("photos", []))
                if isinstance(images, list) and images:
                    if isinstance(images[0], dict):
                        images = [img.get("url", img.get("link", "")) for img in images]

                listing = PropertyListing(
                    property_id=f"FB-{item.get('id', item.get('listing_id', ''))}",
                    source="facebook_marketplace",
                    url=item.get("url", item.get("link", "")),
                    title=title,
                    description=description,
                    price=price,
                    surface_area=surface,
                    rooms=rooms,
                    condition=condition,
                    condition_de=condition_de,
                    latitude=lat,
                    longitude=lng,
                    address=location_str,
                    municipality=municipality,
                    municipality_de=municipality_de,
                    property_type="appartamento",
                    images=images,
                    listing_date=item.get("created_time", item.get("date", "")),
                    raw_data=item,
                )
                listings.append(listing)

            except Exception as e:
                logger.warning(f"Error converting FB item: {e}")
                continue

        logger.info(f"Converted {len(listings)} Facebook Marketplace listings")
        return listings


class FacebookGroupScraper:
    """Monitor Facebook groups for South Tyrol real estate posts."""

    def __init__(self, config: Optional[dict] = None):
        self.config = config or load_config()
        self.filters = self.config.get("search_config", {}).get("filters", {})

    def scrape_groups_via_apify(
        self,
        groups: Optional[list[dict]] = None,
        max_posts: int = 50,
    ) -> list[PropertyListing]:
        """
        Scrape Facebook group posts using Apify.

        Args:
            groups: List of group dicts with 'url' key. Defaults to SUEDTIROL_FB_GROUPS.
            max_posts: Max posts per group.
        """
        try:
            from apify_client import ApifyClient
        except ImportError:
            logger.warning("apify-client not installed.")
            return []

        api_token = os.environ.get("APIFY_API_TOKEN", "")
        if not api_token:
            logger.warning("APIFY_API_TOKEN not set.")
            return []

        if groups is None:
            groups = SUEDTIROL_FB_GROUPS

        client = ApifyClient(api_token)
        all_listings = []

        for group in groups:
            logger.info(f"Scraping FB group: {group['name']}")

            actor_input = {
                "startUrls": [{"url": group["url"]}],
                "maxPosts": max_posts,
                "proxyConfiguration": {
                    "useApifyProxy": True,
                    "apifyProxyGroups": ["RESIDENTIAL"],
                },
            }

            try:
                for actor_name in [
                    "apify/facebook-groups-scraper",
                    "apify/facebook-posts-scraper",
                ]:
                    try:
                        run = client.actor(actor_name).call(
                            run_input=actor_input,
                            timeout_secs=300,
                        )
                        items = list(
                            client.dataset(run["defaultDatasetId"]).iterate_items()
                        )
                        if items:
                            break
                    except Exception:
                        continue
                else:
                    logger.warning(f"No working actor for group: {group['name']}")
                    continue

                listings = self._convert_group_posts(items, group)
                all_listings.extend(listings)

            except Exception as e:
                logger.error(f"Failed to scrape group {group['name']}: {e}")

        logger.info(f"Total from Facebook groups: {len(all_listings)} listings")
        return all_listings

    def _convert_group_posts(
        self, posts: list[dict], group: dict
    ) -> list[PropertyListing]:
        """Convert Facebook group posts to PropertyListing objects."""
        listings = []

        for post in posts:
            try:
                text = post.get("text", post.get("message", ""))
                if not text:
                    continue

                # Must be a sale post
                sale_indicators = [
                    "verkauf", "zu verkaufen", "vendesi", "vendita",
                    "vendo", "in vendita", "prezzo", "preis",
                    "kaufen", "€",
                ]
                if not any(kw in text.lower() for kw in sale_indicators):
                    continue

                # Must NOT be rental
                rental_indicators = [
                    "zu vermieten", "affitto", "affittasi", "miete",
                    "monatlich", "mensile",
                ]
                if any(kw in text.lower() for kw in rental_indicators):
                    continue

                # Extract price
                price = 0
                price_patterns = [
                    r"(?:preis|prezzo|€)\s*[:.]?\s*([\d.,]+)\s*(?:€|EUR|euro)?",
                    r"([\d.,]+)\s*(?:€|EUR|euro)",
                    r"€\s*([\d.,]+)",
                ]
                for pattern in price_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        price = extract_number(match.group(1)) or 0
                        if price > 10000:  # Reasonable property price
                            break

                if price < self.filters.get("price_min", 0):
                    continue

                # Extract surface area
                surface = 0
                surface_match = re.search(r"(\d+)\s*m[²2]", text)
                if surface_match:
                    surface = float(surface_match.group(1))

                # Extract rooms
                rooms = 0
                rooms_match = re.search(
                    r"(\d+)\s*(?:Zimmer|Zi\.|locali|camere|Räume|vani)",
                    text, re.IGNORECASE,
                )
                if rooms_match:
                    rooms = int(rooms_match.group(1))

                # Check red flags
                red_flags = detect_red_flags(text, self.config)
                if red_flags:
                    continue

                condition, condition_de = detect_condition(text)

                # Try to identify municipality
                municipality = ""
                municipality_de = ""
                text_lower = text.lower()
                for it_name, de_name in [
                    ("bolzano", "Bozen"), ("merano", "Meran"),
                    ("bressanone", "Brixen"), ("brunico", "Bruneck"),
                    ("laives", "Leifers"), ("lana", "Lana"),
                    ("egna", "Neumarkt"), ("silandro", "Schlanders"),
                    ("vipiteno", "Sterzing"), ("appiano", "Eppan"),
                    ("caldaro", "Kaltern"), ("renon", "Ritten"),
                ]:
                    if it_name in text_lower or de_name.lower() in text_lower:
                        municipality = it_name
                        municipality_de = de_name
                        break

                # Images from post
                images = post.get("images", post.get("photos", []))
                if isinstance(images, list) and images:
                    if isinstance(images[0], dict):
                        images = [img.get("url", img.get("full", "")) for img in images]

                listing = PropertyListing(
                    property_id=f"FBG-{post.get('id', post.get('postId', ''))}",
                    source=f"facebook_group:{group['name']}",
                    url=post.get("url", post.get("postUrl", "")),
                    title=text[:100].strip(),
                    description=text,
                    price=price,
                    surface_area=surface,
                    rooms=rooms,
                    condition=condition,
                    condition_de=condition_de,
                    municipality=municipality,
                    municipality_de=municipality_de,
                    property_type="appartamento",
                    images=images,
                    listing_date=post.get("time", post.get("timestamp", "")),
                    raw_data=post,
                )
                listings.append(listing)

            except Exception as e:
                logger.warning(f"Error converting group post: {e}")

        return listings


def run_facebook_scraper(
    location: str = "all_suedtirol",
    include_groups: bool = True,
    output_file: str = "facebook_listings.json",
) -> list[PropertyListing]:
    """
    Run Facebook Marketplace and Groups scraper.

    Args:
        location: Location key (bolzano, merano, all_suedtirol, etc.)
        include_groups: Whether to also scrape Facebook groups.
        output_file: Output filename.

    Returns:
        List of PropertyListing objects.
    """
    config = load_config()
    all_listings = []

    # Marketplace
    mp_scraper = FacebookMarketplaceScraper(config)
    mp_listings = mp_scraper.scrape_via_apify(location)
    all_listings.extend(mp_listings)
    logger.info(f"Facebook Marketplace: {len(mp_listings)} listings")

    # Groups
    if include_groups:
        group_scraper = FacebookGroupScraper(config)
        group_listings = group_scraper.scrape_groups_via_apify()
        all_listings.extend(group_listings)
        logger.info(f"Facebook Groups: {len(group_listings)} listings")

    # Save
    if all_listings:
        output_path = save_listings(all_listings, output_file)
        logger.info(f"Saved {len(all_listings)} Facebook listings to {output_path}")

    return all_listings


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    listings = run_facebook_scraper()
    print(f"Found {len(listings)} listings from Facebook")
