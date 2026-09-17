# Rakshak Backend API Spec

Base URL (LocalStack + SAM local): `http://localhost:3000`

All responses are `application/json`. Every response carries a top-level envelope so
the frontend has one shape to handle:

```jsonc
{
  "ok": true,
  "data": { },          // present when ok = true
  "error": null,        // { "code": "...", "message": "..." } when ok = false
  "meta": { "source": "dynamodb", "cached": false, "took_ms": 12 }
}
```

**Auth (hackathon):** send `X-User-Role: anonymous | admin` and optional
`X-User-Id`. The Lambda builds a Cedar principal from these headers and evaluates
the policies in `policies/rakshak.cedar` before touching the data store. Anonymous
callers get every `GET`; only `admin` gets `POST`/`PUT`/`DELETE` on content.

**Error codes:** `NOT_FOUND`, `BAD_REQUEST`, `FORBIDDEN`, `UPSTREAM_ERROR`,
`RATE_LIMITED`.

---

## 1. Emergency

### `GET /emergency/protocols`

| Param | Type | Required | Notes |
|---|---|---|---|
| `scenario` | string | no | `not_breathing`, `breathing_injured`, `heavy_bleeding`, `unconscious_breathing`. Omit to list all. |

`GET /emergency/protocols?scenario=not_breathing`

```json
{
  "ok": true,
  "data": {
    "scenario_id": "not_breathing",
    "title": "Person is not breathing",
    "severity": "critical",
    "subtitle": "Every second counts. Do these in order.",
    "steps": [
      "Tap their shoulder and shout loudly. Check if they respond.",
      "Call 112 now and put the phone on speaker so your hands are free.",
      "If you are trained: push hard and fast in the centre of the chest, 100-120 pushes per minute, about 5 cm deep.",
      "Do not stop until they start breathing or the ambulance team takes over."
    ],
    "do_not": [
      "Do not give water or food.",
      "Do not shake or twist the head and neck.",
      "Do not leave them alone to go look for help - call instead."
    ],
    "tags": ["breathing", "cpr", "critical"],
    "updated_at": "2026-09-17"
  },
  "error": null,
  "meta": { "source": "dynamodb", "cached": true, "took_ms": 8 }
}
```

Without `scenario`, `data` is `{ "items": [ ...protocols ], "count": 4 }`.

**DynamoDB:** `EmergencyProtocols`, PK `scenario_id` (S). `GetItem` for the single
case, `Scan` for the list (4 items — a scan is correct here, not a smell).

### `GET /emergency/numbers`

| Param | Type | Required |
|---|---|---|
| `state` | string | no |

```json
{
  "ok": true,
  "data": {
    "state": "Karnataka",
    "ambulance": "108",
    "police": "112",
    "unified": "112",
    "note": "112 works everywhere in India and connects to police, fire and ambulance."
  },
  "error": null,
  "meta": { "source": "static", "cached": true, "took_ms": 1 }
}
```

### `GET /emergency/good-samaritan`

```json
{
  "ok": true,
  "data": {
    "title": "You are protected when you help",
    "points": [
      "You cannot be forced to reveal your name or address.",
      "You cannot be detained or made to pay for the victim's treatment.",
      "Hospitals must start emergency treatment without waiting for police formalities.",
      "If you choose to be a witness, you can be examined only once, at a time and place you pick."
    ],
    "source": "Good Samaritan guidelines, Motor Vehicles Act s.134A"
  },
  "error": null,
  "meta": { "source": "static", "cached": true, "took_ms": 1 }
}
```

---

## 2. Aftermath

### `GET /aftermath/steps`

| Param | Type | Required | Notes |
|---|---|---|---|
| `stage` | string | no | `hospital`, `police`, `insurance`, `legal`. Omit to list all four in order. |

`GET /aftermath/steps?stage=hospital`

```json
{
  "ok": true,
  "data": {
    "stage_id": "hospital",
    "order": 1,
    "title": "At Hospital",
    "subtitle": "First 48 hours. Get the paperwork right while treatment happens.",
    "checklist": [
      "Ask the hospital to register the case as an MLC (Medico-Legal Case).",
      "Note down the MLC number and the name of the treating doctor.",
      "Collect the admission summary, prescriptions and every test report.",
      "Keep every bill and receipt, including pharmacy and ambulance bills.",
      "Photograph injuries and the discharge summary on your phone as backup."
    ],
    "details": [
      "An MLC is the hospital's official record that the injury came from an accident. Insurance claims and MACT compensation both depend on it.",
      "Emergency treatment cannot be refused for lack of money, police clearance or paperwork."
    ],
    "tags": ["hospital", "mlc", "documents", "bills"]
  },
  "error": null,
  "meta": { "source": "dynamodb", "cached": false, "took_ms": 11 }
}
```

