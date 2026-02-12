# zukunvt Angebot Automation

Automatisiertes System zur Erstellung von Angeboten (Proposals) und Projektphasen-Plänen für die zukunvt Digital Marketing Agency.

## Architektur

```
ClickUp Task (Status: "TO DO")
    → Webhook / n8n Trigger
    → Task-Daten lesen (Custom Fields)
    → Google Drive Templates laden
    → Claude AI generiert Angebot
    → Google Doc erstellen
    → ClickUp Task updaten (Status: "TO REVIEW (INTERN)")
```

## Stack

- **TypeScript** — Core Logic
- **ClickUp API v2** — Task-Management, Custom Fields
- **Google Drive API** — Template-Ordner, Referenz-Angebote
- **Google Docs API** — Angebots-Dokumente erstellen
- **Anthropic Claude API** — Angebots-Text-Generierung
- **n8n** — Workflow-Orchestrierung
- **Express** — Webhook Server

## Setup

```bash
# Dependencies installieren
cd zukunvt-angebot-automation
npm install

# Environment konfigurieren
cp .env.example .env
# → API Keys eintragen

# Entwicklung
npm run dev

# Tests
npm test

# Build
npm run build
npm start
```

## Projektstruktur

```
src/
├── config/
│   ├── pricing.ts          # 2026 Preisliste
│   ├── templates.ts        # Angebots-Struktur & Formatierung
│   └── team.ts             # Team-Zuordnungen
├── clickup/
│   ├── client.ts           # ClickUp API Client
│   ├── webhook-handler.ts  # Express Webhook Server
│   └── custom-fields.ts    # Custom Field Mapping
├── google/
│   ├── drive-client.ts     # Google Drive: Templates lesen
│   ├── docs-client.ts      # Google Docs: Angebote erstellen
│   └── template-parser.ts  # Bestehende Angebote parsen
├── ai/
│   ├── proposal-generator.ts  # Claude API Integration
│   └── phase-planner.ts       # Projektphasen-Generator
├── models/
│   ├── proposal.ts         # Angebots-Datenmodell
│   ├── client-data.ts      # Kundendaten-Interface
│   └── project-phase.ts    # Projektphasen-Modell
└── index.ts                # Entry Point
```

## Verwendung

### Als Webhook Server

```bash
npm start
# → POST /webhook/clickup (ClickUp Webhooks)
# → POST /trigger/proposal (n8n / manuell)
# → GET /health
```

### Manuell (CLI)

```bash
npx ts-node src/index.ts --task CLICKUP_TASK_ID
```

### In n8n

Siehe `n8n/setup-guide.md` für die Einrichtung des n8n Workflows.

## Angebots-Struktur (5 Seiten)

1. **Anschreiben** — Persönlicher, kollaborativer Ton
2. **Rechtlicher Hinweis** — AGB, Gültigkeit, Urheberrecht
3. **Kalkulation** — Projektphasen mit Preisen und Deliverables
4. **Zusammenfassung** — Zahlungsbedingungen, Netto/MwSt./Brutto
5. **Referenzen** — Branchenpassende Partner-Referenzen

## Preisliste 2026

| Kategorie | Preis |
|-----------|-------|
| Strategic Consulting | €150/h |
| Digital Growth & AI | €130/h |
| Creative Design | €105/h |
| Project Management | €105/h |
| Copywriting | €105/h |
| Content Engine (Retainer) | €4.500/Monat |
| Full-Service Partner (Retainer) | €12.000/Monat |
| AI Audit | €3.500 einmalig |
| AI Setup | €8.000–€15.000 einmalig |

## Tests

```bash
npm test
```

Test-Szenarien:
- Strategy Foundation für B2B (€10-20k)
- Full-Service Retainer (€12k/Monat)
- Brand + Marketing Kombi (Italienisch)
- AI Audit für Bestandskunden (€3.500)
