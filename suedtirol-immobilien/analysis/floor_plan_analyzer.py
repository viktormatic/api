"""
Floor plan analysis and apartment splitting potential evaluator.

Pipeline:
1. Extract floor plan images from listing photos
2. Pre-process with OpenCV (contrast, binarize, detect walls)
3. Use AI vision model (Claude/GPT-4V) for detailed analysis
4. Score splitting potential
5. Calculate economic viability of splitting
"""

import base64
import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import httpx

from scrapers.utils import PropertyListing, load_config, load_market_data

logger = logging.getLogger(__name__)


@dataclass
class SplittingAnalysis:
    """Result of apartment splitting analysis."""

    # Basic feasibility
    is_splittable: bool = False
    confidence: float = 0.0  # 0-1

    # Proposed split
    n_units: int = 0
    proposed_units: list = field(default_factory=list)  # List of unit descriptions
    total_area: float = 0.0
    unit_areas: list = field(default_factory=list)  # Area per unit

    # Requirements check
    min_area_met: bool = False
    separate_bathrooms: bool = False
    natural_light_each_unit: bool = False
    separate_access_possible: bool = False
    ventilation_ok: bool = False
    min_height_ok: bool = True  # Assume ok unless noted

    # Structural
    load_bearing_walls_identified: bool = False
    plumbing_positions: str = ""
    window_count: int = 0
    window_distribution: str = ""

    # Economic
    value_before_split: float = 0.0
    value_after_split: float = 0.0
    splitting_cost: float = 0.0
    net_value_add: float = 0.0

    # AI analysis raw response
    ai_analysis_raw: str = ""

    # Splitting score (0-100)
    splitting_score: int = 0

    def to_dict(self) -> dict:
        return {
            "is_splittable": self.is_splittable,
            "confidence": self.confidence,
            "n_units": self.n_units,
            "proposed_units": self.proposed_units,
            "unit_areas": self.unit_areas,
            "checks": {
                "min_area_met": self.min_area_met,
                "separate_bathrooms": self.separate_bathrooms,
                "natural_light": self.natural_light_each_unit,
                "separate_access": self.separate_access_possible,
                "ventilation": self.ventilation_ok,
                "min_height": self.min_height_ok,
            },
            "structural": {
                "load_bearing_walls": self.load_bearing_walls_identified,
                "plumbing": self.plumbing_positions,
                "windows": self.window_count,
                "window_distribution": self.window_distribution,
            },
            "economics": {
                "value_before": self.value_before_split,
                "value_after": self.value_after_split,
                "splitting_cost": self.splitting_cost,
                "net_value_add": self.net_value_add,
            },
            "splitting_score": self.splitting_score,
        }


# Prompt for AI vision analysis
FLOOR_PLAN_ANALYSIS_PROMPT = """Analyze this apartment floor plan as a real estate investment expert specializing in South Tyrol (Italy).

Determine:
a) Estimated total area and individual room areas (in m²)
b) Room layout: number of rooms, bathrooms, kitchen, hallway
c) Load-bearing vs. non-load-bearing walls (if identifiable)
d) Position of wet rooms (bathroom/kitchen) and utility lines
e) Window count and positions per room
f) Access points and escape routes

SPLITTING ANALYSIS:
g) Can this apartment be split into 2+ smaller units?
h) Where could a partition wall be placed?
i) Can each unit have its own bathroom?
j) Does each unit have at least 1 window per living room?
k) Is separate access per unit possible (or achievable)?
l) Estimated area of each resulting unit

REGULATORY ASSESSMENT (Italy/South Tyrol):
m) Minimum apartment size: 28m² for 1 person, 38m² for 2 persons
n) Minimum height: 2.70m (living rooms), 2.40m (auxiliary rooms)
o) Every living room needs natural light (window)
p) Ventilation capability in every room

Respond in JSON format:
{
  "total_area_estimate": <float>,
  "rooms": [{"name": "<str>", "area_estimate": <float>, "windows": <int>, "type": "<living/wet/hall/storage>"}],
  "splittable": <bool>,
  "confidence": <float 0-1>,
  "proposed_split": {
    "n_units": <int>,
    "units": [
      {"rooms": <int>, "area": <float>, "has_bathroom": <bool>, "has_kitchen": <bool>, "windows": <int>, "separate_entrance": <bool>}
    ],
    "partition_wall_description": "<str>",
    "plumbing_work_needed": "<str>"
  },
  "regulatory_compliance": {
    "min_area_met": <bool>,
    "natural_light_ok": <bool>,
    "ventilation_ok": <bool>,
    "separate_access_possible": <bool>
  },
  "structural_notes": "<str>",
  "recommendation": "<str>"
}"""


