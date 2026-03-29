# Südtirol Immobilien Investment Analyzer

Automated real estate investment analysis tool for South Tyrol (Province of Bolzano, Italy). Scans property portals, evaluates listings, and identifies profitable fix-and-flip and apartment splitting opportunities.

## Features

- **Multi-Portal Scraping**: Scrapes immobiliare.it and idealista.it (via Apify)
- **Market Valuation**: Compares listing prices against zone-specific market data
- **Deal Scoring**: Weighted scoring system (A/B/C/No Deal classification)
- **Floor Plan Analysis**: AI-powered floor plan analysis for splitting potential
- **Renovation Calculator**: Detailed cost estimates for renovation projects
- **Apartment Splitting**: Economic analysis of splitting larger units
- **Report Generation**: Detailed markdown/JSON deal reports
- **MCP Server**: Model Context Protocol server for AI assistant integration
- **Bilingual Support**: Handles German and Italian property descriptions

## Project Structure

```
suedtirol-immobilien/
├── config/
│   ├── settings.yaml          # Search parameters, thresholds, API config
│   └── market_data.yaml       # Reference prices €/m² by municipality & zone
├── scrapers/
│   ├── immobiliare_scraper.py # immobiliare.it scraper
│   ├── idealista_scraper.py   # idealista.it scraper (+ Apify integration)
│   └── utils.py               # Shared utilities, data models, deduplication
├── analysis/
│   ├── valuation.py           # Market valuation & investment calculation
│   ├── floor_plan_analyzer.py # Floor plan analysis & splitting potential
│   ├── renovation_calculator.py # Renovation cost estimator
│   └── deal_scorer.py         # Deal scoring & ranking system
├── mcp_server/
│   ├── main.py                # MCP server entry point
│   └── tools/
│       └── report_generator.py # Deal report generation
├── output/
│   ├── reports/               # Generated deal reports
│   └── data/                  # Raw data & analysis results
├── run_analysis.py            # Main CLI entry point
└── requirements.txt
```

## Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Environment Variables

```bash
export APIFY_API_TOKEN="your_apify_token"      # For idealista.it scraping
export ANTHROPIC_API_KEY="your_anthropic_key"   # For AI floor plan analysis
```

### Usage

```bash
# Scrape a single municipality
python run_analysis.py --municipality bolzano

# Scrape all configured municipalities
python run_analysis.py --all

# Only scrape immobiliare.it
python run_analysis.py --municipality merano --portal immobiliare

# Analyze previously stored listings
python run_analysis.py --analyze-stored

# Generate report for a specific listing
python run_analysis.py --report <listing_id>

# Show top 20 deals
python run_analysis.py --all --top 20
```

### MCP Server

Add to your Claude Code or AI assistant configuration:

```json
{
  "mcpServers": {
    "suedtirol-immobilien": {
      "command": "python",
      "args": ["mcp_server/main.py"],
      "env": {
        "APIFY_API_TOKEN": "<YOUR_TOKEN>",
        "ANTHROPIC_API_KEY": "<YOUR_KEY>"
      }
    }
  }
}
```

Available MCP tools:
- `search_properties` - Search listings by municipality
- `analyze_deal` - Full deal analysis with scoring
- `analyze_floor_plan` - AI floor plan evaluation
- `calculate_renovation` - Renovation cost calculator
- `get_market_data` - Market prices by municipality
- `compare_listings` - Side-by-side comparison
- `generate_report` - Detailed deal reports

## Deal Scoring System

| Grade | Score | Action |
|-------|-------|--------|
| A-Deal | ≥80 | Buy immediately |
| B-Deal | 60-79 | Investigate further |
| C-Deal | 40-59 | Only with price negotiation |
| No Deal | <40 | Do not pursue |

### Score Components

| Component | Weight | Description |
|-----------|--------|-------------|
| Price Discount | 30% | Discount vs. market reference price |
| Location | 25% | Municipality tier, amenities, transport |
| ROI Projection | 25% | Projected return on investment |
| Splitting Potential | 10% | Apartment splitting feasibility |
| Liquidity | 10% | Expected resale speed |

## Market Coverage

### Tier 1 (Urban - highest liquidity)
- Bolzano/Bozen (Ø €4,939/m²)
- Merano/Meran (Ø €4,500/m²)

### Tier 2 (Suburban - good value)
- Bressanone/Brixen, Laives/Leifers, Appiano/Eppan, Lana, Brunico/Bruneck

### Tier 3 (Value opportunities)
- Egna/Neumarkt, Silandro/Schlanders, Vipiteno/Sterzing, Caldaro/Kaltern

## Italian Market Notes

- **Cadastral Value**: Property transfer tax is based on cadastral value (~65% of market), not purchase price
- **Prima Casa**: 2% registration tax (vs 9%) for primary residence
- **Red Flags**: Automatically excludes subsidized housing (edilizia agevolata), bare ownership (nuda proprietà), surface rights (diritto di superficie)
- **Minimum Apartment Size**: 28m² (1 person), 38m² (2 persons)
- **Capital Gains**: Exempt after 5 years; 26% flat rate within 5 years
