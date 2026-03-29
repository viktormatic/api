"""
Scraper for idealista.it - South Tyrol property listings.

IMPORTANT: Idealista has aggressive anti-bot measures.
Primary strategy: Use Apify Actor for reliable scraping.
Fallback: Direct HTTP scraping with residential proxies.

Apify Actor "igolaizola/idealista-scraper":
- Supports Italy, Spain, Portugal
- 70+ fields: price, GPS, photos, price history, agency
- Bypasses 1,800 listing limit automatically
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode, urljoin

import httpx
from parsel import Selector

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


class IdealistaScraper:
    """Scraper for idealista.it with Apify integration."""

    BASE_URL = "https://www.idealista.it"

    def __init__(self, config: Optional[dict] = None):
        self.config = config or load_config()
        scraping_config = self.config.get("scraping", {}).get("idealista", {})
        self.rate_limiter = RateLimiter(
            min_delay=scraping_config.get("rate_limit_seconds", 3.0)
        )
        self.max_pages = scraping_config.get("max_pages_per_municipality", 15)
        self.use_apify = scraping_config.get("use_apify", True)
        self.apify_actor = scraping_config.get("apify_actor", "igolaizola/idealista-scraper")
        self.filters = self.config.get("search_config", {}).get("filters", {})

        # HTTP client for direct scraping fallback
        self.client = httpx.Client(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "it-IT,it;q=0.9,de-DE;q=0.8,de;q=0.7",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
            follow_redirects=True,
            timeout=30.0,
        )

    def scrape_via_apify(self, municipality: str) -> list[PropertyListing]:
        """
        Use Apify Actor to scrape idealista listings.
        Requires APIFY_API_TOKEN environment variable.
        """
        try:
            from apify_client import ApifyClient
        except ImportError:
            logger.warning("apify-client not installed. Run: pip install apify-client")
            return []

        api_token = os.environ.get("APIFY_API_TOKEN", "")
        if not api_token:
            logger.warning("APIFY_API_TOKEN not set. Skipping Apify scraping.")
            return []

        client = ApifyClient(api_token)
        it_name, de_name = normalize_municipality(municipality)

        # Build search URL for the actor
        search_url = f"{self.BASE_URL}/vendita-case/{it_name}-provincia-bolzano/"
        params = {}
        if self.filters.get("price_min"):
            params["prezzoMinimo"] = self.filters["price_min"]
        if self.filters.get("price_max"):
            params["prezzoMassimo"] = self.filters["price_max"]
        if self.filters.get("surface_min"):
            params["superficieMinima"] = self.filters["surface_min"]
        if params:
            search_url += "?" + urlencode(params)

        actor_input = {
            "startUrls": [{"url": search_url}],
            "maxItems": 200,
            "proxyConfiguration": {"useApifyProxy": True, "apifyProxyGroups": ["RESIDENTIAL"]},
        }

        logger.info(f"Running Apify actor for {municipality}: {search_url}")

        try:
            run = client.actor(self.apify_actor).call(run_input=actor_input)
            dataset_items = list(
                client.dataset(run["defaultDatasetId"]).iterate_items()
            )
        except Exception as e:
            logger.error(f"Apify actor failed for {municipality}: {e}")
            return []

        logger.info(f"Apify returned {len(dataset_items)} items for {municipality}")

        listings = []
        for item in dataset_items:
            listing = self._apify_item_to_listing(item, it_name, de_name)
            if listing:
                # Check red flags
                text_to_check = f"{listing.title} {listing.description}"
                red_flags = detect_red_flags(text_to_check, self.config)
                if not red_flags:
                    listings.append(listing)
                else:
                    logger.info(f"Skipping {listing.url} due to red flags: {red_flags}")

        return listings

    def _apify_item_to_listing(
        self, item: dict, municipality_it: str, municipality_de: str
    ) -> Optional[PropertyListing]:
        """Convert Apify output item to PropertyListing."""
        try:
            # Detect condition from description
            description = item.get("description", "")
            condition, condition_de = detect_condition(description)

            # Extract price history if available
            price_history = []
            if item.get("priceHistory"):
                price_history = item["priceHistory"]

            listing = PropertyListing(
                property_id=str(item.get("propertyCode", item.get("id", ""))),
                source="idealista",
                url=item.get("url", ""),
                title=item.get("title", ""),
                description=description,
                price=float(item.get("price", 0)),
                price_per_sqm=float(item.get("pricePerSquareMeter", 0)),
                price_history=price_history,
                surface_area=float(item.get("size", item.get("surface", 0))),
                rooms=int(item.get("rooms", 0)),
                bathrooms=int(item.get("bathrooms", 0)),
                floor=item.get("floor"),
                elevator=item.get("hasLift"),
                energy_class=item.get("energyCertification", {}).get("rating", ""),
                condition=condition,
                condition_de=condition_de,
                latitude=item.get("latitude"),
                longitude=item.get("longitude"),
                address=item.get("address", ""),
                municipality=municipality_it,
                municipality_de=municipality_de,
                zone=item.get("neighborhood", item.get("district", "")),
                images=item.get("images", []),
                floor_plan_images=item.get("floorPlanImages", []),
                agency_name=item.get("contactInfo", {}).get("agencyName", ""),
                agency_phone=item.get("contactInfo", {}).get("phone", ""),
                listing_date=item.get("creationDate", ""),
                last_updated=item.get("modificationDate", ""),
                property_type=item.get("propertyType", ""),
                raw_data=item,
            )
            return listing
        except Exception as e:
            logger.warning(f"Error converting Apify item: {e}")
            return None

    def scrape_direct(self, municipality: str) -> list[PropertyListing]:
        """
        Direct HTTP scraping of idealista.it (fallback).
        Less reliable due to anti-bot measures.
        """
        it_name, de_name = normalize_municipality(municipality)
        all_listings = []

        for page in range(1, self.max_pages + 1):
            url = f"{self.BASE_URL}/vendita-case/{it_name}-provincia-bolzano/"
            if page > 1:
                url += f"pagina-{page}.htm"

            params = {}
            if self.filters.get("price_min"):
                params["prezzoMinimo"] = self.filters["price_min"]
            if self.filters.get("price_max"):
                params["prezzoMassimo"] = self.filters["price_max"]
            if self.filters.get("surface_min"):
                params["superficieMinima"] = self.filters["surface_min"]
            if params:
                url += "?" + urlencode(params)

            self.rate_limiter.wait()
            logger.info(f"Scraping idealista page: {url}")

            try:
                response = self.client.get(url)
                if response.status_code == 403:
                    logger.warning("Idealista blocked request (403). Consider using Apify.")
                    break
                response.raise_for_status()
            except httpx.HTTPError as e:
                logger.error(f"Failed to fetch {url}: {e}")
                break

            sel = Selector(text=response.text)

            # Check for CAPTCHA or block page
            if "captcha" in response.text.lower() or "access denied" in response.text.lower():
                logger.warning("Idealista CAPTCHA/block detected. Stopping direct scrape.")
                break

            # Parse listing cards
            cards = sel.css("article.item")
            if not cards:
                cards = sel.css("[class*='item-info']")

            if not cards:
                logger.info(f"No more listings found on page {page}")
                break

            for card in cards:
                listing_data = self._parse_idealista_card(card, it_name, de_name)
                if listing_data:
                    all_listings.append(listing_data)

            # Check for next page
            next_link = sel.css("a.icon-arrow-right-after::attr(href)").get()
            if not next_link:
                break

        return all_listings

    def _parse_idealista_card(
        self, card: Selector, municipality_it: str, municipality_de: str
    ) -> Optional[PropertyListing]:
        """Parse a listing card from idealista search results."""
        try:
            # Link and ID
            link = card.css("a.item-link::attr(href)").get()
            if not link:
                link = card.css("a::attr(href)").get()

            if not link:
                return None

            url = urljoin(self.BASE_URL, link)
            id_match = re.search(r"/immobile/(\d+)/", link)
            property_id = id_match.group(1) if id_match else ""

            # Title
            title = card.css("a.item-link::text").get("").strip()

            # Price
            price_text = card.css("[class*='price']::text").get("")
            price = extract_number(price_text) or 0

            # Details string (e.g., "3 locali, 85 m², 2° piano")
            details_text = " ".join(card.css("[class*='detail']::text").getall())

            surface = 0
            rooms = 0
            floor = None

            surface_match = re.search(r"(\d+)\s*m[²2]", details_text)
            if surface_match:
                surface = float(surface_match.group(1))

            rooms_match = re.search(r"(\d+)\s*local", details_text)
            if rooms_match:
                rooms = int(rooms_match.group(1))

            floor_match = re.search(r"(\d+)[°º]\s*piano", details_text)
            if floor_match:
                floor = int(floor_match.group(1))

            # Description preview
            desc = card.css("[class*='ellipsis']::text").get("").strip()

            # Check red flags
            text_to_check = f"{title} {desc}"
            red_flags = detect_red_flags(text_to_check, self.config)
            if red_flags:
                logger.info(f"Skipping {url} due to red flags: {red_flags}")
                return None

            condition, condition_de = detect_condition(text_to_check)

            return PropertyListing(
                property_id=property_id,
                source="idealista",
                url=url,
                title=title,
                description=desc,
                price=price,
                surface_area=surface,
                rooms=rooms,
                floor=floor,
                condition=condition,
                condition_de=condition_de,
                municipality=municipality_it,
                municipality_de=municipality_de,
                property_type="appartamento",
            )

        except Exception as e:
            logger.warning(f"Error parsing idealista card: {e}")
            return None

    def scrape_municipality(self, municipality: str) -> list[PropertyListing]:
        """Scrape all listings for a municipality, using Apify if configured."""
        if self.use_apify:
            listings = self.scrape_via_apify(municipality)
            if listings:
                return listings
            logger.info("Apify returned no results, falling back to direct scraping")

        return self.scrape_direct(municipality)

    def scrape_all_municipalities(self) -> list[PropertyListing]:
        """Scrape all configured target municipalities."""
        all_listings = []
        municipalities = self.config.get("search_config", {}).get(
            "target_municipalities", {}
        )

        for tier_name, tier_list in municipalities.items():
            logger.info(f"Scraping tier: {tier_name}")
            for muni in tier_list:
                name = muni if isinstance(muni, str) else muni.get("name", "")
                if name:
                    listings = self.scrape_municipality(name)
                    all_listings.extend(listings)

        logger.info(f"Total listings scraped from idealista.it: {len(all_listings)}")
        return all_listings

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def run_idealista_scraper(
    municipalities: Optional[list[str]] = None,
    output_file: str = "idealista_listings.json",
) -> list[PropertyListing]:
    """
    Run the idealista.it scraper.

    Args:
        municipalities: Optional list of municipality names. If None, scrapes all configured.
        output_file: Output filename for the results.

    Returns:
        List of PropertyListing objects.
    """
    config = load_config()

    with IdealistaScraper(config) as scraper:
        if municipalities:
            all_listings = []
            for muni in municipalities:
                listings = scraper.scrape_municipality(muni)
                all_listings.extend(listings)
        else:
            all_listings = scraper.scrape_all_municipalities()

    output_path = save_listings(all_listings, output_file)
    logger.info(f"Saved {len(all_listings)} listings to {output_path}")
    return all_listings


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    listings = run_idealista_scraper(
        municipalities=["bolzano"],
        output_file="idealista_bolzano.json",
    )
    print(f"Scraped {len(listings)} listings from Bolzano via Idealista")
    for listing in listings[:5]:
        print(
            f"  - {listing.title}: €{listing.price:,.0f} | "
            f"{listing.surface_area}m² | {listing.rooms} rooms"
        )