def detect_floor_plan_images(listing: PropertyListing) -> list[str]:
    """
    Identify which images in a listing are floor plans.
    Uses URL patterns and keywords.
    """
    floor_plans = []

    # Check explicit floor plan images
    if listing.floor_plan_images:
        return listing.floor_plan_images

    # Heuristic detection from all images
    floor_plan_keywords = [
        "planimetria", "piantina", "grundriss", "floor_plan",
        "floorplan", "plan_", "pianta",
    ]

    for img_url in listing.images:
        url_lower = img_url.lower()
        if any(kw in url_lower for kw in floor_plan_keywords):
            floor_plans.append(img_url)

    return floor_plans


def analyze_floor_plan_with_ai(
    image_url: str,
    surface_area: float = 0.0,
    anthropic_key: Optional[str] = None,
) -> dict:
    """
    Send floor plan image to Claude Vision API for analysis.

    Args:
        image_url: URL of the floor plan image.
        surface_area: Known surface area for calibration.
        anthropic_key: Anthropic API key.

    Returns:
        Parsed JSON response from the AI model.
    """
    if anthropic_key is None:
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")

    if not anthropic_key:
        logger.warning("ANTHROPIC_API_KEY not set. Cannot perform AI floor plan analysis.")
        return {}

    try:
        # Fetch the image
        img_response = httpx.get(image_url, timeout=30.0)
        img_response.raise_for_status()
        img_data = base64.b64encode(img_response.content).decode("utf-8")

        # Determine media type
        content_type = img_response.headers.get("content-type", "image/jpeg")
        if "png" in content_type:
            media_type = "image/png"
        elif "webp" in content_type:
            media_type = "image/webp"
        else:
            media_type = "image/jpeg"

    except Exception as e:
        logger.error(f"Failed to fetch floor plan image {image_url}: {e}")
        return {}

    # Build prompt with area context
    prompt = FLOOR_PLAN_ANALYSIS_PROMPT
    if surface_area > 0:
        prompt += f"\n\nKnown total area: {surface_area}m². Use this to calibrate your estimates."

    # Call Anthropic API
    try:
        response = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": anthropic_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 4096,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": img_data,
                                },
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
            },
            timeout=60.0,
        )
        response.raise_for_status()
        result = response.json()

        # Extract text content
        text_content = ""
        for block in result.get("content", []):
            if block.get("type") == "text":
                text_content += block["text"]

        # Parse JSON from response
        json_match = re.search(r"\{[\s\S]*\}", text_content)
        if json_match:
            return json.loads(json_match.group())

        return {"raw_response": text_content}

    except Exception as e:
        logger.error(f"AI floor plan analysis failed: {e}")
        return {}


