"""
Scraper for immobiliare.it - South Tyrol property listings.

Scraping strategy:
1. Build search URLs for each target municipality
2. Extract listings from search result pages (ID, price, area, rooms, address, agency)
3. Scrape detail pages (description, floor plan images, energy class, floor)
4. Store structured data in JSON

Alternative: Use Apify Actor "igolaizola/immobiliare-it-scraper" for managed scraping.
"""

import json
import logging
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


class ImmobiliareScraper:
    """Scraper for immobiliare.it property listings in South Tyrol."""

    BASE_URL = "https://www.immobiliare.it"

    def __init__(self, config: Optional[dict] = None):
        self.config = config or load_config()
        scraping_config = self.config.get("scraping", {}).get("immobiliare", {})
        self.rate_limiter = RateLimiter(
            min_delay=scraping_config.get("rate_limit_seconds", 2.0)
        )
        self.max_pages = scraping_config.get("max_pages_per_municipality", 20)
        self.user_agent = scraping_config.get(
            "user_agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )
        self.client = httpx.Client(
            headers={
                "User-Agent": self.user_agent,
                "Accept-Language": "it-IT,it;q=0.9,de-DE;q=0.8,de;q=0.7,en;q=0.5",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
            follow_redirects=True,
            timeout=30.0,
        )
        self.filters = self.config.get("search_config", {}).get("filters", {})

    def build_search_url(self, municipality: str, page: int = 1) -> str:
        """Build immobiliare.it search URL for a given municipality."""
        params = {}

        if self.filters.get("price_min"):
            params["prezzoMinimo"] = self.filters["price_min"]
        if self.filters.get("price_max"):
            params["prezzoMassimo"] = self.filters["price_max"]
        if self.filters.get("surface_min"):
            params["superficieMinima"] = self.filters["surface_min"]
        if self.filters.get("surface_max"):
            params["superficieMassima"] = self.filters["surface_max"]
        if self.filters.get("rooms_min"):
            params["localiMinimo"] = self.filters["rooms_min"]

        if page > 1:
            params["pag"] = page

        query_string = urlencode(params)
        # immobiliare.it URL pattern: /vendita-case/bolzano/
        base = f"{self.BASE_URL}/vendita-case/{municipality}/"
        if query_string:
            return f"{base}?{query_string}"
        return base

    def build_detail_url(self, listing_id: str) -> str:
        """Build detail page URL."""
        return f"{self.BASE_URL}/annunci/{listing_id}/"

    def scrape_search_page(self, url: str) -> tuple[list[dict], Optional[str]]:
        """
        Scrape a search results page.
        Returns (list of listing summaries, next page URL or None).
        """
        self.rate_limiter.wait()
        logger.info(f"Scraping search page: {url}")

        try:
            response = self.client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return [], None

        sel = Selector(text=response.text)
        listings = []

        # immobiliare.it uses structured listing cards
        # Each listing is within an <li> with data attributes or specific classes
        listing_cards = sel.css("li.nd-list__item.in-realEstateResults__item")

        if not listing_cards:
            # Alternative selector pattern
            listing_cards = sel.css("[class*='RealEstateResult']")

        if not listing_cards:
            # Try JSON-LD structured data
            json_ld_scripts = sel.css('script[type="application/ld+json"]::text').getall()
            for script_text in json_ld_scripts:
                try:
                    data = json.loads(script_text)
                    if isinstance(data, list):
                        for item in data:
                            if item.get("@type") in ("Product", "RealEstateListing", "Residence"):
                                listings.append(self._parse_json_ld(item))
                    elif data.get("@type") in ("Product", "RealEstateListing", "Residence"):
                        listings.append(self._parse_json_ld(data))
                except json.JSONDecodeError:
                    continue

        for card in listing_cards:
            listing_data = self._parse_listing_card(card)
            if listing_data:
                listings.append(listing_data)

        # Find next page link
        next_page = None
        next_link = sel.css("a[class*='pager-next']::attr(href)").get()
        if not next_link:
            next_link = sel.css("a[aria-label='next']::attr(href)").get()
        if not next_link:
            next_link = sel.css("link[rel='next']::attr(href)").get()
        if next_link:
            next_page = urljoin(self.BASE_URL, next_link)

        logger.info(f"Found {len(listings)} listings on page")
        return listings, next_page

    def _parse_listing_card(self, card: Selector) -> Optional[dict]:
        """Parse a listing card from search results."""
        try:
            data = {}

            # Extract listing link and ID
            link = card.css("a[href*='/annunci/']::attr(href)").get()
            if not link:
                link = card.css("a::attr(href)").get()

            if link:
                data["url"] = urljoin(self.BASE_URL, link)
                # Extract ID from URL
                id_match = re.search(r"/annunci/(\d+)/", link)
                if id_match:
                    data["property_id"] = id_match.group(1)

            # Title
            title = card.css("a.in-card__title::text").get()
            if not title:
                title = card.css("[class*='title']::text").get()
            data["title"] = (title or "").strip()

            # Price
            price_text = card.css("[class*='price']::text").get()
            if price_text:
                price = extract_number(price_text)
                if price:
                    data["price"] = price

            # Surface area
            surface_text = card.css("[aria-label*='superficie']::text").get()
            if not surface_text:
                # Try extracting from feature list
                features_text = " ".join(card.css("[class*='feature']::text").getall())
                surface_match = re.search(r"(\d+)\s*m[²2]", features_text)
                if surface_match:
                    data["surface_area"] = float(surface_match.group(1))
            else:
                surface = extract_number(surface_text)
                if surface:
                    data["surface_area"] = surface

            # Rooms
            rooms_text = card.css("[aria-label*='locali']::text").get()
            if rooms_text:
                rooms = extract_number(rooms_text)
                if rooms:
                    data["rooms"] = int(rooms)

            # Bathrooms
            bath_text = card.css("[aria-label*='bagn']::text").get()
            if bath_text:
                baths = extract_number(bath_text)
                if baths:
                    data["bathrooms"] = int(baths)

            # Floor
            floor_text = card.css("[aria-label*='piano']::text").get()
            if floor_text:
                floor_match = re.search(r"(\d+)", floor_text)
                if floor_match:
                    data["floor"] = int(floor_match.group(1))

            # Location
            location = card.css("[class*='address']::text").get()
            if not location:
                location = card.css("[class*='location']::text").get()
            data["address"] = (location or "").strip()

            # Agency
            agency = card.css("[class*='agency']::text").get()
            data["agency_name"] = (agency or "").strip()

            # Image
            img = card.css("img::attr(src)").get()
            if img:
                data["images"] = [img]

            return data if data.get("property_id") or data.get("url") else None

        except Exception as e:
            logger.warning(f"Error parsing listing card: {e}")
            return None

    def _parse_json_ld(self, data: dict) -> dict:
        """Parse JSON-LD structured data."""
        result = {}
        result["title"] = data.get("name", "")
        result["description"] = data.get("description", "")

        if "offers" in data:
            offers = data["offers"]
            if isinstance(offers, list):
                offers = offers[0]
            result["price"] = float(offers.get("price", 0))

        if "url" in data:
            result["url"] = data["url"]
            id_match = re.search(r"/annunci/(\d+)/", data["url"])
            if id_match:
                result["property_id"] = id_match.group(1)

        if "geo" in data:
            result["latitude"] = data["geo"].get("latitude")
            result["longitude"] = data["geo"].get("longitude")

        return result

    def scrape_detail_page(self, url: str) -> dict:
        """Scrape detailed information from a listing page."""
        self.rate_limiter.wait()
        logger.info(f"Scraping detail page: {url}")

        try:
            response = self.client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch detail page {url}: {e}")
            return {}

        sel = Selector(text=response.text)
        details = {}

        # Full description
        desc_parts = sel.css("[class*='description'] .in-readAll::text").getall()
        if not desc_parts:
            desc_parts = sel.css("[class*='description']::text").getall()
        details["description"] = " ".join(p.strip() for p in desc_parts if p.strip())

        # Property features table
        feature_items = sel.css("dl[class*='features'] dt, dl[class*='features'] dd")
        current_key = ""
        for item in feature_items:
            if item.root.tag == "dt":
                current_key = item.css("::text").get("").strip().lower()
            elif item.root.tag == "dd" and current_key:
                value = item.css("::text").get("").strip()
                if "superficie" in current_key or "fläche" in current_key:
                    area = extract_number(value)
                    if area:
                        details["surface_area"] = area
                elif "local" in current_key or "zimmer" in current_key:
                    rooms = extract_number(value)
                    if rooms:
                        details["rooms"] = int(rooms)
                elif "bagn" in current_key or "bad" in current_key:
                    baths = extract_number(value)
                    if baths:
                        details["bathrooms"] = int(baths)
                elif "piano" in current_key or "etage" in current_key:
                    floor_match = re.search(r"(\d+)", value)
                    if floor_match:
                        details["floor"] = int(floor_match.group(1))
                elif "ascensore" in current_key or "aufzug" in current_key:
                    details["elevator"] = value.lower() in ("sì", "si", "ja", "yes")
                elif "riscaldamento" in current_key or "heizung" in current_key:
                    details["heating_type"] = value
                elif "classe energetica" in current_key or "energieklasse" in current_key:
                    details["energy_class"] = value.strip().upper()
                elif "anno" in current_key or "baujahr" in current_key:
                    year = extract_number(value)
                    if year and 1800 < year < 2030:
                        details["year_built"] = int(year)
                elif "stato" in current_key or "zustand" in current_key:
                    details["condition_raw"] = value
                elif "balcon" in current_key:
                    details["balcony"] = True
                elif "terrazza" in current_key or "terrasse" in current_key:
                    details["terrace"] = True
                elif "giardino" in current_key or "garten" in current_key:
                    details["garden"] = True
                elif "garage" in current_key or "box" in current_key:
                    details["garage"] = True
                elif "cantina" in current_key or "keller" in current_key:
                    details["cellar"] = True

        # All images
        images = sel.css("[class*='gallery'] img::attr(src)").getall()
        if not images:
            images = sel.css("img[src*='pwm.im-cdn']::attr(src)").getall()
        details["images"] = list(set(images))

        # Floor plan images (often identifiable by filename or alt text)
        floor_plans = []
        for img in sel.css("img"):
            src = img.attrib.get("src", "")
            alt = img.attrib.get("alt", "").lower()
            if any(
                kw in alt or kw in src.lower()
                for kw in ["planimetria", "piantina", "grundriss", "floor_plan", "floorplan"]
            ):
                floor_plans.append(src)
        details["floor_plan_images"] = floor_plans

        # GPS coordinates from embedded map or meta tags
        lat_meta = sel.css("meta[property='place:location:latitude']::attr(content)").get()
        lon_meta = sel.css("meta[property='place:location:longitude']::attr(content)").get()
        if lat_meta and lon_meta:
            try:
                details["latitude"] = float(lat_meta)
                details["longitude"] = float(lon_meta)
            except ValueError:
                pass

        # Try to extract from page scripts
        if "latitude" not in details:
            scripts = sel.css("script::text").getall()
            for script in scripts:
                lat_match = re.search(r'"latitude":\s*([\d.]+)', script)
                lon_match = re.search(r'"longitude":\s*([\d.]+)', script)
                if lat_match and lon_match:
                    try:
                        details["latitude"] = float(lat_match.group(1))
                        details["longitude"] = float(lon_match.group(1))
                    except ValueError:
                        pass
                    break

        # Agency info
        agency = sel.css("[class*='agency'] [class*='name']::text").get()
        if agency:
            details["agency_name"] = agency.strip()
        phone = sel.css("[class*='agency'] a[href^='tel:']::attr(href)").get()
        if phone:
            details["agency_phone"] = phone.replace("tel:", "")

        # Listing date
        date_text = sel.css("[class*='date']::text").get()
        if date_text:
            details["listing_date"] = date_text.strip()

        # JSON-LD data as fallback
        json_ld_scripts = sel.css('script[type="application/ld+json"]::text').getall()
        for script_text in json_ld_scripts:
            try:
                ld_data = json.loads(script_text)
                if isinstance(ld_data, dict):
                    if "geo" in ld_data and "latitude" not in details:
                        details["latitude"] = ld_data["geo"].get("latitude")
                        details["longitude"] = ld_data["geo"].get("longitude")
                    if "floorSize" in ld_data and "surface_area" not in details:
                        area = extract_number(str(ld_data["floorSize"].get("value", "")))
                        if area:
                            details["surface_area"] = area
            except (json.JSONDecodeError, AttributeError):
                continue

        return details

    def scrape_municipality(self, municipality: str) -> list[PropertyListing]:
        """Scrape all listings for a given municipality."""
        logger.info(f"Starting scrape for municipality: {municipality}")
        it_name, de_name = normalize_municipality(municipality)

        all_summaries = []
        url = self.build_search_url(it_name)

        for page_num in range(1, self.max_pages + 1):
            summaries, next_url = self.scrape_search_page(url)
            all_summaries.extend(summaries)

            if not next_url or not summaries:
                break
            url = next_url
            logger.info(f"Moving to page {page_num + 1}")

        logger.info(
            f"Found {len(all_summaries)} total listings for {municipality}"
        )

        # Scrape detail pages and build PropertyListing objects
        listings = []
        red_flag_config = self.config

        for summary in all_summaries:
            detail_url = summary.get("url", "")
            if not detail_url and summary.get("property_id"):
                detail_url = self.build_detail_url(summary["property_id"])

            if not detail_url:
                continue

            # Fetch detail page
            details = self.scrape_detail_page(detail_url)

            # Merge summary and detail data
            merged = {**summary, **details}

            # Check for red flags
            text_to_check = f"{merged.get('title', '')} {merged.get('description', '')}"
            red_flags = detect_red_flags(text_to_check, red_flag_config)
            if red_flags:
                logger.info(
                    f"Skipping {detail_url} due to red flags: {red_flags}"
                )
                continue

            # Detect condition
            condition, condition_de = detect_condition(text_to_check)

            # Build PropertyListing
            listing = PropertyListing(
                property_id=merged.get("property_id", ""),
                source="immobiliare",
                url=detail_url,
                title=merged.get("title", ""),
                description=merged.get("description", ""),
                price=merged.get("price", 0),
                surface_area=merged.get("surface_area", 0),
                rooms=merged.get("rooms", 0),
                bathrooms=merged.get("bathrooms", 0),
                floor=merged.get("floor"),
                elevator=merged.get("elevator"),
                balcony=merged.get("balcony"),
                terrace=merged.get("terrace"),
                garden=merged.get("garden"),
                garage=merged.get("garage"),
                cellar=merged.get("cellar"),
                energy_class=merged.get("energy_class", ""),
                heating_type=merged.get("heating_type", ""),
                year_built=merged.get("year_built"),
                condition=condition,
                condition_de=condition_de,
                latitude=merged.get("latitude"),
                longitude=merged.get("longitude"),
                address=merged.get("address", ""),
                municipality=it_name,
                municipality_de=de_name,
                zone=merged.get("zone", ""),
                images=merged.get("images", []),
                floor_plan_images=merged.get("floor_plan_images", []),
                agency_name=merged.get("agency_name", ""),
                agency_phone=merged.get("agency_phone", ""),
                listing_date=merged.get("listing_date", ""),
                property_type=merged.get("property_type", "appartamento"),
                raw_data=merged,
            )
            listings.append(listing)

        logger.info(
            f"Completed scraping {municipality}: {len(listings)} valid listings"
        )
        return listings

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

        logger.info(f"Total listings scraped from immobiliare.it: {len(all_listings)}")
        return all_listings

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def run_immobiliare_scraper(
    municipalities: Optional[list[str]] = None,
    output_file: str = "immobiliare_listings.json",
) -> list[PropertyListing]:
    """
    Convenience function to run the immobiliare.it scraper.

    Args:
        municipalities: Optional list of municipality names. If None, scrapes all configured.
        output_file: Output filename for the results.

    Returns:
        List of PropertyListing objects.
    """
    config = load_config()

    with ImmobiliareScraper(config) as scraper:
        if municipalities:
            all_listings = []
            for muni in municipalities:
                listings = scraper.scrape_municipality(muni)
                all_listings.extend(listings)
        else:
            all_listings = scraper.scrape_all_municipalities()

    # Save results
    output_path = save_listings(all_listings, output_file)
    logger.info(f"Saved {len(all_listings)} listings to {output_path}")

    return all_listings


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Example: Scrape only Bozen as proof of concept
    listings = run_immobiliare_scraper(
        municipalities=["bolzano"],
        output_file="immobiliare_bolzano.json",
    )
    print(f"Scraped {len(listings)} listings from Bozen/Bolzano")
    for listing in listings[:5]:
        print(
            f"  - {listing.title}: €{listing.price:,.0f} | "
            f"{listing.surface_area}m² | {listing.rooms} rooms"
        )
