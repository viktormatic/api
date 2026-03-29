"""
Deal scoring and ranking system for Südtirol real estate investments.

Classifies properties into deal categories:
  A-DEAL (>=80): Immediate opportunity
  B-DEAL (60-79): Worth investigating
  C-DEAL (40-59): Only with negotiation room
  NO DEAL (<40): Do not pursue
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from scrapers.utils import PropertyListing, load_config, load_market_data
from .valuation import ValuationResult, valuate_property
from .floor_plan_analyzer import SplittingAnalysis, analyze_splitting_potential
from .renovation_calculator import RenovationPlan, estimate_renovation_for_listing

logger = logging.getLogger(__name__)


@dataclass
class DealScore:
    """Complete deal scoring result."""

    # Overall
    total_score: int = 0
    deal_grade: str = ""  # A, B, C, or NO_DEAL
    deal_label: str = ""
    deal_emoji: str = ""

    # Component scores (each 0-100, then weighted)
    price_discount_score: int = 0       # Weight: 30%
    location_score: int = 0             # Weight: 25%
    roi_score: int = 0                  # Weight: 25%
    splitting_score: int = 0            # Weight: 10%
    liquidity_score: int = 0            # Weight: 10%

    # Sub-analyses
    valuation: Optional[ValuationResult] = None
    splitting: Optional[SplittingAnalysis] = None
    renovation: Optional[RenovationPlan] = None

    # Recommendation
    recommendation: str = ""
    action_items: list = field(default_factory=list)
    risks: list = field(default_factory=list)

    def to_dict(self) -> dict:
        result = {
            "total_score": self.total_score,
            "deal_grade": self.deal_grade,
            "deal_label": self.deal_label,
            "components": {
                "price_discount": {"score": self.price_discount_score, "weight": 0.30},
                "location": {"score": self.location_score, "weight": 0.25},
                "roi": {"score": self.roi_score, "weight": 0.25},
                "splitting": {"score": self.splitting_score, "weight": 0.10},
                "liquidity": {"score": self.liquidity_score, "weight": 0.10},
            },
            "recommendation": self.recommendation,
            "action_items": self.action_items,
            "risks": self.risks,
        }
        if self.valuation:
            result["valuation"] = {
                "discount_to_market_pct": self.valuation.discount_to_market_pct,
                "roi_pct": self.valuation.roi_pct,
                "net_profit": self.valuation.net_profit,
                "arv_total": self.valuation.arv_total,
                "total_investment": self.valuation.total_investment,
                "location_score": self.valuation.location_score,
                "renovation_level": self.valuation.renovation_level,
            }
        if self.splitting:
            result["splitting_analysis"] = self.splitting.to_dict()
        if self.renovation:
            result["renovation_plan"] = self.renovation.to_dict()
        return result


# Scoring weights
WEIGHTS = {
    "price_discount": 0.30,
    "location": 0.25,
    "roi": 0.25,
    "splitting": 0.10,
    "liquidity": 0.10,
}

# Grade thresholds
GRADE_THRESHOLDS = {
    "A": 80,
    "B": 60,
    "C": 40,
}


def score_price_discount(discount_pct: float) -> int:
    """Score based on discount to market price (0-100)."""
    if discount_pct >= 30:
        return 100
    elif discount_pct >= 25:
        return 90
    elif discount_pct >= 20:
        return 80
    elif discount_pct >= 15:
        return 65
    elif discount_pct >= 10:
        return 50
    elif discount_pct >= 5:
        return 35
    elif discount_pct >= 0:
        return 20
    else:
        # Above market price
        return max(0, int(20 + discount_pct * 2))


def score_location(location_score: float, tier: str) -> int:
    """Score based on location quality (0-100)."""
    # Location score is 1-10, convert to 0-100
    base = int(location_score * 10)

    # Tier bonus for liquidity
    tier_bonus = {
        "tier_1_urban": 10,
        "tier_2_suburban": 5,
        "tier_3_value": 0,
    }
    return min(100, base + tier_bonus.get(tier, 0))


def score_roi(roi_pct: float) -> int:
    """Score based on projected ROI (0-100)."""
    if roi_pct >= 40:
        return 100
    elif roi_pct >= 30:
        return 90
    elif roi_pct >= 25:
        return 80
    elif roi_pct >= 20:
        return 70
    elif roi_pct >= 15:
        return 55
    elif roi_pct >= 10:
        return 40
    elif roi_pct >= 5:
        return 25
    elif roi_pct >= 0:
        return 10
    else:
        return 0


def score_splitting(splitting_analysis: Optional[SplittingAnalysis]) -> int:
    """Score based on splitting potential (0-100)."""
    if splitting_analysis is None:
        return 0
    return splitting_analysis.splitting_score


def score_liquidity(listing: PropertyListing, valuation: ValuationResult) -> int:
    """
    Score based on expected ease and speed of resale (0-100).
    Factors: municipality tier, property size, condition after renovation.
    """
    score = 50  # Base

    # Tier 1 cities sell faster
    if valuation.location_tier == "tier_1_urban":
        score += 25
    elif valuation.location_tier == "tier_2_suburban":
        score += 15
    elif valuation.location_tier == "tier_3_value":
        score += 5

    # Optimal size for resale (60-100m² = sweet spot)
    if 60 <= listing.surface_area <= 100:
        score += 15
    elif 40 <= listing.surface_area <= 120:
        score += 10
    else:
        score += 0

    # Desirable features
    if listing.elevator:
        score += 5
    if listing.balcony or listing.terrace:
        score += 3
    if listing.garage:
        score += 2

    # Days on market (long listing = lower liquidity)
    if valuation.days_on_market > 180:
        score -= 10
    elif valuation.days_on_market > 90:
        score -= 5

    return min(100, max(0, score))


def classify_deal(score: int) -> tuple[str, str, str]:
    """
    Classify deal based on total score.
    Returns (grade, label, emoji).
    """
    if score >= GRADE_THRESHOLDS["A"]:
        return "A", "A-DEAL: Sofort zuschlagen", "🟢"
    elif score >= GRADE_THRESHOLDS["B"]:
        return "B", "B-DEAL: Genauer prüfen", "🟡"
    elif score >= GRADE_THRESHOLDS["C"]:
        return "C", "C-DEAL: Nur bei Verhandlungsspielraum", "🟠"
    else:
        return "NO_DEAL", "Kein Deal: Nicht weiterverfolgen", "🔴"


def generate_recommendation(
    listing: PropertyListing,
    deal_score: DealScore,
) -> tuple[str, list[str], list[str]]:
    """
    Generate human-readable recommendation, action items, and risks.
    """
    valuation = deal_score.valuation
    recommendation = ""
    actions = []
    risks = []

    if deal_score.deal_grade == "A":
        recommendation = (
            f"Starke Kaufempfehlung. Das Objekt liegt {valuation.discount_to_market_pct:.0f}% "
            f"unter dem Marktpreis mit einem prognostizierten ROI von {valuation.roi_pct:.0f}%. "
            f"Sofortige Besichtigung und Verhandlung empfohlen."
        )
        actions = [
            "Sofort Besichtigungstermin vereinbaren",
            f"Finanzierung für ca. €{valuation.total_investment:,.0f} vorbereiten",
            "Bautechniker für Zustandsbewertung beauftragen",
            "Katasterwert beim Grundbuchamt prüfen",
        ]
    elif deal_score.deal_grade == "B":
        recommendation = (
            f"Interessantes Objekt mit Potenzial. Discount: {valuation.discount_to_market_pct:.0f}%, "
            f"ROI: {valuation.roi_pct:.0f}%. Detailprüfung und Preisverhandlung empfohlen."
        )
        actions = [
            "Besichtigung terminieren",
            "Detaillierte Renovierungskosten-Schätzung erstellen",
            "Vergleichsobjekte in der Umgebung analysieren",
            f"Preisverhandlung anstreben (Zielpreis: €{listing.price * 0.92:,.0f})",
        ]
    elif deal_score.deal_grade == "C":
        recommendation = (
            f"Nur interessant bei deutlicher Preissenkung. "
            f"Aktueller Discount: {valuation.discount_to_market_pct:.0f}%, ROI: {valuation.roi_pct:.0f}%. "
            f"Beobachten und bei Preisreduktion erneut bewerten."
        )
        actions = [
            "Auf Preisbeobachtungsliste setzen",
            "Bei Preissenkung > 10% erneut analysieren",
            f"Verhandlungsziel: €{listing.price * 0.85:,.0f}",
        ]
    else:
        recommendation = (
            f"Kein empfehlenswertes Investment. "
            f"Discount: {valuation.discount_to_market_pct:.0f}%, ROI: {valuation.roi_pct:.0f}%. "
            f"Nicht weiterverfolgen."
        )

    # Common risks
    if valuation.renovation_level == "schwer":
        risks.append("Hoher Renovierungsaufwand - Kostenüberschreitungen möglich (+20-30%)")
    if valuation.discount_to_market_pct < 5:
        risks.append("Geringer Discount - wenig Puffer bei Marktschwankungen")
    if listing.energy_class in ("F", "G"):
        risks.append("Schlechte Energieklasse - zukünftige Auflagen möglich")
    if not listing.elevator and listing.floor and listing.floor > 2:
        risks.append("Kein Aufzug bei hohem Stockwerk - eingeschränkter Käuferkreis")
    if valuation.location_tier == "tier_3_value":
        risks.append("Periphere Lage - längere Vermarktungszeit zu erwarten")

    if deal_score.splitting and deal_score.splitting.is_splittable:
        risks.append("Wohnungsteilung erfordert Baugenehmigung - Verzögerungen möglich")
        if deal_score.splitting.net_value_add > 0:
            actions.append(
                f"Teilungspotenzial prüfen: Mehrwert ca. €{deal_score.splitting.net_value_add:,.0f}"
            )

    return recommendation, actions, risks


def score_deal(
    listing: PropertyListing,
    config: Optional[dict] = None,
    market_data: Optional[dict] = None,
    include_splitting: bool = True,
    use_ai_floor_plan: bool = False,
) -> DealScore:
    """
    Perform complete deal scoring for a property listing.

    Args:
        listing: Property listing to score.
        config: Settings configuration.
        market_data: Market data configuration.
        include_splitting: Whether to include splitting analysis.
        use_ai_floor_plan: Whether to use AI for floor plan analysis.

    Returns:
        DealScore with all components and recommendation.
    """
    if config is None:
        config = load_config()
    if market_data is None:
        market_data = load_market_data()

    deal = DealScore()

    # 1. Valuation
    valuation = valuate_property(listing, config, market_data)
    deal.valuation = valuation

    # 2. Renovation plan
    renovation = estimate_renovation_for_listing(listing, market_data)
    deal.renovation = renovation

    # 3. Splitting analysis (if applicable)
    splitting = None
    if include_splitting and listing.surface_area >= 80:
        splitting = analyze_splitting_potential(
            listing, config, market_data, use_ai=use_ai_floor_plan
        )
        deal.splitting = splitting

    # 4. Component scores
    deal.price_discount_score = score_price_discount(valuation.discount_to_market_pct)
    deal.location_score = score_location(valuation.location_score, valuation.location_tier)
    deal.roi_score = score_roi(valuation.roi_pct)
    deal.splitting_score = score_splitting(splitting)
    deal.liquidity_score = score_liquidity(listing, valuation)

    # 5. Weighted total score
    deal.total_score = int(
        deal.price_discount_score * WEIGHTS["price_discount"]
        + deal.location_score * WEIGHTS["location"]
        + deal.roi_score * WEIGHTS["roi"]
        + deal.splitting_score * WEIGHTS["splitting"]
        + deal.liquidity_score * WEIGHTS["liquidity"]
    )

    # 6. Classification
    deal.deal_grade, deal.deal_label, deal.deal_emoji = classify_deal(deal.total_score)

    # 7. Recommendation
    deal.recommendation, deal.action_items, deal.risks = generate_recommendation(
        listing, deal
    )

    return deal


def rank_deals(
    listings: list[PropertyListing],
    config: Optional[dict] = None,
    market_data: Optional[dict] = None,
    top_n: int = 10,
) -> list[tuple[PropertyListing, DealScore]]:
    """
    Score and rank multiple listings.

    Returns top N deals sorted by score descending.
    """
    if config is None:
        config = load_config()
    if market_data is None:
        market_data = load_market_data()

    scored = []
    for listing in listings:
        try:
            deal = score_deal(listing, config, market_data)
            scored.append((listing, deal))
        except Exception as e:
            logger.warning(f"Scoring failed for {listing.property_id}: {e}")

    # Sort by total score descending
    scored.sort(key=lambda x: x[1].total_score, reverse=True)

    if top_n:
        return scored[:top_n]
    return scored
