"""
MCP Server for Südtirol Immobilien Investment Analyzer.

Provides tools for property search, analysis, floor plan evaluation,
renovation cost calculation, and report generation.
"""

import json
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, Resource

from scrapers.utils import load_config, load_market_data, load_listings, PropertyListing
from scrapers.immobiliare_scraper import ImmobiliareScraper
from scrapers.idealista_scraper import IdealistaScraper
from analysis.valuation import valuate_property, batch_valuate
from analysis.deal_scorer import score_deal, rank_deals
from analysis.floor_plan_analyzer import analyze_splitting_potential
from analysis.renovation_calculator import create_renovation_plan, estimate_renovation_for_listing

logger = logging.getLogger(__name__)

app = Server("suedtirol-immobilien")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available MCP tools."""
    return [
        Tool(
            name="search_properties",
            description="Search for property listings in South Tyrol municipalities. Scrapes immobiliare.it and optionally idealista.it.",
            inputSchema={
                "type": "object",
                "properties": {
                    "municipality": {
                        "type": "string",
                        "description": "Municipality name (Italian or German), e.g. 'bolzano', 'Bozen', 'merano'"
                    },
                    "max_price": {
                        "type": "number",
                        "description": "Maximum price in EUR"
                    },
                    "min_surface": {
                        "type": "number",
                        "description": "Minimum surface area in m²"
                    },
                    "portal": {
                        "type": "string",
                        "enum": ["immobiliare", "idealista", "both"],
                        "description": "Which portal to search (default: immobiliare)"
                    },
                },
                "required": ["municipality"],
            },
        ),
        Tool(
            name="analyze_deal",
            description="Perform full deal analysis on a property listing including valuation, renovation estimate, splitting potential, and deal scoring.",
            inputSchema={
                "type": "object",
                "properties": {
                    "listing_id": {
                        "type": "string",
                        "description": "Property listing ID"
                    },
                    "source": {
                        "type": "string",
                        "enum": ["immobiliare", "idealista"],
                        "description": "Source portal of the listing"
                    },
                    "include_splitting": {
                        "type": "boolean",
                        "description": "Include apartment splitting analysis (default: true)"
                    },
                },
                "required": ["listing_id"],
            },
        ),
        Tool(
            name="analyze_floor_plan",
            description="Analyze a floor plan image for apartment splitting potential. Can use AI vision if an API key is available.",
            inputSchema={
                "type": "object",
                "properties": {
                    "image_url": {
                        "type": "string",
                        "description": "URL of the floor plan image"
                    },
                    "surface_area": {
                        "type": "number",
                        "description": "Known total surface area in m² (for calibration)"
                    },
                    "use_ai": {
                        "type": "boolean",
                        "description": "Use AI vision model for analysis (requires API key)"
                    },
                },
                "required": ["image_url"],
            },
        ),
        Tool(
            name="calculate_renovation",
            description="Calculate renovation costs for a property based on area, condition, and specific work items.",
            inputSchema={
                "type": "object",
                "properties": {
                    "surface_area": {
                        "type": "number",
                        "description": "Property surface area in m²"
                    },
                    "level": {
                        "type": "string",
                        "enum": ["leicht", "mittel", "schwer", "luxus"],
                        "description": "Renovation level"
                    },
                    "bathrooms_new": {
                        "type": "integer",
                        "description": "Number of new bathrooms to add"
                    },
                    "kitchen_new": {
                        "type": "boolean",
                        "description": "Whether to install a new kitchen"
                    },
                    "splitting": {
                        "type": "boolean",
                        "description": "Whether apartment splitting is planned"
                    },
                    "n_split_units": {
                        "type": "integer",
                        "description": "Number of units to split into (if splitting)"
                    },
                },
                "required": ["surface_area", "level"],
            },
        ),
        Tool(
            name="get_market_data",
            description="Get current market prices and reference data for a South Tyrol municipality.",
            inputSchema={
                "type": "object",
                "properties": {
                    "municipality": {
                        "type": "string",
                        "description": "Municipality name (Italian or German)"
                    },
                    "zone": {
                        "type": "string",
                        "description": "Specific zone/district within the municipality"
                    },
                },
                "required": ["municipality"],
            },
        ),
        Tool(
            name="compare_listings",
            description="Compare multiple property listings side by side with deal scores.",
            inputSchema={
                "type": "object",
                "properties": {
                    "listing_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of listing IDs to compare"
                    },
                },
                "required": ["listing_ids"],
            },
        ),
        Tool(
            name="generate_report",
            description="Generate a detailed deal report for a property listing.",
            inputSchema={
                "type": "object",
                "properties": {
                    "listing_id": {
                        "type": "string",
                        "description": "Property listing ID"
                    },
                    "format": {
                        "type": "string",
                        "enum": ["markdown", "json"],
                        "description": "Output format (default: markdown)"
                    },
                },
                "required": ["listing_id"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    config = load_config()
    market_data = load_market_data()

    if name == "search_properties":
        return await _search_properties(arguments, config)
    elif name == "analyze_deal":
        return await _analyze_deal(arguments, config, market_data)
    elif name == "analyze_floor_plan":
        return await _analyze_floor_plan(arguments)
    elif name == "calculate_renovation":
        return await _calculate_renovation(arguments, market_data)
    elif name == "get_market_data":
        return await _get_market_data(arguments, market_data)
    elif name == "compare_listings":
        return await _compare_listings(arguments, config, market_data)
    elif name == "generate_report":
        return await _generate_report(arguments, config, market_data)
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def _search_properties(args: dict, config: dict) -> list[TextContent]:
    """Search for properties."""
    municipality = args["municipality"]
    portal = args.get("portal", "immobiliare")

    listings = []

    if portal in ("immobiliare", "both"):
        with ImmobiliareScraper(config) as scraper:
            listings.extend(scraper.scrape_municipality(municipality))

    if portal in ("idealista", "both"):
        with IdealistaScraper(config) as scraper:
            listings.extend(scraper.scrape_municipality(municipality))

    result = {
        "total_found": len(listings),
        "municipality": municipality,
        "listings": [
            {
                "id": l.property_id,
                "source": l.source,
                "title": l.title,
                "price": l.price,
                "surface_area": l.surface_area,
                "rooms": l.rooms,
                "price_per_sqm": l.price_per_sqm,
                "url": l.url,
            }
            for l in listings[:20]  # Return top 20
        ],
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]


async def _analyze_deal(args: dict, config: dict, market_data: dict) -> list[TextContent]:
    """Analyze a specific deal."""
    listing_id = args["listing_id"]
    include_splitting = args.get("include_splitting", True)

    # Find listing in stored data
    listings = load_listings()
    listing = None
    for l in listings:
        if l.property_id == listing_id:
            listing = l
            break

    if not listing:
        return [TextContent(type="text", text=f"Listing {listing_id} not found in stored data.")]

    deal = score_deal(listing, config, market_data, include_splitting=include_splitting)
    result = deal.to_dict()
    result["listing"] = {
        "id": listing.property_id,
        "title": listing.title,
        "price": listing.price,
        "surface_area": listing.surface_area,
        "url": listing.url,
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]


async def _analyze_floor_plan(args: dict) -> list[TextContent]:
    """Analyze a floor plan."""
    from analysis.floor_plan_analyzer import analyze_floor_plan_with_ai

    image_url = args["image_url"]
    surface_area = args.get("surface_area", 0)
    use_ai = args.get("use_ai", False)

    if use_ai:
        result = analyze_floor_plan_with_ai(image_url, surface_area)
    else:
        result = {"message": "Set use_ai=true for AI-powered floor plan analysis."}

    return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]


async def _calculate_renovation(args: dict, market_data: dict) -> list[TextContent]:
    """Calculate renovation costs."""
    plan = create_renovation_plan(
        surface_area=args["surface_area"],
        level=args["level"],
        bathrooms_new=args.get("bathrooms_new", 0),
        kitchen_new=args.get("kitchen_new", False),
        splitting=args.get("splitting", False),
        n_split_units=args.get("n_split_units", 2),
        market_data=market_data,
    )
    return [TextContent(type="text", text=json.dumps(plan.to_dict(), indent=2, ensure_ascii=False))]


async def _get_market_data(args: dict, market_data: dict) -> list[TextContent]:
    """Get market data for a municipality."""
    from scrapers.utils import normalize_municipality
    from analysis.valuation import MUNICIPALITY_KEY_MAP

    municipality = args["municipality"]
    it_name, de_name = normalize_municipality(municipality)
    muni_key = MUNICIPALITY_KEY_MAP.get(it_name, it_name)

    prices = market_data.get("market_prices_per_sqm", {})
    muni_data = prices.get(muni_key, {})

    province_data = market_data.get("provinz_bozen", {})
    renovation_costs = market_data.get("renovation_costs_per_sqm", {})
    purchase_costs = market_data.get("purchase_costs", {})

    result = {
        "municipality": it_name,
        "municipality_de": de_name,
        "market_data_key": muni_key,
        "price_data": muni_data,
        "province_averages": province_data,
        "renovation_costs_per_sqm": {
            k: v for k, v in renovation_costs.items() if k != "specific"
        },
        "purchase_costs": purchase_costs,
    }

    return [TextContent(type="text", text=json.dumps(result, indent=2, ensure_ascii=False))]


async def _compare_listings(args: dict, config: dict, market_data: dict) -> list[TextContent]:
    """Compare multiple listings."""
    listing_ids = args["listing_ids"]
    all_listings = load_listings()

    selected = [l for l in all_listings if l.property_id in listing_ids]

    if not selected:
        return [TextContent(type="text", text="No matching listings found.")]

    comparisons = []
    for listing in selected:
        deal = score_deal(listing, config, market_data)
        comparisons.append({
            "id": listing.property_id,
            "title": listing.title,
            "price": listing.price,
            "surface_area": listing.surface_area,
            "price_per_sqm": listing.price_per_sqm,
            "deal_score": deal.total_score,
            "deal_grade": deal.deal_grade,
            "roi_pct": deal.valuation.roi_pct if deal.valuation else 0,
            "discount_pct": deal.valuation.discount_to_market_pct if deal.valuation else 0,
            "url": listing.url,
        })

    comparisons.sort(key=lambda x: x["deal_score"], reverse=True)

    return [TextContent(type="text", text=json.dumps(comparisons, indent=2, ensure_ascii=False))]


async def _generate_report(args: dict, config: dict, market_data: dict) -> list[TextContent]:
    """Generate a deal report."""
    from mcp_server.tools.report_generator import generate_deal_report

    listing_id = args["listing_id"]
    fmt = args.get("format", "markdown")

    listings = load_listings()
    listing = None
    for l in listings:
        if l.property_id == listing_id:
            listing = l
            break

    if not listing:
        return [TextContent(type="text", text=f"Listing {listing_id} not found.")]

    deal = score_deal(listing, config, market_data)
    report = generate_deal_report(listing, deal, format=fmt)

    return [TextContent(type="text", text=report)]


@app.list_resources()
async def list_resources() -> list[Resource]:
    """List available resources."""
    return [
        Resource(
            uri="market://bozen",
            name="Bozen/Bolzano Market Data",
            description="Current market prices for Bozen/Bolzano",
            mimeType="application/json",
        ),
        Resource(
            uri="market://meran",
            name="Meran/Merano Market Data",
            description="Current market prices for Meran/Merano",
            mimeType="application/json",
        ),
        Resource(
            uri="market://province",
            name="Province Overview",
            description="Province-wide market overview and averages",
            mimeType="application/json",
        ),
    ]


async def main():
    """Run the MCP server."""
    logging.basicConfig(level=logging.INFO)
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
