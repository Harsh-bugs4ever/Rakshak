# Rakshak

One app for the first minutes after a road accident and the family support that
comes after. Next.js frontend, Python Lambda handlers, DynamoDB, optional
OpenSearch, and optional local Strands/Ollama FAQ matching.

## Run the complete demo without Docker

Use Python 3.12 or 3.13 and Node.js 22.6 or newer.

```powershell
py -3.13 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-dev.txt
.venv/Scripts/python.exe scripts/dev_api.py
```

In a second terminal:

```powershell
cd frontend
npm install
npm run build
npm start
```

Open [Rakshak](http://localhost:3001). The demo API listens on loopback port 3000
and runs the real handlers against seeded in-memory moto DynamoDB. Its data
resets on exit. This is a development convenience, not a replacement for testing
SAM and LocalStack. Checklist progress remains in the browser.

Use `npm run dev` for editing; service-worker caching is production-only.

## What works

- Emergency calls, native location sharing with SMS fallback, triage guidance,
  and separate warnings. Reference protocols render before the API responds.
- Four aftermath checklists with device-local progress, FAQ search, and resource
  filters. Reference data is bundled for backend outages.
- Both `/ai/*` routes return grounded answers, session IDs, actions and
  disclaimers. Emergency routing is deterministic; unknown questions redirect
  to the visible triage choices and 112. Aftermath answers cite retrieved FAQs.
- Optional Strands uses a local model to select a retrieved FAQ. Visible answers
  come from reference records, not generated medical or legal prose. Model
  failures fall back to reference retrieval. No conversation history is stored.
- Optional OpenSearch handles FAQ and resource queries. Search failures fall
  back to DynamoDB. Resource filtering supports nationwide and non-city-specific
  entries, and missing coordinates do not remove entries.
- A production build creates a versioned service worker that saves both screens
  and static assets. Once the saved-for-offline status appears, either screen
  can reopen offline. AI requests and external API responses are not cached.

The bundled directory is sample reference content, not live availability.

## Local AWS stack and OpenSearch

```powershell
docker compose --profile search up -d
.venv/Scripts/python.exe scripts/bootstrap.py
$env:AWS_ENDPOINT_URL = 'http://localhost:4566'
$env:AWS_ACCESS_KEY_ID = 'test'
$env:AWS_SECRET_ACCESS_KEY = 'test'
$env:OPENSEARCH_ENDPOINT = 'http://localhost:9200'
.venv/Scripts/python.exe scripts/index_opensearch.py
sam build
sam local start-api --port 3000 --parameter-overrides SearchEndpoint=http://host.docker.internal:9200
```

The Docker search service is loopback-only and has authentication disabled for
local development. SAM containers reach services through `host.docker.internal`.
Leave `SearchEndpoint` empty to use DynamoDB search alone.

Indexing upserts records by ID. `--recreate` deletes and rebuilds indexes, and is
required when mappings change or removed records must disappear. `--dry-run`
validates document shaping without writing to OpenSearch.

## Optional local Strands

Install the extra dependencies and configure a locally installed Ollama model
that supports tools and structured output:

```powershell
.venv/Scripts/python.exe -m pip install -r requirements-ai.txt
$env:AI_PROVIDER = 'ollama'
$env:OLLAMA_HOST = 'http://localhost:11434'
$env:OLLAMA_MODEL_ID = 'your-installed-model-name'
.venv/Scripts/python.exe scripts/dev_api.py
```

The model call has an eight-second deadline. Default `AI_PROVIDER=retrieval`
needs no model or cloud account. SAM's default package includes only the base
requirements and runs reference mode; an AI-enabled Lambda package must also
include `requirements-ai.txt` dependencies and the Ollama environment values.
Emergency triage never waits for model inference.

Implementation references: [Strands Ollama provider](https://strandsagents.com/docs/api/python/strands.models.ollama/),
[Strands tools](https://strandsagents.com/docs/user-guide/concepts/tools/),
[OpenSearch Python client](https://docs.opensearch.org/latest/clients/python-low-level/).

## Verification

```powershell
.venv/Scripts/python.exe -m pytest
.venv/Scripts/python.exe scripts/bootstrap.py --validate-only
cd frontend
npm test
npm run typecheck
npm run lint
npm run build
```

LocalStack integration tests skip when Docker is unavailable. Unit tests cover
request validation, grounded answers, model failure, search outages, content,
authorization, filtering, coordinates, and serialization.

See [frontend/README.md](frontend/README.md) for the UI checklist.
