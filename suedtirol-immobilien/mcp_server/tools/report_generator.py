"""
Deal report generator for Südtirol Immobilien.

Generates structured markdown or JSON reports for investment deals.
"""

import json
from datetime import datetime
from typing import Optional

from scrapers.utils import PropertyListing
from analysis.deal_scorer import DealScore


def generate_deal_report(
    listing: PropertyListing,
    deal: DealScore,
    format: str = "markdown",
) -> str:
    """
    Generate a comprehensive deal report.

    Args:
        listing: The property listing.
        deal: The deal scoring result.
        format: Output format ('markdown' or 'json').

    Returns:
        Formatted report string.
    """
    if format == "json":
        return _generate_json_report(listing, deal)
    return _generate_markdown_report(listing, deal)


def _generate_markdown_report(listing: PropertyListing, deal: DealScore) -> str:
    """Generate markdown deal report."""
    v = deal.valuation
    s = deal.splitting
    r = deal.renovation

    report = f"""# Deal-Report: {listing.title or listing.address or listing.property_id}

**Generiert:** {datetime.now().strftime('%d.%m.%Y %H:%M')}
**Deal-Score:** {deal.deal_emoji} {deal.total_score}/100 — {deal.deal_label}

---

## Zusammenfassung

| Kennzahl | Wert |
|----------|------|
| Portal | {listing.source} |
| Listing-ID | {listing.property_id} |
| URL | {listing.url} |
| Kaufpreis | {_fmt_eur(listing.price)} |
| Fläche | {listing.surface_area} m² |
| Zimmer | {listing.rooms} |
| Bäder | {listing.bathrooms} |
| €/m² (Angebot) | {_fmt_eur(listing.price_per_sqm)} |
| €/m² (Marktref.) | {_fmt_eur(v.market_ref_mid) if v else 'N/A'} |
| Discount zum Markt | {v.discount_to_market_pct:.1f}% |
| Geschätzter ARV | {_fmt_eur(v.arv_total) if v else 'N/A'} |
| Geschätzter ROI | {v.roi_pct:.1f}% |
| Deal-Score | {deal.deal_emoji} {deal.total_score} Punkte |

## Score-Aufschlüsselung

| Komponente | Score | Gewicht |
|------------|-------|---------|
| Preis-Discount | {deal.price_discount_score}/100 | 30% |
| Lage | {deal.location_score}/100 | 25% |
| ROI-Prognose | {deal.roi_score}/100 | 25% |
| Teilungspotenzial | {deal.splitting_score}/100 | 10% |
| Liquidität | {deal.liquidity_score}/100 | 10% |
| **Gesamt** | **{deal.total_score}/100** | |

## Lage-Analyse

| Merkmal | Wert |
|---------|------|
| Gemeinde | {listing.municipality_de or listing.municipality} ({listing.municipality}) |
| Zone/Stadtteil | {listing.zone or 'Nicht angegeben'} |
| Lage-Tier | {v.location_tier if v else 'N/A'} |
| Lage-Score | {v.location_score:.1f}/10 |
| Ø-Preis Gemeinde | {_fmt_eur(v.municipality_avg_price)}/m² |
"""

    # Property details
    report += f"""
## Objektdetails

| Merkmal | Wert |
|---------|------|
| Immobilientyp | {listing.property_type} |
| Etage | {listing.floor if listing.floor is not None else 'N/A'} |
| Aufzug | {'Ja' if listing.elevator else 'Nein' if listing.elevator is not None else 'N/A'} |
| Balkon/Terrasse | {'Ja' if listing.balcony or listing.terrace else 'Nein'} |
| Garten | {'Ja' if listing.garden else 'Nein'} |
| Garage | {'Ja' if listing.garage else 'Nein'} |
| Keller | {'Ja' if listing.cellar else 'Nein'} |
| Energieklasse | {listing.energy_class or 'N/A'} |
| Heizung | {listing.heating_type or 'N/A'} |
| Baujahr | {listing.year_built or 'N/A'} |
| Zustand | {v.condition_assessed if v else listing.condition_de} |
| Renovierungsbedarf | {v.renovation_level if v else 'N/A'} |
"""

    # Renovation plan
    if r:
        report += "\n## Renovierungsplan\n\n"
        report += f"**Niveau:** {r.level}\n\n"
        report += "| Maßnahme | Menge | Geschätzte Kosten |\n"
        report += "|----------|-------|-------------------|\n"
        for item in r.items:
            report += f"| {item.name_de} | {item.quantity:.0f} {item.unit} | {_fmt_eur(item.cost_estimate)} |\n"
        report += f"| **Zwischensumme** | | **{_fmt_eur(r.subtotal)}** |\n"
        report += f"| Risikopuffer ({r.contingency_pct*100:.0f}%) | | {_fmt_eur(r.contingency)} |\n"
        report += f"| **Gesamt Renovierung** | | **{_fmt_eur(r.total_estimate)}** |\n"

    # Splitting potential
    if s:
        report += f"""
## Teilungspotenzial

| Merkmal | Wert |
|---------|------|
| Teilbar | {'Ja' if s.is_splittable else 'Nein'} |
| Konfidenz | {s.confidence:.0%} |
| Splitting-Score | {s.splitting_score}/100 |
| Anzahl Einheiten | {s.n_units} |
| Wert vor Teilung | {_fmt_eur(s.value_before_split)} |
| Wert nach Teilung | {_fmt_eur(s.value_after_split)} |
| Teilungskosten | {_fmt_eur(s.splitting_cost)} |
| Netto-Mehrwert | {_fmt_eur(s.net_value_add)} |
"""
        if s.proposed_units:
            report += "\n### Vorgeschlagene Aufteilung\n\n"
            report += "| Einheit | Fläche | Zimmer | Bad | Küche |\n"
            report += "|---------|--------|--------|-----|-------|\n"
            for i, unit in enumerate(s.proposed_units):
                if isinstance(unit, dict):
                    report += f"| {i+1} | {unit.get('area', 'N/A')} m² | {unit.get('rooms', 'N/A')} | {'Ja' if unit.get('has_bathroom') else 'Nein'} | {'Ja' if unit.get('has_kitchen') else 'Nein'} |\n"

        report += f"""
### Regulatorische Prüfung

| Anforderung | Erfüllt |
|-------------|---------|
| Mindestfläche (28m²) | {'✅' if s.min_area_met else '❌'} |
| Separate Bäder | {'✅' if s.separate_bathrooms else '❌'} |
| Natürliches Licht | {'✅' if s.natural_light_each_unit else '❌'} |
| Separater Zugang | {'✅' if s.separate_access_possible else '❌'} |
| Belüftung | {'✅' if s.ventilation_ok else '❌'} |
"""

    # Investment calculation
    if v:
        report += f"""
## Investment-Kalkulation

| Position | Betrag |
|----------|--------|
| Kaufpreis | {_fmt_eur(listing.price)} |
| Kaufnebenkosten | {_fmt_eur(v.purchase_costs)} |
| Renovierung | {_fmt_eur(v.renovation_cost_estimate)} |
| **Gesamtinvestment** | **{_fmt_eur(v.total_investment)}** |
| After-Repair-Value (ARV) | {_fmt_eur(v.arv_total)} |
| Verkaufskosten | {_fmt_eur(v.selling_costs)} |
| **Netto-Gewinn** | **{_fmt_eur(v.net_profit)}** |
| **ROI** | **{v.roi_pct:.1f}%** |
"""

    # Risks and recommendation
    if deal.risks:
        report += "\n## Risiken\n\n"
        for risk in deal.risks:
            report += f"- {risk}\n"

    if deal.action_items:
        report += "\n## Nächste Schritte\n\n"
        for i, action in enumerate(deal.action_items, 1):
            report += f"{i}. {action}\n"

    report += f"\n## Empfehlung\n\n**{deal.recommendation}**\n"

    # Warnings
    if v and v.warnings:
        report += "\n## Hinweise\n\n"
        for warning in v.warnings:
            report += f"- ⚠️ {warning}\n"

    # Description
    if listing.description:
        report += f"\n## Originalbeschreibung\n\n{listing.description[:1000]}"
        if len(listing.description) > 1000:
            report += "\n\n*(gekürzt)*"

    report += f"\n\n---\n*Report generiert am {datetime.now().strftime('%d.%m.%Y %H:%M')}*\n"

    return report


