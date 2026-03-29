"""
Renovation cost calculator for Südtirol real estate.

Estimates renovation costs based on property condition, area,
and specific work items needed.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from scrapers.utils import PropertyListing, load_market_data

logger = logging.getLogger(__name__)


@dataclass
class RenovationItem:
    """A single renovation work item."""

    name: str
    name_de: str
    description: str = ""
    quantity: float = 1.0
    unit: str = "Stück"
    cost_low: float = 0.0
    cost_high: float = 0.0

    @property
    def cost_estimate(self) -> float:
        """Midpoint estimate."""
        return self.quantity * (self.cost_low + self.cost_high) / 2

    @property
    def cost_range(self) -> tuple[float, float]:
        return self.quantity * self.cost_low, self.quantity * self.cost_high


@dataclass
class RenovationPlan:
    """Complete renovation plan with cost breakdown."""

    level: str = ""  # leicht, mittel, schwer, luxus
    items: list = field(default_factory=list)
    contingency_pct: float = 0.10  # 10% contingency buffer

    @property
    def subtotal(self) -> float:
        return sum(item.cost_estimate for item in self.items)

    @property
    def contingency(self) -> float:
        return self.subtotal * self.contingency_pct

    @property
    def total_estimate(self) -> float:
        return self.subtotal + self.contingency

    @property
    def total_low(self) -> float:
        return sum(item.cost_range[0] for item in self.items)

    @property
    def total_high(self) -> float:
        high = sum(item.cost_range[1] for item in self.items)
        return high * (1 + self.contingency_pct)

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "items": [
                {
                    "name": item.name,
                    "name_de": item.name_de,
                    "description": item.description,
                    "quantity": item.quantity,
                    "unit": item.unit,
                    "cost_estimate": round(item.cost_estimate, 2),
                    "cost_range": [
                        round(item.cost_range[0], 2),
                        round(item.cost_range[1], 2),
                    ],
                }
                for item in self.items
            ],
            "subtotal": round(self.subtotal, 2),
            "contingency_pct": self.contingency_pct,
            "contingency": round(self.contingency, 2),
            "total_estimate": round(self.total_estimate, 2),
            "total_range": [round(self.total_low, 2), round(self.total_high, 2)],
        }


def create_renovation_plan(
    surface_area: float,
    level: str = "mittel",
    bathrooms_new: int = 0,
    kitchen_new: bool = False,
    splitting: bool = False,
    n_split_units: int = 2,
    market_data: Optional[dict] = None,
) -> RenovationPlan:
    """
    Create a detailed renovation plan.

    Args:
        surface_area: Property area in m².
        level: Renovation level (leicht, mittel, schwer, luxus).
        bathrooms_new: Number of new bathrooms to add.
        kitchen_new: Whether to install a new kitchen.
        splitting: Whether apartment splitting is planned.
        n_split_units: Number of units to split into.
        market_data: Market data configuration.
    """
    if market_data is None:
        market_data = load_market_data()

    costs = market_data.get("renovation_costs_per_sqm", {})
    specific = costs.get("specific", {})
    plan = RenovationPlan(level=level)

    # Base renovation by level
    if level == "leicht":
        plan.items.extend([
            RenovationItem(
                name="Painting",
                name_de="Malerarbeiten",
                description="Walls and ceilings throughout",
                quantity=surface_area,
                unit="m²",
                cost_low=specific.get("malerarbeiten_pro_sqm", [15, 35])[0],
                cost_high=specific.get("malerarbeiten_pro_sqm", [15, 35])[1],
            ),
            RenovationItem(
                name="Flooring",
                name_de="Fußbodenbeläge",
                description="New floor coverings",
                quantity=surface_area * 0.7,  # ~70% of area needs new floors
                unit="m²",
                cost_low=specific.get("fussboden_pro_sqm", [40, 120])[0],
                cost_high=specific.get("fussboden_pro_sqm", [40, 120])[1],
            ),
        ])
    elif level == "mittel":
        plan.items.extend([
            RenovationItem(
                name="Painting",
                name_de="Malerarbeiten",
                quantity=surface_area,
                unit="m²",
                cost_low=specific.get("malerarbeiten_pro_sqm", [15, 35])[0],
                cost_high=specific.get("malerarbeiten_pro_sqm", [15, 35])[1],
            ),
            RenovationItem(
                name="Flooring",
                name_de="Fußbodenbeläge",
                quantity=surface_area,
                unit="m²",
                cost_low=specific.get("fussboden_pro_sqm", [40, 120])[0],
                cost_high=specific.get("fussboden_pro_sqm", [40, 120])[1],
            ),
            RenovationItem(
                name="Bathroom renovation",
                name_de="Badsanierung",
                description="Full bathroom renovation",
                quantity=1,
                unit="Stück",
                cost_low=specific.get("badezimmer_neu", [8000, 18000])[0],
                cost_high=specific.get("badezimmer_neu", [8000, 18000])[1],
            ),
            RenovationItem(
                name="Window replacement",
                name_de="Fenstertausch",
                description="Estimated 5-8 windows",
                quantity=6,
                unit="Stück",
                cost_low=specific.get("fenster_pro_stueck", [800, 2000])[0],
                cost_high=specific.get("fenster_pro_stueck", [800, 2000])[1],
            ),
            RenovationItem(
                name="Partial electrical update",
                name_de="Elektrik teilweise",
                quantity=surface_area * 0.5,
                unit="m²",
                cost_low=specific.get("elektrik_komplett_pro_sqm", [80, 150])[0] * 0.5,
                cost_high=specific.get("elektrik_komplett_pro_sqm", [80, 150])[1] * 0.5,
            ),
        ])
    elif level in ("schwer", "luxus"):
        plan.items.extend([
            RenovationItem(
                name="Complete electrical rewiring",
                name_de="Elektrik komplett",
                quantity=surface_area,
                unit="m²",
                cost_low=specific.get("elektrik_komplett_pro_sqm", [80, 150])[0],
                cost_high=specific.get("elektrik_komplett_pro_sqm", [80, 150])[1],
            ),
            RenovationItem(
                name="Complete heating system",
                name_de="Heizung komplett",
                quantity=surface_area,
                unit="m²",
                cost_low=specific.get("heizung_neu_pro_sqm", [60, 120])[0],
                cost_high=specific.get("heizung_neu_pro_sqm", [60, 120])[1],
            ),
            RenovationItem(
                name="Flooring",
                name_de="Fußbodenbeläge",
                quantity=surface_area,
                unit="m²",
                cost_low=specific.get("fussboden_pro_sqm", [40, 120])[0],
                cost_high=specific.get("fussboden_pro_sqm", [40, 120])[1],
            ),
            RenovationItem(
                name="Painting & plastering",
                name_de="Maler- und Verputzarbeiten",
                quantity=surface_area,
                unit="m²",
                cost_low=specific.get("malerarbeiten_pro_sqm", [15, 35])[0] * 1.5,
                cost_high=specific.get("malerarbeiten_pro_sqm", [15, 35])[1] * 1.5,
            ),
            RenovationItem(
                name="Bathroom - complete new",
                name_de="Badezimmer komplett neu",
                quantity=1,
                unit="Stück",
                cost_low=specific.get("badezimmer_neu", [8000, 18000])[0],
                cost_high=specific.get("badezimmer_neu", [8000, 18000])[1],
            ),
            RenovationItem(
                name="Window replacement",
                name_de="Fenstertausch",
                quantity=8,
                unit="Stück",
                cost_low=specific.get("fenster_pro_stueck", [800, 2000])[0],
                cost_high=specific.get("fenster_pro_stueck", [800, 2000])[1],
            ),
            RenovationItem(
                name="Interior doors",
                name_de="Innentüren",
                quantity=5,
                unit="Stück",
                cost_low=specific.get("neue_tueren_pro_stueck", [800, 2500])[0],
                cost_high=specific.get("neue_tueren_pro_stueck", [800, 2500])[1],
            ),
        ])

    # Additional bathrooms
    if bathrooms_new > 0:
        plan.items.append(
            RenovationItem(
                name="New bathroom(s)",
                name_de="Neue(s) Badezimmer",
                description=f"Add {bathrooms_new} new bathroom(s) with all installations",
                quantity=bathrooms_new,
                unit="Stück",
                cost_low=specific.get("badezimmer_neu", [8000, 18000])[0],
                cost_high=specific.get("badezimmer_neu", [8000, 18000])[1],
            )
        )
        plan.items.append(
            RenovationItem(
                name="Plumbing for new bathrooms",
                name_de="Sanitärinstallation",
                quantity=bathrooms_new,
                unit="Stück",
                cost_low=specific.get("neue_installationen_je_einheit", [5000, 12000])[0],
                cost_high=specific.get("neue_installationen_je_einheit", [5000, 12000])[1],
            )
        )

    # Kitchen
    if kitchen_new:
        plan.items.append(
            RenovationItem(
                name="New kitchen",
                name_de="Neue Küche",
                quantity=1,
                unit="Stück",
                cost_low=specific.get("kueche_neu", [5000, 25000])[0],
                cost_high=specific.get("kueche_neu", [5000, 25000])[1],
            )
        )

    # Splitting costs
    if splitting and n_split_units > 1:
        extra_units = n_split_units - 1

        plan.items.append(
            RenovationItem(
                name="Building permit for splitting",
                name_de="Baugenehmigung Teilung",
                quantity=1,
                unit="Stück",
                cost_low=specific.get("baugenehmigung_teilung", [3000, 8000])[0],
                cost_high=specific.get("baugenehmigung_teilung", [3000, 8000])[1],
            )
        )

        # New partition walls (estimate ~15m² of new wall per split)
        wall_area = 15 * extra_units
        plan.items.append(
            RenovationItem(
                name="Partition walls",
                name_de="Trennwände",
                description=f"New partition walls for {n_split_units} units",
                quantity=wall_area,
                unit="m²",
                cost_low=specific.get("neue_trennwaende_pro_sqm", [80, 150])[0],
                cost_high=specific.get("neue_trennwaende_pro_sqm", [80, 150])[1],
            )
        )

        # New entrance doors
        plan.items.append(
            RenovationItem(
                name="Entrance doors",
                name_de="Eingangstüren",
                quantity=extra_units,
                unit="Stück",
                cost_low=1500,
                cost_high=3500,
            )
        )

        # Separate utility meters
        plan.items.append(
            RenovationItem(
                name="Separate utility connections",
                name_de="Separate Versorgungsanschlüsse",
                description="Electricity, water, gas meters per unit",
                quantity=extra_units,
                unit="Stück",
                cost_low=2000,
                cost_high=5000,
            )
        )

    # Adjust contingency for complex projects
    if splitting or level == "schwer":
        plan.contingency_pct = 0.15  # 15% for complex projects
    elif level == "luxus":
        plan.contingency_pct = 0.12

    return plan


def estimate_renovation_for_listing(
    listing: PropertyListing,
    market_data: Optional[dict] = None,
) -> RenovationPlan:
    """
    Automatically estimate renovation needs and create a plan for a listing.
    """
    if market_data is None:
        market_data = load_market_data()

    # Determine renovation level from condition
    level_map = {
        "nuovo": "leicht",
        "ristrutturato": "leicht",
        "buono": "mittel",
        "da_ristrutturare": "schwer",
    }
    level = level_map.get(listing.condition, "mittel")

    # Determine if new bathroom needed
    bathrooms_new = 0
    if listing.bathrooms <= 1 and listing.rooms >= 4:
        bathrooms_new = 1

    # Determine if kitchen needed
    kitchen_new = level in ("schwer", "luxus")

    # Check splitting potential
    splitting = listing.surface_area >= 80
    n_units = 2 if listing.surface_area < 150 else 3

    return create_renovation_plan(
        surface_area=listing.surface_area,
        level=level,
        bathrooms_new=bathrooms_new,
        kitchen_new=kitchen_new,
        splitting=splitting,
        n_split_units=n_units,
        market_data=market_data,
    )
