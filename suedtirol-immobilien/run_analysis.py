#!/usr/bin/env python3
"""
Main runner script for Südtirol Immobilien Investment Analyzer.

Usage:
    python run_analysis.py --municipality bolzano
    python run_analysis.py --all
    python run_analysis.py --analyze-stored
    python run_analysis.py --report <listing_id>
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from scrapers.utils import (
    PropertyListing,
    deduplicate_listings,
    load_config,
    load_listings,
    load_market_data,
    save_listings,
)
from scrapers.immobiliare_scraper import ImmobiliareScraper
from scrapers.idealista_scraper import IdealistaScraper
from analysis.deal_scorer import rank_deals, score_deal
from analysis.valuation import valuate_property
from mcp_server.tools.report_generator import generate_deal_report, generate_summary_table

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def scrape_municipality(municipality: str, portal: str = "both") -> list[PropertyListing]:
    """Scrape listings for a single municipality."""
    config = load_config()
    all_listings = []

    if portal in ("immobiliare", "both"):
        logger.info(f"Scraping immobiliare.it for {municipality}...")
        with ImmobiliareScraper(config) as scraper:
            listings = scraper.scrape_municipality(municipality)
            all_listings.extend(listings)
            logger.info(f"  Found {len(listings)} listings on immobiliare.it")

    if portal in ("idealista", "both"):
        logger.info(f"Scraping idealista.it for {municipality}...")
        with IdealistaScraper(config) as scraper:
            listings = scraper.scrape_municipality(municipality)
            all_listings.extend(listings)
            logger.info(f"  Found {len(listings)} listings on idealista.it")

    return all_listings


def scrape_all_municipalities(portal: str = "both") -> list[PropertyListing]:
    """Scrape all configured municipalities."""
    config = load_config()
    municipalities = config.get("search_config", {}).get("target_municipalities", {})
    all_listings = []

    for tier_name, tier_list in municipalities.items():
        logger.info(f"\n{'='*50}")
        logger.info(f"Scraping tier: {tier_name}")
        logger.info(f"{'='*50}")

        for muni in tier_list:
            name = muni if isinstance(muni, str) else muni.get("name", "")
            if name:
                listings = scrape_municipality(name, portal)
                all_listings.extend(listings)

    return all_listings


def analyze_and_rank(listings: list[PropertyListing], top_n: int = 10):
    """Analyze listings and print ranked results."""
    config = load_config()
    market_data = load_market_data()

    logger.info(f"\nAnalyzing {len(listings)} listings...")
    ranked = rank_deals(listings, config, market_data, top_n=top_n)

    if not ranked:
        logger.info("No deals found matching criteria.")
        return []

    # Print summary table
    print("\n" + "=" * 80)
    print("TOP DEALS - Südtirol Immobilien Investment Analyse")
    print("=" * 80 + "\n")
    print(generate_summary_table(ranked))

    # Print detailed info for top deals
    for i, (listing, deal) in enumerate(ranked[:5], 1):
        print(f"\n{'─' * 60}")
        print(f"#{i} {deal.deal_emoji} Score: {deal.total_score} | {listing.title}")
        print(f"   Preis: €{listing.price:,.0f} | {listing.surface_area}m² | {listing.rooms} Zimmer")
        print(f"   €/m²: €{listing.price_per_sqm:,.0f} (Markt: €{deal.valuation.market_ref_mid:,.0f})")
        print(f"   Discount: {deal.valuation.discount_to_market_pct:.1f}% | ROI: {deal.valuation.roi_pct:.1f}%")
        print(f"   Netto-Gewinn: €{deal.valuation.net_profit:,.0f}")
        print(f"   {listing.municipality_de} ({listing.municipality})")
        print(f"   {listing.url}")
        print(f"   Empfehlung: {deal.recommendation[:100]}...")

    return ranked


def generate_reports(ranked_deals, output_dir: str = "output/reports"):
    """Generate detailed reports for top deals."""
    output_path = Path(__file__).parent / output_dir
    output_path.mkdir(parents=True, exist_ok=True)

    for i, (listing, deal) in enumerate(ranked_deals, 1):
        if deal.deal_grade in ("A", "B"):
            report = generate_deal_report(listing, deal, format="markdown")
            filename = f"deal_{i:02d}_{listing.property_id}_{listing.municipality}.md"
            filepath = output_path / filename
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(report)
            logger.info(f"Report saved: {filepath}")

            # Also save JSON version
            json_report = generate_deal_report(listing, deal, format="json")
            json_path = output_path / filename.replace(".md", ".json")
            with open(json_path, "w", encoding="utf-8") as f:
                f.write(json_report)


def main():
    parser = argparse.ArgumentParser(
        description="Südtirol Immobilien Investment Analyzer"
    )
    parser.add_argument(
        "--municipality", "-m",
        help="Municipality to scrape (e.g., 'bolzano', 'merano')",
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Scrape all configured municipalities",
    )
    parser.add_argument(
        "--portal", "-p",
        choices=["immobiliare", "idealista", "both"],
        default="both",
        help="Which portal to scrape (default: both)",
    )
    parser.add_argument(
        "--analyze-stored",
        action="store_true",
        help="Analyze previously stored listings",
    )
    parser.add_argument(
        "--report",
        help="Generate report for a specific listing ID",
    )
    parser.add_argument(
        "--top", "-t",
        type=int,
        default=10,
        help="Number of top deals to show (default: 10)",
    )
    parser.add_argument(
        "--output", "-o",
        default="listings.json",
        help="Output filename for scraped data",
    )

    args = parser.parse_args()

    if args.report:
        # Generate report for specific listing
        config = load_config()
        market_data = load_market_data()
        listings = load_listings()

        listing = None
        for l in listings:
            if l.property_id == args.report:
                listing = l
                break

        if not listing:
            print(f"Listing {args.report} not found.")
            sys.exit(1)

        deal = score_deal(listing, config, market_data)
        report = generate_deal_report(listing, deal)
        print(report)
        return

    if args.analyze_stored:
        # Analyze stored listings
        listings = load_listings(args.output)
        if not listings:
            print("No stored listings found. Run scraping first.")
            sys.exit(1)
        ranked = analyze_and_rank(listings, args.top)
        if ranked:
            generate_reports(ranked)
        return

    # Scrape
    if args.municipality:
        listings = scrape_municipality(args.municipality, args.portal)
    elif args.all:
        listings = scrape_all_municipalities(args.portal)
    else:
        parser.print_help()
        sys.exit(1)

    if not listings:
        print("No listings found.")
        sys.exit(1)

    # Deduplicate
    logger.info(f"\nTotal listings before deduplication: {len(listings)}")
    listings = deduplicate_listings(listings)
    logger.info(f"After deduplication: {len(listings)}")

    # Save
    output_path = save_listings(listings, args.output)
    logger.info(f"Saved to: {output_path}")

    # Analyze and rank
    ranked = analyze_and_rank(listings, args.top)
    if ranked:
        generate_reports(ranked)

    print(f"\nDone. {len(listings)} listings processed, top {min(args.top, len(ranked))} deals identified.")


if __name__ == "__main__":
    main()