def _generate_json_report(listing: PropertyListing, deal: DealScore) -> str:
    """Generate JSON deal report."""
    report = {
        "report_date": datetime.now().isoformat(),
        "listing": listing.to_dict(),
        "deal_analysis": deal.to_dict(),
    }
    return json.dumps(report, indent=2, ensure_ascii=False, default=str)


def _fmt_eur(value: float) -> str:
    """Format a number as EUR currency."""
    if value is None:
        return "N/A"
    if abs(value) >= 1000:
        return f"€{value:,.0f}"
    return f"€{value:,.2f}"


def generate_summary_table(
    deals: list[tuple[PropertyListing, DealScore]],
) -> str:
    """
    Generate a summary comparison table for multiple deals.
    """
    if not deals:
        return "Keine Deals gefunden."

    header = (
        "| # | Score | Gemeinde | Preis | Fläche | €/m² | Discount | ROI | Teilbar |\n"
        "|---|-------|----------|-------|--------|------|----------|-----|--------|\n"
    )

    rows = []
    for i, (listing, deal) in enumerate(deals, 1):
        v = deal.valuation
        s = deal.splitting
        rows.append(
            f"| {i} | {deal.deal_emoji} {deal.total_score} | "
            f"{listing.municipality_de or listing.municipality} | "
            f"{_fmt_eur(listing.price)} | "
            f"{listing.surface_area}m² | "
            f"{_fmt_eur(listing.price_per_sqm)} | "
            f"{v.discount_to_market_pct:.0f}% | "
            f"{v.roi_pct:.0f}% | "
            f"{'Ja' if s and s.is_splittable else 'Nein'} |"
        )

    return header + "\n".join(rows)