def calculate_splitting_economics(
    total_area: float,
    unit_areas: list[float],
    price_per_sqm_whole: float,
    price_per_sqm_small: float,
    market_data: Optional[dict] = None,
) -> dict:
    """
    Calculate the economic viability of apartment splitting.

    Small apartments typically command a premium per m² over larger ones.
    """
    if market_data is None:
        market_data = load_market_data()

    value_whole = total_area * price_per_sqm_whole
    value_split = sum(area * price_per_sqm_small for area in unit_areas)

    # Splitting costs
    specific = market_data.get("renovation_costs_per_sqm", {}).get("specific", {})
    n_extra_units = len(unit_areas) - 1

    permit_cost = sum(specific.get("baugenehmigung_teilung", [3000, 8000])) / 2
    wall_cost = 15 * n_extra_units * sum(specific.get("neue_trennwaende_pro_sqm", [80, 150])) / 2
    bathroom_cost = n_extra_units * sum(specific.get("badezimmer_neu", [8000, 18000])) / 2
    install_cost = n_extra_units * sum(specific.get("neue_installationen_je_einheit", [5000, 12000])) / 2
    door_cost = n_extra_units * sum(specific.get("neue_tueren_pro_stueck", [800, 2500])) / 2

    total_split_cost = permit_cost + wall_cost + bathroom_cost + install_cost + door_cost

    return {
        "value_whole": round(value_whole, 2),
        "value_split": round(value_split, 2),
        "gross_value_add": round(value_split - value_whole, 2),
        "splitting_cost": round(total_split_cost, 2),
        "net_value_add": round(value_split - value_whole - total_split_cost, 2),
        "roi_splitting_pct": round(
            (value_split - value_whole - total_split_cost) / total_split_cost * 100, 1
        ) if total_split_cost > 0 else 0,
    }