**DynamoDB:** `AftermathSteps`, PK `stage_id` (S).

### `GET /aftermath/faqs`

| Param | Type | Required | Notes |
|---|---|---|---|
| `topic` | string | no | `good_samaritan`, `hospital`, `fir`, `insurance`, `legal_aid`, `compensation` |
| `q` | string | no | Free text; routed to OpenSearch instead of DynamoDB |
| `limit` | int | no | Default 10, max 50 |

`GET /aftermath/faqs?q=police%20refusing%20fir&limit=2`

```json
{
  "ok": true,
  "data": {
    "query": "police refusing fir",
    "count": 2,
    "items": [
      {
        "faq_id": "faq_fir_delay",
        "question": "The police are refusing or delaying the FIR. What are our options?",
        "answer": "Send a written complaint by registered post to the Superintendent of Police. If that fails, a Magistrate can direct registration of the FIR under Section 156(3) CrPC. Keep proof of every attempt you made.",
        "topic": "fir",
        "tags": ["police", "delay", "escalation"],
        "score": 8.41
      },
      {
        "faq_id": "faq_fir_needed",
        "question": "Do we need an FIR for the insurance claim?",
        "answer": "Yes, for injury and death claims the FIR is essential.",
        "topic": "fir",
        "tags": ["insurance", "fir"],
        "score": 3.02
      }
    ]
  },
  "error": null,
  "meta": { "source": "opensearch", "index": "aftermath_topics", "took_ms": 24 }
}
```

**OpenSearch query** (index `aftermath_topics`):

```json
{
  "size": 10,
  "query": {
    "bool": {
      "should": [
        { "match": { "question": { "query": "police refusing fir", "boost": 3 } } },
        { "match": { "answer": { "query": "police refusing fir" } } },
        { "terms": { "tags": ["police", "fir"], "boost": 2 } }
      ],
      "filter": [ { "term": { "topic": "fir" } } ],
      "minimum_should_match": 1
    }
  }
}
```

Drop the `filter` block when `topic` is absent. With `topic` but no `q`, skip
OpenSearch entirely and use a DynamoDB GSI query on `topic`.

---

## 3. Resources

### `GET /resources`

| Param | Type | Required | Notes |
|---|---|---|---|
| `type` | string | no | `hospital`, `legal_aid`, `ngo`, `scheme` |
| `state` | string | no | Exact match; `All India` entries always included |
| `city` | string | no | |
| `q` | string | no | Free text over name, description, tags |
| `lat`, `lon` | float | no | Sort by distance when both present |
| `limit` | int | no | Default 20 |

`GET /resources?type=hospital&state=Karnataka&city=Bengaluru&lat=12.97&lon=77.59`

```json
{
  "ok": true,
  "data": {
    "count": 2,
    "items": [
      {
        "resource_id": "res_victoria_blr",
        "name": "Victoria Hospital Emergency Department",
        "type": "hospital",
        "state": "Karnataka",
        "city": "Bengaluru",
        "address": "Fort Road, Kalasipalya, Bengaluru 560002",
        "contact": { "phone": "080-26701150", "alt_phone": "112", "website": "" },
        "description": "Government tertiary hospital with a 24x7 casualty and trauma unit.",
        "hours": "24x7",
        "geo": { "lat": 12.9622, "lon": 77.5731 },
        "distance_km": 2.1,
        "tags": ["trauma", "government", "24x7", "free"]
      },
      {
        "resource_id": "res_nimhans_trauma_blr",
        "name": "NIMHANS Trauma and Emergency Care Centre",
        "type": "hospital",
        "state": "Karnataka",
        "city": "Bengaluru",
        "address": "Hosur Road, Lakkasandra, Bengaluru 560029",
        "contact": { "phone": "080-26995000", "alt_phone": "112", "website": "https://nimhans.ac.in" },
        "description": "24x7 neurotrauma and emergency care centre. Accepts medico-legal cases.",
        "hours": "24x7",
        "geo": { "lat": 12.9433, "lon": 77.5964 },
        "distance_km": 3.6,
        "tags": ["trauma", "24x7", "neuro", "mlc"]
      }
    ]
  },
  "error": null,
  "meta": { "source": "opensearch", "index": "resources", "took_ms": 31 }
}
```

**OpenSearch index mapping** (`resources`):

```json
{
  "mappings": {
    "properties": {
      "resource_id": { "type": "keyword" },
      "name":        { "type": "text", "fields": { "raw": { "type": "keyword" } } },
      "type":        { "type": "keyword" },
      "state":       { "type": "keyword" },
      "city":        { "type": "keyword" },
      "address":     { "type": "text" },
      "description": { "type": "text" },
      "hours":       { "type": "keyword" },
      "tags":        { "type": "keyword" },
      "geo":         { "type": "geo_point" }
    }
  }
}
```

---

