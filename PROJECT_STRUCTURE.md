# Project Structure

Every directory in the repo, what belongs in it, and what is still a stub.

Legend: **done** = implemented and tested · **stub** = contract defined, Day 2 work

```
Rakshak/
├── .github/workflows/ci.yml      done   pytest + seed validation on every push
├── docker-compose.yml            done   LocalStack (DynamoDB + OpenSearch)
├── template.yaml                 done   SAM stack: functions, tables, routes
├── pyproject.toml                done   pytest + coverage config
├── requirements.txt              done   Lambda runtime deps
├── requirements-dev.txt          done   test deps (moto, pytest)
│
├── data/                         done   The seed content - this is the product
│   ├── emergency_protocols.json         4 scenarios
│   ├── aftermath_steps.json             4 stages
│   ├── faqs.json                        15 Q&A pairs
│   └── resources.json                   10 hospitals / legal aid / NGOs / schemes
│
├── policies/rakshak.cedar        done   Authorization policy source of truth
│
├── infra/
│   ├── localstack/init-aws.sh    done   Auto-bootstrap on container start
│   └── opensearch/                      Index mappings, applied by scripts/
│       ├── resources.mapping.json       geo_point + keyword facets
│       └── aftermath_topics.mapping.json
│
├── scripts/
│   ├── bootstrap.py              done   Create tables, validate, seed
│   ├── index_opensearch.py       stub   Push DynamoDB content into OpenSearch
│   └── smoke_test.py             done   Hit every endpoint, print pass/fail
│
├── src/
│   ├── common/                   done   Shared building blocks
│   │   ├── config.py                    Env-driven table names, endpoints
│   │   ├── errors.py                    Typed API errors -> HTTP status
│   │   ├── response.py                  The {ok, data, error, meta} envelope
│   │   ├── http.py                      @api_handler: timing, CORS, error mapping
│   │   ├── params.py                    Query parsing and validation
│   │   ├── authz.py                     Cedar evaluation
│   │   ├── store.py                     DynamoDB access
│   │   ├── geo.py                       Haversine, coordinate extraction
│   │   ├── schema.py                    Seed-data validation
│   │   ├── static_content.py            Numbers + rights, served from memory
│   │   └── search.py             stub   OpenSearch client and query builders
│   │
│   ├── handlers/                        One Lambda entry point per route group
│   │   ├── emergency.py          done   /emergency/protocols, /numbers, /good-samaritan
│   │   ├── aftermath.py          done   /aftermath/steps, /faqs
│   │   ├── resources.py          done   /resources
│   │   ├── health.py             done   /health
│   │   └── ai.py                 stub   /ai/emergency, /ai/aftermath (501 until Day 2)
│   │
│   └── agents/                   stub   Strands Agents layer
│       ├── prompts.py                   System prompts - the safety contract
│       ├── emergency_agent.py           EmergencyGuideAgent
│       ├── aftermath_agent.py           AftermathGuideAgent
│       └── tools/                       Tools the agents may call
│           ├── emergency_tools.py       done (thin wrappers over the store)
│           └── aftermath_tools.py       done
│
├── frontend/                     stub   Next.js app, mobile-first
│   ├── package.json / tsconfig.json / next.config.mjs
│   ├── app/
│   │   ├── layout.tsx                   Shell, theme, tab bar
│   │   ├── page.tsx                     Redirects to /emergency
│   │   ├── emergency/page.tsx           Emergency tab
│   │   └── aftermath/page.tsx           Aftermath tab
│   ├── components/
│   │   ├── emergency/                   CallButtons, TriageQuestion, StepCards
│   │   ├── aftermath/                   StageCard, FaqSearch, ResourceList
│   │   └── shared/                      TabBar, AskBar, ErrorBoundary
│   ├── lib/
│   │   ├── types.ts              done   Types generated from the API envelope
│   │   ├── api.ts                done   Typed fetch client with offline fallback
│   │   └── offline.ts            done   Bundled protocols for the no-network case
│   └── public/offline-protocols.json    Shipped in the bundle, never fetched
│
├── tests/                        done   435 tests, 99% coverage
│   ├── conftest.py                      moto fixtures, event builders
│   ├── test_params.py / test_authz.py / test_geo.py / test_response.py
│   ├── test_emergency_handler.py / test_aftermath_handler.py
│   ├── test_resources_handler.py / test_store_and_health.py
│   ├── test_seed_data.py                Content tests - the product itself
│   ├── test_edge_cases.py               Database down, pagination, bad records
│   ├── test_ai_handler.py               Pins the 501 contract until Day 2
│   └── test_integration_localstack.py   Skipped unless LocalStack is up
│
├── docs/
│   ├── api-spec.md               done   Full request/response bodies
│   └── architecture.md           done   How the pieces fit, and why
│
├── design/
│   ├── emergency-tab.md          done   Mobile UI spec
│   └── emergency-mockup.html     done   Working mockup
│
└── tools/make_pdf.py             done   Build guide PDF generator
```

## Why the stubs are shaped this way

**`ai.py` returns a real 501 envelope, not a crash.** The route exists, is wired
into `template.yaml`, and returns `{ok: false, error: {code: "NOT_IMPLEMENTED"}}`.
The frontend can integrate against it today and will keep working unchanged when
the agents land. `tests/test_ai_handler.py` pins that contract.

**Agent tools are implemented; agent reasoning is not.** The tools are thin
wrappers over `store.py` - they were nearly free and make the Day 2 work purely
about prompts and orchestration.

**`search.py` mirrors the Day 1 scorer.** The OpenSearch queries use the same
question-3x / tags-2x / answer-1x weighting as `aftermath.py`, so switching
engines does not reorder results under the UI. `meta.source` reports which one
answered.