def analyze_splitting_potential(
    listing: PropertyListing,
    config: Optional[dict] = None,
    market_data: Optional[dict] = None,
    use_ai: bool = False,
) -> SplittingAnalysis:
    """
    Full splitting potential analysis for a property listing.

    Args:
        listing: Property listing to analyze.
        config: Settings configuration.
        market_data: Market data configuration.
        use_ai: Whether to use AI vision for floor plan analysis.
    """
    if config is None:
        config = load_config()
    if market_data is None:
        market_data = load_market_data()

    analysis = SplittingAnalysis()
    analysis.total_area = listing.surface_area

    # Basic area check
    min_split_area = config.get("search_config", {}).get("thresholds", {}).get(
        "min_splitting_area", 80
    )

    if listing.surface_area < min_split_area:
        analysis.is_splittable = False
        analysis.splitting_score = 0
        return analysis

    # Determine number of possible units
    if listing.surface_area >= 150:
        n_units = 3
    elif listing.surface_area >= 80:
        n_units = 2
    else:
        analysis.is_splittable = False
        return analysis

    analysis.n_units = n_units

    # Check if units would meet minimum size
    avg_unit_area = listing.surface_area / n_units
    if avg_unit_area < 28:
        analysis.is_splittable = False
        analysis.min_area_met = False
        return analysis

    analysis.min_area_met = True

    # Estimate unit areas (not perfectly equal - account for hallways, walls)
    usable_area = listing.surface_area * 0.92  # ~8% lost to new walls/hallways
    if n_units == 2:
        # Try to make one slightly larger unit
        analysis.unit_areas = [
            round(usable_area * 0.55, 1),
            round(usable_area * 0.45, 1),
        ]
    else:
        analysis.unit_areas = [
            round(usable_area * 0.40, 1),
            round(usable_area * 0.35, 1),
            round(usable_area * 0.25, 1),
        ]

    # All units must be >= 28m²
    if any(area < 28 for area in analysis.unit_areas):
        analysis.is_splittable = False
        analysis.min_area_met = False
        return analysis

    # Bathroom analysis
    existing_baths = listing.bathrooms or 1
    if existing_baths >= n_units:
        analysis.separate_bathrooms = True
    else:
        # Need to add bathrooms - check if plumbing proximity allows it
        analysis.separate_bathrooms = True  # Assume possible with cost
        analysis.plumbing_positions = "Additional bathroom(s) required"

    # Window analysis (estimate from room count)
    estimated_windows = max(listing.rooms * 1.5, 4)  # At least 1.5 windows per room
    analysis.window_count = int(estimated_windows)

    if estimated_windows >= n_units * 2:
        analysis.natural_light_each_unit = True
        analysis.window_distribution = "Sufficient for all units"
    else:
        analysis.natural_light_each_unit = estimated_windows >= n_units
        analysis.window_distribution = "May be tight - verify on floor plan"

    # Separate access
    analysis.separate_access_possible = listing.rooms >= n_units + 1

    # Ventilation
    analysis.ventilation_ok = analysis.natural_light_each_unit

    # AI analysis if requested and floor plans available
    if use_ai:
        floor_plans = detect_floor_plan_images(listing)
        if floor_plans:
            ai_result = analyze_floor_plan_with_ai(
                floor_plans[0], listing.surface_area
            )
            if ai_result:
                analysis.ai_analysis_raw = json.dumps(ai_result, indent=2)
                # Override estimates with AI results
                if "splittable" in ai_result:
                    analysis.is_splittable = ai_result["splittable"]
                if "confidence" in ai_result:
                    analysis.confidence = ai_result["confidence"]
                if "proposed_split" in ai_result:
                    split = ai_result["proposed_split"]
                    if "units" in split:
                        analysis.proposed_units = split["units"]
                        analysis.unit_areas = [u.get("area", 0) for u in split["units"]]
                        analysis.n_units = len(split["units"])

    # Calculate economics
    from .valuation import get_market_reference, MUNICIPALITY_KEY_MAP

    # Price for whole apartment (current condition)
    ref_low, ref_high = get_market_reference(
        listing.municipality, listing.zone, listing.condition, market_data
    )
    whole_price_sqm = (ref_low + ref_high) / 2

    # Price for renovated smaller apartments (premium)
    reno_ref_low, reno_ref_high = get_market_reference(
        listing.municipality, listing.zone, "ristrutturato", market_data
    )
    small_price_sqm = (reno_ref_low + reno_ref_high) / 2 * 1.08  # 8% small-unit premium

    economics = calculate_splitting_economics(
        listing.surface_area,
        analysis.unit_areas,
        whole_price_sqm,
        small_price_sqm,
        market_data,
    )

    analysis.value_before_split = economics["value_whole"]
    analysis.value_after_split = economics["value_split"]
    analysis.splitting_cost = economics["splitting_cost"]
    analysis.net_value_add = economics["net_value_add"]

    # Calculate splitting score (0-100)
    score = 0

    # Area bonus (max 25 points)
    if listing.surface_area >= 150:
        score += 25
    elif listing.surface_area >= 120:
        score += 20
    elif listing.surface_area >= 100:
        score += 15
    elif listing.surface_area >= 80:
        score += 10

    # Bathrooms (max 20 points)
    if existing_baths >= n_units:
        score += 20
    elif existing_baths >= n_units - 1:
        score += 10

    # Windows/light (max 15 points)
    if analysis.natural_light_each_unit:
        score += 15
    elif analysis.window_count >= n_units:
        score += 8

    # Separate access (max 15 points)
    if analysis.separate_access_possible:
        score += 15

    # Economic viability (max 25 points)
    if analysis.net_value_add > 50000:
        score += 25
    elif analysis.net_value_add > 30000:
        score += 20
    elif analysis.net_value_add > 10000:
        score += 15
    elif analysis.net_value_add > 0:
        score += 10

    analysis.splitting_score = min(100, score)
    analysis.is_splittable = score >= 40
    if not analysis.confidence:
        analysis.confidence = min(1.0, score / 100)

    # Create unit descriptions
    if not analysis.proposed_units:
        for i, area in enumerate(analysis.unit_areas):
            rooms = max(1, int(area / 25))
            analysis.proposed_units.append({
                "unit": i + 1,
                "area": area,
                "rooms": rooms,
                "has_bathroom": True,
                "has_kitchen": True,
            })

    return analysis
