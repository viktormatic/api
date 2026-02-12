# n8n Workflow Setup — Angebot Auto-Generator

## Voraussetzungen

1. **n8n Instanz**: https://marketingzukunvt.app.n8n.cloud
2. **API Credentials** eingerichtet in n8n:
   - ClickUp API Token
   - Google Docs OAuth2
   - Anthropic API Key

## Einrichtung

### 1. Workflow importieren

1. Öffne n8n: https://marketingzukunvt.app.n8n.cloud
2. Gehe zu **Workflows** → **Import from File**
3. Wähle `workflow-angebot.json` aus diesem Ordner
4. Der Workflow "Angebot Auto-Generator" wird erstellt

### 2. Credentials konfigurieren

Ersetze die Platzhalter-IDs in allen Nodes:

#### ClickUp API
- Gehe zu **Settings** → **Credentials** → **New Credential**
- Typ: **ClickUp API**
- API Token: `pk_...` (aus `.env`)
- Ersetze `CLICKUP_CREDENTIAL_ID` in allen ClickUp-Nodes

#### Google Docs OAuth2
- Typ: **Google Docs OAuth2 API**
- Client ID & Secret aus Google Cloud Console
- Scopes: `https://www.googleapis.com/auth/documents`, `https://www.googleapis.com/auth/drive.file`
- Ersetze `GOOGLE_CREDENTIAL_ID` im "Create Google Doc" Node

#### Anthropic API
- Typ: **Anthropic API** (über @n8n/n8n-nodes-langchain)
- API Key: `sk-ant-...` (aus `.env`)
- Ersetze `ANTHROPIC_CREDENTIAL_ID` im "Generate Proposal" Node

### 3. ClickUp Webhook einrichten

#### Option A: ClickUp Native Webhook (empfohlen)
1. Gehe zu ClickUp → **Settings** → **Integrations** → **Webhooks**
2. Erstelle einen neuen Webhook:
   - **URL**: `https://marketingzukunvt.app.n8n.cloud/webhook/angebot-trigger`
   - **Events**: `taskStatusUpdated`
   - **Space/Folder**: Deals & Sales / Angebote (List ID: 54419064)

#### Option B: n8n Polling
Falls Webhooks nicht verfügbar sind, kann der Trigger-Node durch einen
ClickUp Trigger Node ersetzt werden, der regelmäßig nach Tasks mit Status "TO DO" pollt.

### 4. Workflow aktivieren

1. Öffne den Workflow
2. Klicke auf **Active** (Toggle oben rechts)
3. Der Workflow wartet nun auf eingehende Webhooks

## Workflow-Ablauf

```
[Webhook] → [ClickUp: Get Task] → [Code: Parse Fields] → [IF: Valid?]
  ↓ (valid)                                                    ↓ (invalid)
[Claude: Generate] → [Code: Assemble] → [Google Docs: Create]  [ClickUp: NEEDS INPUT]
  → [ClickUp: Update Status] → [ClickUp: Add Comment]
```

## Error Handling

### Bei fehlenden Pflichtfeldern
- Task-Status wird auf "NEEDS INPUT" gesetzt
- Kommentar mit fehlenden Feldern wird hinzugefügt

### Bei AI-Generierungsfehler
- Workflow kann manuell erneut ausgeführt werden
- Bei wiederholtem Fehler: Task-Status auf "BLOCKED" setzen

### Bei Google Docs Fehler
- Prüfe Google OAuth2 Credentials
- Prüfe Ordner-Berechtigungen (Service Account muss Zugriff haben)

## Test

1. Erstelle einen Test-Task in der Angebots-Liste
2. Fülle alle Custom Fields aus
3. Setze Status auf "TO DO"
4. Beobachte den Workflow in n8n → **Executions**
5. Prüfe das erstellte Google Doc

## Monitoring

- **n8n Executions**: Alle Workflow-Ausführungen mit Logs
- **ClickUp Comments**: Automatische Kommentare bei Erfolg/Fehler
- **Notification Email**: vm@zukunvt.com erhält Fehler-Benachrichtigungen

## Kontakt

- **ClickUp-Berater**: Pierre Becher (pierre@neworkflow.co)
- **System-Verantwortlich**: Viktor Matic (vm@zukunvt.com)
