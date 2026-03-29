#!/usr/bin/env python3
"""
Generate realistic sample listings for South Tyrol to demonstrate
the full analysis pipeline without live scraping.

Based on real market data from immobiliare.it/idealista.it (2025/2026).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from scrapers.utils import PropertyListing, save_listings


def generate_sample_listings() -> list[PropertyListing]:
    """Create realistic sample listings for Bozen and surrounding area."""
    return [
        # 1. Underpriced large apartment in Bozen Gries - strong splitting candidate
        PropertyListing(
            property_id="IMM-101234",
            source="immobiliare",
            url="https://www.immobiliare.it/annunci/101234/",
            title="Ampio appartamento da ristrutturare - Gries/Bozen",
            description=(
                "Großzügige 5-Zimmer-Wohnung im Stadtteil Gries, zu renovieren. "
                "Ideale Raumaufteilung mit 2 Bädern, großer Wohnküche und Südbalkon. "
                "Keller und Garagenstellplatz. Energieklasse G. Baujahr 1975. "
                "Geeignet auch für Aufteilung in zwei separate Wohneinheiten."
            ),
            price=380000,
            surface_area=135,
            rooms=5,
            bathrooms=2,
            floor=2,
            total_floors=4,
            elevator=True,
            balcony=True,
            garage=True,
            cellar=True,
            energy_class="G",
            heating_type="centralizzato",
            year_built=1975,
            condition="da_ristrutturare",
            condition_de="renovierungsbedürftig",
            latitude=46.4963,
            longitude=11.3400,
            address="Via Duca d'Aosta 48, Gries",
            municipality="bolzano",
            municipality_de="Bozen",
            zone="gries_quirein",
            property_type="appartamento",
            images=["https://example.com/img1.jpg", "https://example.com/img2.jpg"],
            floor_plan_images=["https://example.com/planimetria1.jpg"],
            agency_name="Immobiliare Gasser",
            agency_phone="+39 0471 123456",
            listing_date="2025-10-15",
        ),
        # 2. Good deal in Bozen Zentrum - small but well-priced
        PropertyListing(
            property_id="IMM-102567",
            source="immobiliare",
            url="https://www.immobiliare.it/annunci/102567/",
            title="Trilocale ristrutturato centro Bolzano",
            description=(
                "Frisch renovierte 3-Zimmer-Wohnung im Zentrum von Bozen. "
                "Neue Küche, neues Bad, Parkettböden. Energieklasse C. "
                "Sofort beziehbar. Ruhige Lage in Seitenstraße. "
                "Perfekt als Erstwohnung oder Kapitalanlage."
            ),
            price=295000,
            surface_area=72,
            rooms=3,
            bathrooms=1,
            floor=3,
            total_floors=5,
            elevator=True,
            balcony=True,
            energy_class="C",
            heating_type="autonomo",
            year_built=1960,
            condition="ristrutturato",
            condition_de="renoviert",
            latitude=46.4983,
            longitude=11.3548,
            address="Via dei Portici 22, Zentrum",
            municipality="bolzano",
            municipality_de="Bozen",
            zone="zentrum_rentsch",
            property_type="appartamento",
            agency_name="Agenzia Alto Adige Immobiliare",
            agency_phone="+39 0471 234567",
            listing_date="2025-12-01",
        ),
        # 3. Villa near Meran - excellent splitting potential
        PropertyListing(
            property_id="IMM-103890",
            source="immobiliare",
            url="https://www.immobiliare.it/annunci/103890/",
            title="Villa bifamiliare Obermais - Merano",
            description=(
                "Freistehende Villa in Obermais mit herrlichem Blick auf die Texelgruppe. "
                "2 Etagen, 7 Zimmer, 3 Bäder, großer Garten mit altem Baumbestand. "
                "Teilweise renovierungsbedürftig. EG und OG mit separaten Eingängen. "
                "Ideale Voraussetzung für Aufteilung in 2 Wohnungen. "
                "Garage für 2 Autos. Energieklasse F."
            ),
            price=650000,
            surface_area=210,
            rooms=7,
            bathrooms=3,
            floor=0,
            total_floors=2,
            garden=True,
            garage=True,
            cellar=True,
            terrace=True,
            energy_class="F",
            heating_type="autonomo a gas",
            year_built=1965,
            condition="buono",
            condition_de="guter Zustand",
            latitude=46.6741,
            longitude=11.1597,
            address="Cavourstraße 15, Obermais",
            municipality="merano",
            municipality_de="Meran",
            zone="obermais",
            property_type="villa",
            images=["https://example.com/villa1.jpg"],
            floor_plan_images=["https://example.com/villa_plan.jpg"],
            agency_name="Paregger & Partner",
            agency_phone="+39 0473 345678",
            listing_date="2025-11-20",
        ),
        # 4. Cheap opportunity in Neumarkt
        PropertyListing(
            property_id="IDL-204561",
            source="idealista",
            url="https://www.idealista.it/immobile/204561/",
            title="Quadrilocale da ristrutturare a Egna",
            description=(
                "4-Zimmer-Wohnung in Neumarkt, komplett zu renovieren. "
                "100m², Erdgeschoss mit kleinem Garten. 1 Bad. "
                "Neue Heizung bereits installiert. Ruhige Wohnlage. "
                "Gute Anbindung an die Brennerautobahn. "
                "Preis verhandelbar. Da ristrutturare completamente."
            ),
            price=195000,
            surface_area=100,
            rooms=4,
            bathrooms=1,
            floor=0,
            total_floors=3,
            garden=True,
            cellar=True,
            energy_class="F",
            heating_type="autonomo",
            year_built=1980,
            condition="da_ristrutturare",
            condition_de="renovierungsbedürftig",
            latitude=46.3120,
            longitude=11.2636,
            address="Via Stazione 8, Egna/Neumarkt",
            municipality="egna",
            municipality_de="Neumarkt",
            zone="zentrum",
            property_type="appartamento",
            agency_name="Immobiliare Unterland",
            agency_phone="+39 0471 456789",
            listing_date="2025-09-10",
        ),
        # 5. Attic in Brixen - good value
        PropertyListing(
            property_id="IMM-105432",
            source="immobiliare",
            url="https://www.immobiliare.it/annunci/105432/",
            title="Attico panoramico Bressanone centro",
            description=(
                "Helle Dachgeschosswohnung im Zentrum von Brixen mit Panoramablick. "
                "4 Zimmer, 2 Bäder, große Dachterrasse (25m²). "
                "Guter Zustand, teilweise zu modernisieren (Küche, Böden). "
                "Klimahaus B. Aufzug vorhanden. Tiefgaragenstellplatz."
            ),
            price=420000,
            surface_area=110,
            rooms=4,
            bathrooms=2,
            floor=5,
            total_floors=5,
            elevator=True,
            terrace=True,
            garage=True,
            energy_class="B",
            heating_type="teleriscaldamento",
            year_built=2005,
            condition="buono",
            condition_de="guter Zustand",
            latitude=46.7154,
            longitude=11.6563,
            address="Große Lauben 30, Bressanone",
            municipality="bressanone",
            municipality_de="Brixen",
            zone="zentrum",
            property_type="attico",
            agency_name="Engel & Völkers Brixen",
            agency_phone="+39 0472 567890",
            listing_date="2025-12-15",
        ),
        # 6. Bargain in Schlanders
        PropertyListing(
            property_id="IDL-206789",
            source="idealista",
            url="https://www.idealista.it/immobile/206789/",
            title="Appartamento 3 locali Silandro centro",
            description=(
                "Günstige 3-Zimmer-Wohnung im Zentrum von Schlanders. "
                "Renovierungsbedürftig aber solide Bausubstanz. "
                "85m², 1 Bad, Balkon nach Süden. Keller. "
                "Gute Infrastruktur im Ort. Energieklasse G. "
                "Schnäppchen im Vinschgau!"
            ),
            price=155000,
            surface_area=85,
            rooms=3,
            bathrooms=1,
            floor=1,
            total_floors=3,
            balcony=True,
            cellar=True,
            energy_class="G",
            heating_type="centralizzato",
            year_built=1970,
            condition="da_ristrutturare",
            condition_de="renovierungsbedürftig",
            latitude=46.6268,
            longitude=10.7726,
            address="Hauptstraße 42, Silandro/Schlanders",
            municipality="silandro",
            municipality_de="Schlanders",
            zone="zentrum",
            property_type="appartamento",
            agency_name="Vinschgau Immobilien",
            agency_phone="+39 0473 678901",
            listing_date="2025-08-20",
        ),
        # 7. Overpriced property in Leifers (control - should score low)
        PropertyListing(
            property_id="IMM-107654",
            source="immobiliare",
            url="https://www.immobiliare.it/annunci/107654/",
            title="Bilocale Laives centro",
            description=(
                "Gepflegte 2-Zimmer-Wohnung in Leifers. "
                "62m², renoviert, 1 Bad, kleiner Balkon. "
                "3. Stock ohne Aufzug. Energieklasse D."
            ),
            price=280000,
            surface_area=62,
            rooms=2,
            bathrooms=1,
            floor=3,
            total_floors=4,
            elevator=False,
            balcony=True,
            energy_class="D",
            heating_type="autonomo",
            year_built=1985,
            condition="ristrutturato",
            condition_de="renoviert",
            latitude=46.4310,
            longitude=11.3400,
            address="Via Kennedy 5, Laives/Leifers",
            municipality="laives",
            municipality_de="Leifers",
            zone="zentrum",
            property_type="appartamento",
            agency_name="Casa & Co.",
            agency_phone="+39 0471 789012",
            listing_date="2025-11-01",
        ),
        # 8. Large apartment in Eppan
        PropertyListing(
            property_id="IMM-108321",
            source="immobiliare",
            url="https://www.immobiliare.it/annunci/108321/",
            title="Grande appartamento St. Michael/Eppan",
            description=(
                "Geräumige 4-Zimmer-Wohnung in St. Michael, Eppan. "
                "120m², 1 Bad, Wohnküche, Loggia. Zu renovieren. "
                "Ruhige Lage im Überetsch mit Blick auf die Weinberge. "
                "Keller und Autostellplatz. Energieklasse F. "
                "Viel Potenzial für Wertsteigerung nach Sanierung."
            ),
            price=340000,
            surface_area=120,
            rooms=4,
            bathrooms=1,
            floor=1,
            total_floors=3,
            cellar=True,
            garage=True,
            energy_class="F",
            heating_type="centralizzato",
            year_built=1978,
            condition="da_ristrutturare",
            condition_de="renovierungsbedürftig",
            latitude=46.4540,
            longitude=11.2590,
            address="Bahnhofstraße 12, St. Michael/Eppan",
            municipality="appiano-sulla-strada-del-vino",
            municipality_de="Eppan",
            zone="st_michael_st_pauls",
            property_type="appartamento",
            agency_name="Immobiliare Überetsch",
            agency_phone="+39 0471 890123",
            listing_date="2025-10-05",
        ),
        # 9. Sterzing opportunity
        PropertyListing(
            property_id="IDL-209876",
            source="idealista",
            url="https://www.idealista.it/immobile/209876/",
            title="Trilocale Vipiteno buono stato",
            description=(
                "3-Zimmer-Wohnung in Sterzing in gutem Zustand. "
                "78m², 1 Bad, Balkon. 1. OG mit Aufzug. "
                "Sofort beziehbar, nur leichte Auffrischung nötig. "
                "Energieklasse D. Autostellplatz vorhanden. "
                "Ideale Ferienwohnung nahe Skigebiet."
            ),
            price=210000,
            surface_area=78,
            rooms=3,
            bathrooms=1,
            floor=1,
            total_floors=4,
            elevator=True,
            balcony=True,
            garage=True,
            energy_class="D",
            heating_type="teleriscaldamento",
            year_built=1990,
            condition="buono",
            condition_de="guter Zustand",
            latitude=46.8978,
            longitude=11.4320,
            address="Neustadt 28, Vipiteno/Sterzing",
            municipality="vipiteno",
            municipality_de="Sterzing",
            zone="zentrum",
            property_type="appartamento",
            agency_name="Wipptal Immobilien",
            agency_phone="+39 0472 901234",
            listing_date="2025-11-10",
        ),
        # 10. Bruneck apartment
        PropertyListing(
            property_id="IMM-110543",
            source="immobiliare",
            url="https://www.immobiliare.it/annunci/110543/",
            title="Quadrilocale Brunico - buon prezzo",
            description=(
                "Gepflegte 4-Zimmer-Wohnung in Bruneck. "
                "95m², 1 Bad, Balkon, Keller. 2. OG. "
                "Teilweise zu modernisieren (Bad, Küche). "
                "Gute Lage nahe Stadtpark. Energieklasse E. "
                "Auch als Ferienwohnung nutzbar (Kronplatz)."
            ),
            price=260000,
            surface_area=95,
            rooms=4,
            bathrooms=1,
            floor=2,
            total_floors=4,
            balcony=True,
            cellar=True,
            energy_class="E",
            heating_type="centralizzato",
            year_built=1982,
            condition="buono",
            condition_de="guter Zustand",
            latitude=46.7962,
            longitude=11.9365,
            address="Stadtgasse 15, Brunico/Bruneck",
            municipality="brunico",
            municipality_de="Bruneck",
            zone="zentrum",
            property_type="appartamento",
            agency_name="Pustertal Immobilien",
            agency_phone="+39 0474 012345",
            listing_date="2025-12-05",
        ),
    ]


if __name__ == "__main__":
    listings = generate_sample_listings()
    output = save_listings(listings, "listings.json")
    print(f"Generated {len(listings)} sample listings -> {output}")