## 4. AI assistant

### `POST /ai/emergency`

Request:

```json
{
  "message": "there is a lot of blood coming from his leg, what do I do",
  "session_id": "8d1f-anon-0d2a",
  "context": {
    "triage_answer": "yes_breathing",
    "state": "Karnataka",
    "location": { "lat": 12.9716, "lon": 77.5946 }
  }
}
```

Response:

```json
{
  "ok": true,
  "data": {
    "session_id": "8d1f-anon-0d2a",
    "reply": "Press down hard on the wound with any clean cloth and do not lift it to check. Add more cloth on top if it soaks through. Raise the leg above the level of the heart if you can. Call 112 if you have not already.",
    "steps": [
      "Press hard on the wound with a clean cloth.",
      "Do not lift the cloth - add more on top.",
      "Raise the leg above heart level.",
      "Keep pressing until the ambulance arrives."
    ],
    "protocol_id": "heavy_bleeding",
    "severity": "critical",
    "actions": [
      { "type": "call", "label": "Call 112 now", "value": "tel:112" },
      { "type": "open_protocol", "label": "Full bleeding steps", "value": "heavy_bleeding" }
    ],
    "tools_used": ["get_emergency_protocol"],
    "disclaimer": "Guidance only. Call 112 for professional help."
  },
  "error": null,
  "meta": { "source": "strands", "agent": "EmergencyGuideAgent", "took_ms": 940 }
}
```

The `steps` array is what the UI renders as cards; `reply` is the fallback prose.
Keep the agent's system prompt hard-capped at 4 short steps.

### `POST /ai/aftermath`

Request:

```json
{
  "message": "hospital wants 50000 deposit before treating my father",
  "session_id": "3ab9-anon-91cc",
  "context": { "stage": "hospital", "state": "Delhi" }
}
```

Response:

```json
{
  "ok": true,
  "data": {
    "session_id": "3ab9-anon-91cc",
    "reply": "Emergency treatment cannot be refused for lack of payment or police formalities - this applies to private hospitals too. Ask for the refusal in writing, note the time and the staff member's name, and call 112. Also ask them to register the case as an MLC.",
    "citations": [
      { "faq_id": "faq_hospital_refuse", "question": "The hospital is refusing treatment until we deposit money. What do we do?" },
      { "stage_id": "hospital", "title": "At Hospital" }
    ],
    "suggested_next": [
      { "type": "open_stage", "label": "Hospital checklist", "value": "hospital" },
      { "type": "open_resources", "label": "Legal aid in Delhi", "value": "type=legal_aid&state=Delhi" }
    ],
    "tools_used": ["answer_aftermath_faq", "get_aftermath_steps"],
    "disclaimer": "General information, not legal advice."
  },
  "error": null,
  "meta": { "source": "strands", "agent": "AftermathGuideAgent", "took_ms": 1180 }
}
```

---

## 5. Admin writes (Cedar-gated)

`PUT /emergency/protocols/{scenario_id}` and `PUT /aftermath/steps/{stage_id}`
take the same object shape as the corresponding `GET` response `data`.

With `X-User-Role: anonymous`:

```json
{
  "ok": false,
  "data": null,
  "error": {
    "code": "FORBIDDEN",
    "message": "Only admins can edit safety content.",
    "cedar": { "decision": "Deny", "reasons": [] }
  },
  "meta": { "source": "cedar", "took_ms": 3 }
}
```

Returns HTTP 403. A Cedar `Deny` with an empty `reasons` array means no policy
matched — which is the correct default for this app.

---

## 6. Local setup quick reference

```bash
# 1. LocalStack
docker run -d -p 4566:4566 -e SERVICES=dynamodb,opensearch localstack/localstack

# 2. Tables
awslocal dynamodb create-table --table-name EmergencyProtocols \
  --attribute-definitions AttributeName=scenario_id,AttributeType=S \
  --key-schema AttributeName=scenario_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

awslocal dynamodb create-table --table-name AftermathSteps \
  --attribute-definitions AttributeName=stage_id,AttributeType=S \
  --key-schema AttributeName=stage_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

awslocal dynamodb create-table --table-name FAQs \
  --attribute-definitions AttributeName=faq_id,AttributeType=S AttributeName=topic,AttributeType=S \
  --key-schema AttributeName=faq_id,KeyType=HASH \
  --global-secondary-indexes \
    'IndexName=topic-index,KeySchema=[{AttributeName=topic,KeyType=HASH}],Projection={ProjectionType=ALL}' \
  --billing-mode PAY_PER_REQUEST

awslocal dynamodb create-table --table-name Resources \
  --attribute-definitions AttributeName=resource_id,AttributeType=S \
  --key-schema AttributeName=resource_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST

# 3. Seed from data/*.json, then run the API
sam local start-api --env-vars env.json --port 3000
```
