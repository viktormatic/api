#!/usr/bin/env python3
"""
Quick scrape script with Apify - fetch real listings with direct URLs.

Usage:
    export APIFY_API_TOKEN="your_token_here"
    python quick_scrape.py

Or pass token directly:
    python quick_scrape.py --token "apify_api_..."

This script:
1. Uses Apify Actor "azzouzana/immobiliare-it-listing-page-scraper-by-search-url"
   to scrape immobiliare.it (ultra-fast, ~$0.01/1K listings)
2. Uses Apify Actor "igolaizola/idealista-scraper" for idealista.it
3. Deduplicates cross-portal results
4. Analyzes each listing with the deal scorer
5. Prints a ranked table with DIRECT LINKS to the best deals
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from scrapers.utils import (
    PropertyListing,
    deduplicate_listings,
    load_config,
    load_market_data,
    save_listings,
)
from analysis.deal_scorer import rank_deals

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Priority municipalities for investment analysis
PRIORITY_MUNICIPALITIES = [
    "bolzano",
    "merano",
    "bressanone",
    "laives",
    "appiano-sulla-strada-del-vino",
    "brunico",
]

SECONDARY_MUNICIPALITIES = [
    "egna",
    "silandro",
    "vipiteno",
    "lana",
    "caldaro-sulla-strada-del-vino",
]


def scrape_immobiliare_apify(token: str, municipalities: list[str]) -> list[PropertyListing]:
    """
    Scrape immobiliare.it via Apify Actor azzouzana/immobiliare-it-listing-page-scraper-by-search-url.
    Returns PropertyListing objects with real direct URLs.
    """
    os.environ["APIFY_API_TOKEN"] = token
    config = load_config()
    all_listings = []

    from scrapers.immobiliare_scraper import ImmobiliareScraper
    scraper = ImmobiliareScraper(config)

    for muni in municipalities:
        logger.info(f"Scraping immobiliare.it via Apify: {muni}...")
        try:
            listings = scraper.scrape_via_apify(muni)
            all_listings.extend(listings)
            logger.info(f"  -> {len(listings)} immobiliare.it listings for {muni}")
        except Exception as e:
            logger.error(f"  -> immobiliare.it failed for {muni}: {e}")

    return all_listings


def scrape_idealista_apify(token: str, municipalities: list[str]) -> list[PropertyListing]:
    """
    Scrape idealista.it via Apify Actor igolaizola/idealista-scraper.
    Returns PropertyListing objects with real direct URLs.
    """
    os.environ["APIFY_API_TOKEN"] = token
    config = load_config()
    all_listings = []

    from scrapers.idealista_scraper import IdealistaScraper
    scraper = IdealistaScraper(config)

    for muni in municipalities:
        logger.info(f"Scraping idealista.it via Apify: {muni}...")
        try:
            listings = scraper.scrape_via_apify(muni)
            all_listings.extend(listings)
            logger.info(f"  -> {len(listings)} idealista.it listings for {muni}")
        except Exception as e:
            logger.error(f"  -> idealista.it failed for {muni}: {e}")

    return all_listings


def print_results(ranked_deals, show_all: bool = False):
    """Print ranked deals with direct URLs."""
    n = len(ranked_deals) if show_all else min(20, len(ranked_deals))

    print("\n" + "=" * 100)
    print("  SUEDTIROL IMMOBILIEN - TOP DEALS MIT DIREKTEN LINKS")
    print("=" * 100)

    for i, (listing, deal) in enumerate(ranked_deals[:n], 1):
        v = deal.valuation
        emoji = deal.deal_emoji
        grade = deal.deal_grade

        print(f"\n{'_' * 90}")
        print(f"  #{i} {emoji} [{grade}-DEAL] Score: {deal.total_score}/100")
        print(f"  {listing.title}")
        print(f"  Ort: {listing.municipality_de} ({listing.municipality}) | Zone: {listing.zone}")
        print(f"  Preis: EUR {listing.price:>10,.0f} | {listing.surface_area:>6.0f} m2 | {listing.rooms} Zi | {listing.condition_de}")
        print(f"  EUR/m2: EUR {listing.price_per_sqm:>6,.0f} (Markt: EUR {v.market_ref_mid:>6,.0f})")
        print(f"  Discount: {v.discount_to_market_pct:>5.1f}% | ROI: {v.roi_pct:>5.1f}% | Netto: EUR {v.net_profit:>10,.0f}")
        if deal.splitting and deal.splitting.is_splittable:
            print(f"  Splitting: JA ({deal.splitting.n_units} Einheiten) | Mehrwert: EUR {deal.splitting.net_value_add:>10,.0f}")
        print(f"")
        print(f"  DIREKT-LINK: {listing.url}")
        print(f"  Quelle: {listing.source} | Agentur: {listing.agency_name}")
        print(f"  Empfehlung: {deal.recommendation[:120]}")

    print(f"\n{'=' * 100}")
    print(f"  Gesamt: {len(ranked_deals)} Deals analysiert | Top {n} angezeigt")
    print(f"{'=' * 100}\n")


def main():
    parser = argparse.ArgumentParser(description="Quick Apify Scrape for Suedtirol Immobilien")
    parser.add_argument("--token", "-t", help="Apify API token (or set APIFY_API_TOKEN env var)")
    parser.add_argument("--portal", "-p", choices=["immobiliare", "idealista", "both"], default="both",
                        help="Which portal to scrape (default: both)")
    parser.add_argument("--all-municipalities", "-a", action="store_true", help="Include secondary municipalities")
    parser.add_argument("--top", type=int, default=20, help="Number of top deals to show (default: 20)")
    parser.add_argument("--output", "-o", default="live_results.json", help="Output file")
    args = parser.parse_args()

    token = args.token or os.environ.get("APIFY_API_TOKEN", "")
    if not token:
        print("ERROR: Provide Apify token via --token or APIFY_API_TOKEN env var")
        print("  Get your token at: https://console.apify.com/account/integrations")
        sys.exit(1)

    municipalities = PRIORITY_MUNICIPALITIES[:]
    if args.all_municipalities:
        municipalities.extend(SECONDARY_MUNICIPALITIES)

    all_listings = []

    # Scrape immobiliare.it via Apify
    if args.portal in ("immobiliare", "both"):
        immo_listings = scrape_immobiliare_apify(token, municipalities)
        all_listings.extend(immo_listings)
        logger.info(f"Immobiliare.it total: {len(immo_listings)} listings")

    # Scrape idealista.it via Apify
    if args.portal in ("idealista", "both"):
        idealista_listings = scrape_idealista_apify(token, municipalities)
        all_listings.extend(idealista_listings)
        logger.info(f"Idealista.it total: {len(idealista_listings)} listings")

    if not all_listings:
        print("\nKeine Ergebnisse gefunden. Pruefe:")
        print("  1. Apify Token gueltig? (https://console.apify.com/account/integrations)")
        print("  2. Internetverbindung OK?")
        print("  3. Apify-Guthaben vorhanden?")
        sys.exit(1)

    # Deduplicate cross-portal
    logger.info(f"Before dedup: {len(all_listings)} listings")
    all_listings = deduplicate_listings(all_listings)
    logger.info(f"After dedup: {len(all_listings)} listings")

    # Save raw data
    output_path = save_listings(all_listings, args.output)
    logger.info(f"Saved to: {output_path}")

    # Analyze and rank
    config = load_config()
    market_data = load_market_data()
    ranked = rank_deals(all_listings, config, market_data, top_n=args.top)

    # Print results with direct links
    print_results(ranked)

    # Save ranked results as JSON with URLs
    results_file = Path(__file__).parent / "output" / "data" / "top_deals.json"
    results_file.parent.mkdir(parents=True, exist_ok=True)
    top_deals_data = []
    for listing, deal in ranked:
        top_deals_data.append({
            "rank": len(top_deals_data) + 1,
            "score": deal.total_score,
            "grade": deal.deal_grade,
            "url": listing.url,
            "title": listing.title,
            "source": listing.source,
            "municipality": listing.municipality_de,
            "price": listing.price,
            "surface_area": listing.surface_area,
            "rooms": listing.rooms,
            "price_per_sqm": listing.price_per_sqm,
            "discount_pct": deal.valuation.discount_to_market_pct,
            "roi_pct": deal.valuation.roi_pct,
            "net_profit": deal.valuation.net_profit,
            "splittable": deal.splitting.is_splittable if deal.splitting else False,
            "condition": listing.condition_de,
            "agency": listing.agency_name,
        })

    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(top_deals_data, f, indent=2, ensure_ascii=False)
    print(f"\nTop deals saved to: {results_file}")
    print(f"All listings saved to: {output_path}")


if __name__ == "__main__":
    main()
