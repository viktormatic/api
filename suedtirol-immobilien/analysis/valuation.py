"""
Property valuation logic for Südtirol real estate.

Calculates market price comparisons, condition assessments,
location scoring, and after-repair-value projections.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from scrapers.utils import PropertyListing, load_config, load_market_data

logger = logging.getLogger(__name__)


@dataclass
class ValuationResult:
    """Result of property valuation analysis."""

    # Market comparison
    market_ref_low: float = 0.0
    market_ref_high: float = 0.0
    market_ref_mid: float = 0.0
    current_price_per_sqm: float = 0.0
    discount_to_market_pct: float = 0.0

    # After-repair-value
    arv_per_sqm: float = 0.0
    arv_total: float = 0.0
    renovation_cost_estimate: float = 0.0
    renovation_level: str = ""  # leicht, mittel, schwer

    # Location score
    location_score: float = 0.0  # 1-10
    location_tier: str = ""  # tier_1_urban, tier_2_suburban, tier_3_value

    # Investment metrics
    total_investment: float = 0.0
    purchase_costs: float = 0.0
    selling_costs: float = 0.0
    net_profit: float = 0.0
    roi_pct: float = 0.0

    # Splitting potential
    splittable: bool = False
    splitting_value_add: float = 0.0

    # Days on market
    days_on_market: int = 0
    negotiation_potential: str = ""  # low, medium, high

    # Summary
    condition_assessed: str = ""
    municipality_avg_price: float = 0.0
    warnings: list = field(default_factory=list)


# Municipality to market_data key mapping
MUNICIPALITY_KEY_MAP = {
    "bolzano": "bozen",
    "merano": "meran",
    "bressanone": "brixen",
    "laives": "leifers",
    "appiano-sulla-strada-del-vino": "eppan",
    "appiano": "eppan",
    "lana": "lana",
    "brunico": "bruneck",
    "egna": "neumarkt",
    "silandro": "schlanders",
    "vipiteno": "sterzing",
    "caldaro-sulla-strada-del-vino": "kaltern",
    "caldaro": "kaltern",
    "renon": "ritten",
    "tirolo": "dorf_tirol",
    "fortezza": "franzensfeste",
}

# Condition to market data key mapping
CONDITION_TO_KEY = {
    "da_ristrutturare": "renovierungsbeduerftig",
    "buono": "gut_renoviert",
    "ristrutturato": "gut_renoviert",
    "nuovo": "neubau",
}

# Location scores by tier
TIER_LOCATION_SCORES = {
    "tier_1_urban": 8.5,
    "tier_2_suburban": 7.0,
    "tier_3_value": 5.5,
}


def get_municipality_tier(municipality: str, config: dict) -> str:
    """Determine which tier a municipality belongs to."""
    municipalities = config.get("search_config", {}).get("target_municipalities", {})
    for tier_name, tier_list in municipalities.items():
        for muni in tier_list:
            name = muni if isinstance(muni, str) else muni.get("name", "")
            if name == municipality:
                return tier_name
    return "tier_3_value"  # Default


def get_market_reference(
    municipality: str,
    zone: str,
    condition: str,
    market_data: dict,
) -> tuple[float, float]:
    """
    Get market reference price range (€/m²) for a property.
    Returns (low, high) price per sqm.
    """
    prices = market_data.get("market_prices_per_sqm", {})
    muni_key = MUNICIPALITY_KEY_MAP.get(municipality, municipality)
    muni_data = prices.get(muni_key, {})

    if not muni_data:
        # Use province average as fallback
        province_avg = market_data.get("provinz_bozen", {}).get("kauf_durchschnitt_sqm", 4777)
        return province_avg * 0.7, province_avg * 1.3

    condition_key = CONDITION_TO_KEY.get(condition, "gut_renoviert")

    # Try zone-specific data first
    if zone:
        zone_lower = zone.lower().replace(" ", "_").replace("-", "_")
        for zone_key, zone_data in muni_data.items():
            if isinstance(zone_data, dict) and zone_lower in zone_key:
                if condition_key in zone_data:
                    return tuple(zone_data[condition_key])

    # Try any zone with condition data
    for zone_key, zone_data in muni_data.items():
        if isinstance(zone_data, dict) and condition_key in zone_data:
            return tuple(zone_data[condition_key])

    # Use durchschnitt (average) with condition adjustment
    avg = muni_data.get("durchschnitt", 0)
    if avg:
        adjustments = {
            "renovierungsbeduerftig": (0.65, 0.85),
            "gut_renoviert": (0.90, 1.10),
            "neubau": (1.10, 1.40),
        }
        adj = adjustments.get(condition_key, (0.85, 1.05))
        return avg * adj[0], avg * adj[1]

    # Use range if available
    range_data = muni_data.get("range")
    if range_data:
        return tuple(range_data)

    # Province fallback
    province_avg = market_data.get("provinz_bozen", {}).get("kauf_durchschnitt_sqm", 4777)
    return province_avg * 0.7, province_avg * 1.3


def estimate_renovation_level(listing: PropertyListing) -> str:
    """Estimate renovation level needed based on listing data."""
    if listing.condition in ("nuovo", "ristrutturato"):
        return "leicht"

    # Check energy class
    low_energy = listing.energy_class in ("F", "G", "")

    # Check description keywords
    desc_lower = (listing.description + " " + listing.title).lower()
    heavy_keywords = [
        "completamente da ristrutturare",
        "komplett zu renovieren",
        "grezzo",
        "da rifare",
        "rudere",
        "in pessimo stato",
    ]
    medium_keywords = [
        "da ristrutturare",
        "zu renovieren",
        "da rinnovare",
        "parzialmente",
        "teilweise",
    ]

    if any(kw in desc_lower for kw in heavy_keywords):
        return "schwer"
    if any(kw in desc_lower for kw in medium_keywords):
        return "mittel"
    if listing.condition == "da_ristrutturare":
        return "mittel" if not low_energy else "schwer"
    if listing.condition == "buono" and low_energy:
        return "mittel"

    return "leicht"


def calculate_renovation_cost(
    surface_area: float,
    renovation_level: str,
    market_data: dict,
    extra_items: Optional[dict] = None,
) -> float:
    """
    Calculate estimated renovation costs.

    Args:
        surface_area: Property surface area in m².
        renovation_level: leicht, mittel, schwer, or luxus.
        market_data: Market data configuration.
        extra_items: Additional specific items (e.g., {"badezimmer_neu": 1}).
    """
    costs = market_data.get("renovation_costs_per_sqm", {})
    level_range = costs.get(renovation_level, [700, 1200])
    # Use midpoint of range
    cost_per_sqm = sum(level_range) / 2
    base_cost = surface_area * cost_per_sqm

    # Add specific items
    extra_cost = 0
    if extra_items:
        specific = costs.get("specific", {})
        for item, count in extra_items.items():
            item_range = specific.get(item, [0, 0])
            item_cost = sum(item_range) / 2
            extra_cost += item_cost * count

    return base_cost + extra_cost


def calculate_purchase_costs(
    purchase_price: float,
    is_prima_casa: bool,
    market_data: dict,
) -> float:
    """Calculate total purchase costs (taxes, notary, broker)."""
    costs = market_data.get("purchase_costs", {})

    # Registration tax (on cadastral value, typically ~60-70% of market price for apartments)
    cadastral_multiplier = 0.65
    cadastral_value = purchase_price * cadastral_multiplier

    if is_prima_casa:
        registration_tax = cadastral_value * costs.get("grunderwerbsteuer_erstwohnung", 0.02)
        # Minimum 1000€
        registration_tax = max(registration_tax, 1000)
    else:
        registration_tax = cadastral_value * costs.get("grunderwerbsteuer_zweitwohnung", 0.09)

    # Notary fees
    notar_range = costs.get("notar", [2000, 4000])
    notar = sum(notar_range) / 2

    # Broker fee (3% + 22% VAT)
    makler_pct = costs.get("makler_pct", 0.03)
    makler_mwst = costs.get("makler_mwst", 0.22)
    broker_fee = purchase_price * makler_pct * (1 + makler_mwst)

    # Fixed costs
    kataster = costs.get("kataster_umschreibung", 300)
    hypothek = costs.get("hypothekensteuer", 50)
    kataster_steuer = costs.get("katastersteuer", 50)

    total = registration_tax + notar + broker_fee + kataster + hypothek + kataster_steuer
    return round(total, 2)


def calculate_selling_costs(
    selling_price: float,
    market_data: dict,
    holding_years: float = 1.0,
    profit: float = 0.0,
) -> float:
    """Calculate total selling costs."""
    costs = market_data.get("selling_costs", {})

    # Broker fee
    makler_pct = costs.get("makler_pct", 0.03)
    makler_mwst = costs.get("makler_mwst", 0.22)
    broker_fee = selling_price * makler_pct * (1 + makler_mwst)

    # Energy certificate
    ape_range = costs.get("energieausweis", [200, 400])
    ape = sum(ape_range) / 2

    # Capital gains tax (only if sold within 5 years and there's profit)
    capital_gains_tax = 0
    if holding_years < 5 and profit > 0:
        flat_rate = costs.get("plusvalenza_flat_rate", 0.26)
        capital_gains_tax = profit * flat_rate

    return round(broker_fee + ape + capital_gains_tax, 2)


def valuate_property(
    listing: PropertyListing,
    config: Optional[dict] = None,
    market_data: Optional[dict] = None,
    is_prima_casa: bool = False,
) -> ValuationResult:
    """
    Perform full valuation analysis on a property listing.

    Args:
        listing: The property listing to valuate.
        config: Settings configuration.
        market_data: Market data configuration.
        is_prima_casa: Whether this qualifies as primary residence (lower taxes).

    Returns:
        ValuationResult with all calculated metrics.
    """
    if config is None:
        config = load_config()
    if market_data is None:
        market_data = load_market_data()

    result = ValuationResult()
    warnings = []

    # 1. MARKET PRICE COMPARISON
    if listing.surface_area <= 0:
        warnings.append("Surface area unknown - valuation may be inaccurate")
        result.warnings = warnings
        return result

    result.current_price_per_sqm = round(listing.price / listing.surface_area, 2)

    ref_low, ref_high = get_market_reference(
        listing.municipality, listing.zone, listing.condition, market_data
    )
    result.market_ref_low = ref_low
    result.market_ref_high = ref_high
    result.market_ref_mid = (ref_low + ref_high) / 2

    # Discount to market
    if result.market_ref_mid > 0:
        result.discount_to_market_pct = round(
            (result.market_ref_mid - result.current_price_per_sqm)
            / result.market_ref_mid
            * 100,
            1,
        )

    # Municipality average
    muni_key = MUNICIPALITY_KEY_MAP.get(listing.municipality, listing.municipality)
    muni_data = market_data.get("market_prices_per_sqm", {}).get(muni_key, {})
    result.municipality_avg_price = muni_data.get(
        "durchschnitt",
        market_data.get("provinz_bozen", {}).get("kauf_durchschnitt_sqm", 4777),
    )

    # 2. CONDITION & RENOVATION ASSESSMENT
    result.renovation_level = estimate_renovation_level(listing)
    result.condition_assessed = listing.condition_de or listing.condition

    result.renovation_cost_estimate = calculate_renovation_cost(
        listing.surface_area, result.renovation_level, market_data
    )

    # 3. LOCATION SCORING
    tier = get_municipality_tier(listing.municipality, config)
    result.location_tier = tier
    base_score = TIER_LOCATION_SCORES.get(tier, 5.0)

    # Adjustments
    if listing.elevator:
        base_score += 0.3
    if listing.balcony or listing.terrace:
        base_score += 0.2
    if listing.garden:
        base_score += 0.3
    if listing.garage:
        base_score += 0.2
    if listing.floor and listing.floor > 3 and not listing.elevator:
        base_score -= 0.5

    result.location_score = round(min(10.0, max(1.0, base_score)), 1)

    # 4. AFTER-REPAIR-VALUE (ARV)
    # ARV is based on "gut_renoviert" price for the area
    arv_ref_low, arv_ref_high = get_market_reference(
        listing.municipality, listing.zone, "ristrutturato", market_data
    )
    result.arv_per_sqm = (arv_ref_low + arv_ref_high) / 2
    result.arv_total = round(result.arv_per_sqm * listing.surface_area, 2)

    # 5. SPLITTING POTENTIAL
    thresholds = config.get("search_config", {}).get("thresholds", {})
    min_split_area = thresholds.get("min_splitting_area", 80)

    if listing.surface_area >= min_split_area:
        result.splittable = True
        # Estimate value add from splitting
        # Smaller units typically command 5-15% higher €/m²
        premium_pct = 0.08  # Conservative 8% premium for smaller units
        n_units = 2 if listing.surface_area < 150 else 3
        split_area = listing.surface_area / n_units

        if split_area >= 28:  # Italian minimum
            split_value = n_units * split_area * result.arv_per_sqm * (1 + premium_pct)
            # Subtract splitting costs
            split_costs = market_data.get("renovation_costs_per_sqm", {}).get(
                "specific", {}
            ).get("baugenehmigung_teilung", [3000, 8000])
            split_cost_avg = sum(split_costs) / 2

            # Additional per-unit costs (bathroom, kitchen, installations)
            extra_units = n_units - 1
            per_unit_cost = 20000  # Average for new bathroom + installations + walls
            total_split_cost = split_cost_avg + extra_units * per_unit_cost

            result.splitting_value_add = round(
                split_value - result.arv_total - total_split_cost, 2
            )
        else:
            result.splittable = False
            warnings.append(
                f"Split units would be {split_area:.0f}m² - below 28m² minimum"
            )

    # 6. INVESTMENT CALCULATION
    result.purchase_costs = calculate_purchase_costs(
        listing.price, is_prima_casa, market_data
    )

    result.total_investment = (
        listing.price + result.purchase_costs + result.renovation_cost_estimate
    )

    # Selling costs based on ARV
    gross_profit = result.arv_total - result.total_investment
    result.selling_costs = calculate_selling_costs(
        result.arv_total, market_data, holding_years=1.0, profit=max(0, gross_profit)
    )

    result.net_profit = round(
        result.arv_total - result.total_investment - result.selling_costs, 2
    )

    if result.total_investment > 0:
        result.roi_pct = round(
            result.net_profit / result.total_investment * 100, 1
        )

    # 7. NEGOTIATION POTENTIAL
    if result.discount_to_market_pct < 0:
        result.negotiation_potential = "low"
        warnings.append("Property is above market price")
    elif result.discount_to_market_pct < 10:
        result.negotiation_potential = "low"
    elif result.discount_to_market_pct < 20:
        result.negotiation_potential = "medium"
    else:
        result.negotiation_potential = "high"

    result.warnings = warnings
    return result


def batch_valuate(
    listings: list[PropertyListing],
    config: Optional[dict] = None,
    market_data: Optional[dict] = None,
) -> list[tuple[PropertyListing, ValuationResult]]:
    """
    Valuate multiple listings.

    Returns list of (listing, valuation) tuples sorted by ROI descending.
    """
    if config is None:
        config = load_config()
    if market_data is None:
        market_data = load_market_data()

    results = []
    for listing in listings:
        try:
            valuation = valuate_property(listing, config, market_data)
            results.append((listing, valuation))
        except Exception as e:
            logger.warning(f"Valuation failed for {listing.property_id}: {e}")

    # Sort by ROI descending
    results.sort(key=lambda x: x[1].roi_pct, reverse=True)
    return results
