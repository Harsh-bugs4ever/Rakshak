# Rakshak

One app, two modes: **the first minutes** after you witness a road accident, and
**the long road after** your own family is in one.

Built for the Build It track on an open-source AWS stack running entirely
locally — SAM CLI, LocalStack, DynamoDB, OpenSearch and Cedar. No AWS account
needed.

---

## Day 1 status — backend complete

| Piece | State |
|---|---|
| SAM template, 4 functions + 4 tables | done — `template.yaml` |
| DynamoDB tables + idempotent seeding | done — `scripts/bootstrap.py` |
| Seed content (4 protocols, 4 stages, 15 FAQs, 10 resources) | done — `data/` |
| `GET /emergency/protocols` · `/numbers` · `/good-samaritan` | done |
| `GET /aftermath/steps` · `/faqs` (topic + free-text search) | done |
| `GET /resources` (type, state, city, text, distance sort) | done |
| `GET /health` | done |
| Cedar-style authorization | done — `policies/rakshak.cedar`, `src/common/authz.py` |
| Test suite | done — `tests/` |
| Strands agents, `/ai/*` endpoints | Day 2 |
| OpenSearch-backed search | Day 2 (same response shape; `meta.source` flips) |

---

## Run it

### 1. Dependencies

```bash
pip install -r requirements-dev.txt
```

### 2. Start LocalStack

```bash
docker run -d -p 4566:4566 -e SERVICES=dynamodb,opensearch localstack/localstack
```

### 3. Create and seed the tables

```bash
python scripts/bootstrap.py
```

Idempotent — rerun any time. Useful flags:

```bash
python scripts/bootstrap.py --drop           # recreate from scratch
python scripts/bootstrap.py --validate-only  # check data/*.json, touch nothing
python scripts/bootstrap.py --skip-seed      # tables only
```

### 4. Serve the API

```bash
sam local start-api --port 3000
```

```bash
curl "http://localhost:3000/health"
curl "http://localhost:3000/emergency/protocols?scenario=not_breathing"
curl "http://localhost:3000/aftermath/faqs?q=police%20refusing%20fir"
curl "http://localhost:3000/resources?type=hospital&lat=12.97&lon=77.59"
```

---

## Tests

```bash
pytest                        # unit tests, no Docker needed
pytest --cov                  # with coverage
pytest -m integration         # requires LocalStack + a bootstrapped stack
```

Unit tests run against **moto**, so they need no network, no Docker and no
LocalStack — they work on hackathon wifi. The integration tests skip themselves
automatically when LocalStack is not listening on 4566.

What the suite deliberately covers:

- **Content, not just code.** `tests/test_seed_data.py` fails if a protocol
  loses its "call 112" step, grows past five steps, or a hospital loses its
  coordinates. The content is the product.
- **The `null` query string.** API Gateway sends `queryStringParameters: null`,
  not `{}` — the single most common serverless crash.
- **Decimal from DynamoDB.** Every number comes back as `Decimal`; unhandled,
  `json.dumps` turns a trauma centre into a 500.
- **Degraded states.** Empty tables, missing tables, half-bootstrapped stacks
  and database-down all return a usable envelope, never a stack trace. The
  static routes (`/numbers`, `/good-samaritan`) are tested *with the database
  down*, because that is exactly when someone needs the number to dial.
- **Authorization edges.** Header casing, unknown roles degrading to anonymous,
  and a Cedar `Deny` with empty `reasons` meaning "no policy matched".
- **Geo edges.** Null Island, antipodal points, NaN, out-of-range, and records
  with no coordinates at all.

---

## Layout

```
data/            Seed content — the actual product
docs/            API spec with full request/response bodies
design/          Emergency tab UI spec + working mobile mockup
policies/        Cedar policies
scripts/         bootstrap.py — create tables, validate and seed
src/common/      Envelope, params, authz, store, geo, schema
src/handlers/    One Lambda entry point per route group
tests/           Unit tests (moto) + integration tests (LocalStack)
tools/           make_pdf.py — build guide PDF
template.yaml    SAM stack
```

## Design notes

**One response envelope.** Every endpoint returns
`{ok, data, error, meta}` — including failures. The frontend has one shape to
handle, which is what lets the Emergency tab fall back to bundled offline
content instead of a blank screen.

**Static content never touches the database.** Emergency numbers and Good
Samaritan rights are served from memory. If DynamoDB is down at 2am, the
bystander still gets the number to dial.

**Scans are correct here.** These are reference tables of 4–15 rows that change
only when an admin edits content. Anything cleverer would be complexity without
a payoff.

**Search is swappable.** Day 1 ranks FAQs with a scorer weighted
question 3× / tags 2× / answer 1× — deliberately mirroring the OpenSearch query
in `docs/api-spec.md`, so Day 2 can swap the engine without reordering results
under the UI. `meta.source` tells you which engine answered.
