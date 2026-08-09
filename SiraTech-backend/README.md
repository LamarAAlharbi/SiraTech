# SiraTech Backend — Guide API

Backend for **SiraTech**, an AI-powered cultural tourism *Guide* for Saudi Arabia.

**Scope:** This service ONLY covers Guide functionality — Saudi locations, landmarks,
and historical-image metadata, plus search. It intentionally does **not** include
itinerary planning, pricing, packages, hotels, transportation, or booking.

---

## 1. Requirements

- Python 3.10+
- pip

## 2. Setup (exact commands)

```bash
# 1. Clone / cd into the project
cd SiraTech-backend

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create your local .env from the example
cp .env.example .env
```

`.env` is git-ignored. Never commit it. All config (host, port, CORS origins) is
read from environment variables — nothing is hard-coded in the source.

## 3. Run the server

```bash
python run.py
```

The API will start at `http://localhost:5000` (or whatever `HOST`/`PORT` you set in `.env`).

Quick check:

```bash
curl http://localhost:5000/health
```

## 4. Run tests

```bash
pytest
```

## 5. CORS

Allowed frontend origins are configured via `CORS_ORIGINS` in `.env` (comma-separated).
Default allows `http://localhost:3000` and `http://127.0.0.1:3000` for local frontend dev.

## 6. AI Guide Chat (Gemini)

`POST /api/guide/chat` answers visitor questions about a single landmark using
Gemini, grounded in Google Search when possible. To use it:

1. Get a key at https://aistudio.google.com/apikey
2. Put it in `.env`: `GEMINI_API_KEY=your-key-here`
3. `pip install -r requirements.txt` (installs `google-genai`)

If the key or package is missing, or Gemini fails/times out, the endpoint
returns a clean `503 AI_SERVICE_UNAVAILABLE` JSON error instead of crashing —
the rest of the API keeps working either way.

---

## Response Format Conventions

Every endpoint in this API follows one of four consistent JSON shapes:

| Kind | Shape | Example |
|------|-------|---------|
| **List** | `{"count": <int>, "results": [...]}` | `GET /api/v1/landmarks` |
| **Single resource** | the resource object itself | `GET /api/v1/landmarks/<id>` |
| **Action / operation** | an operation-specific object (documented per-endpoint below) | `POST /api/guide/chat`, `POST /api/tts`, `POST /api/gamification/discover` |
| **Error** | `{"error": {"code", "message", "details"}}` — always this shape, on every 4xx/5xx | any failed request |

Rules that hold across the whole API:

- **Content-Type** is always `application/json` (via Flask's `jsonify`) — `/api/vision/analyze`
  is the only endpoint that *accepts* `multipart/form-data`, but it still *returns* JSON, not a file.
- **Errors never leak internals.** Every error — expected (`404`, `400`) or unexpected (`500`) —
  is normalized by `app/errors.py` into the same `{"error": {...}}` shape. No raw Python
  traceback, SQL error, or HTML error page is ever returned to a client. See
  `test_health.py`/every route's own test file for the 400/404 cases exercised.
- **Upstream AI failures (Gemini, TTS) always come back as a clean `503 AI_SERVICE_UNAVAILABLE`**
  with a human-readable `details.reason` — never a raw SDK exception, and never a credential.
- **List endpoints are never `null`.** An empty result set is always `{"count": 0, "results": []}`,
  not `null` or a missing key — safe to `.map()`/`.length` on directly in the frontend.

## API Endpoints

All responses are JSON. All errors follow this shape:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Landmark 'lm-xyz' was not found.",
    "details": {}
  }
}
```

### Health

| Method | Path      | Description          |
|--------|-----------|-----------------------|
| GET    | `/health` | Service health check |

### Locations

| Method | Path                            | Description                                   |
|--------|----------------------------------|------------------------------------------------|
| GET    | `/api/v1/locations`              | List all locations. Optional `?region=` filter |
| GET    | `/api/v1/locations/regions`      | List distinct regions                          |
| GET    | `/api/v1/locations/<id>`         | Get one location by id                         |

### Landmarks

| Method | Path                                  | Description                                                                 |
|--------|-----------------------------------------|-------------------------------------------------------------------------------|
| GET    | `/api/v1/landmarks`                     | List landmarks. Optional `?location_id=`, `?category=`, `?unesco=true|false` |
| GET    | `/api/v1/landmarks/categories`          | List distinct landmark categories                                            |
| GET    | `/api/v1/landmarks/<id>`                | Get one landmark by id                                                       |

### Images (historical image metadata)

| Method | Path                          | Description                                  |
|--------|--------------------------------|-----------------------------------------------|
| GET    | `/api/v1/images`               | List images. Optional `?landmark_id=` filter |
| GET    | `/api/v1/images/<id>`          | Get one image by id                          |

### Guide (search + combined lookups)

| Method | Path                                   | Description                                                        |
|--------|------------------------------------------|-----------------------------------------------------------------------|
| GET    | `/api/v1/guide/search?q=<text>&limit=`   | Free-text search across locations and landmarks (name/region/desc)   |
| GET    | `/api/v1/guide/landmarks/<landmark_id>`  | A landmark enriched with its location and all of its images          |
| GET    | `/api/v1/guide/locations/<location_id>`  | A location enriched with all of its landmarks                        |

### AI Guide Chat

| Method | Path                | Description                                                    |
|--------|-----------------------|--------------------------------------------------------------------|
| POST   | `/api/guide/chat`    | Ask a Gemini-powered question about one specific landmark          |

**Request body:**

```json
{
  "landmark_id": "lm-hegra",
  "user_message": "When was this site built and by whom?",
  "language": "en",
  "context": [
    {"role": "user", "content": "Tell me about this place."},
    {"role": "assistant", "content": "It's an ancient Nabataean site..."}
  ]
}
```

- `landmark_id` (required) — must match an existing landmark, or you'll get a 404.
- `user_message` (required) — up to 2000 characters.
- `language` (required) — `"ar"` or `"en"`. The reply is always in this language.
- `context` (optional) — up to 8 prior `{role: "user"|"assistant", content}` turns.

**Response body:**

```json
{
  "answer": "Hegra was carved by the Nabataeans starting in the 1st century BCE...",
  "short_answer_for_speech": "Hegra was carved by the Nabataeans over two thousand years ago.",
  "language": "en",
  "landmark_id": "lm-hegra",
  "grounding": {
    "sources": [{"title": "UNESCO World Heritage - Hegra", "uri": "https://whc.unesco.org/en/list/1293/"}],
    "search_queries": ["Hegra Nabataean history"]
  }
}
```

`grounding` is `null` when the model didn't use search grounding for that particular answer.

The model is explicitly instructed to: stay only on the selected landmark (politely
declining itinerary/pricing/booking/transportation questions and redirecting back
to the site), never invent historical facts, say so when it's not confident, and
prefer search-grounded claims for factual details.

### Hidden Gems: AI Landmark Recognition (Gemini Vision)

| Method | Path                   | Description                                                        |
|--------|--------------------------|-------------------------------------------------------------------|
| POST   | `/api/vision/analyze`   | Identify a visible landmark/architectural feature in a photo       |

**Request:** `multipart/form-data`

| Field         | Required | Notes                                                                 |
|---------------|----------|------------------------------------------------------------------------|
| `image`       | yes      | jpeg/png/webp, size-limited by `VISION_MAX_IMAGE_BYTES` (default 8MB) |
| `language`    | yes      | `"ar"` or `"en"`                                                       |
| `landmark_id` | no       | A landmark the visitor believes they're at — used only as an unverified hint |
| `latitude`    | no*      | Visitor's reported latitude — narrows match candidates                |
| `longitude`   | no*      | Visitor's reported longitude — must be given together with `latitude` |

**Response body:**

```json
{
  "identified_name": "Hegra",
  "category": "UNESCO Heritage Site",
  "description": "A Nabataean rock-cut tomb complex with monumental carved facades...",
  "possible_landmark_id": "lm-hegra",
  "confidence": "high",
  "uncertain": false,
  "language": "en"
}
```

- `identified_name` / `category` / `description` — the model's read of the photo. Always in
  the requested `language`.
- `possible_landmark_id` — only set when the model's answer can be cross-referenced against
  SiraTech's own verified data (via `landmark_id`/`latitude`/`longitude` hints or a name
  match). **This is a recognition step only** — once you have a `possible_landmark_id`, call
  `GET /api/v1/guide/landmarks/<possible_landmark_id>` to fetch the verified historical
  record (curated description, era, UNESCO status, images) for that landmark. The vision
  model's own `description` is a best-effort visual read and should be treated as
  provisional, not as the verified record.
- `confidence` — `"high" | "medium" | "low"`, the model's own self-reported certainty.
- `uncertain` — `true` whenever the model isn't reasonably confident. When `true`,
  `identified_name` is always `null` — the model is instructed (and the service
  double-checks) to never guess a specific name it isn't sure of.

Like `/api/guide/chat`, this endpoint never leaks the Gemini API key, and any
Gemini/SDK failure comes back as a clean `503 AI_SERVICE_UNAVAILABLE` rather than a raw
error. All Gemini-vision code is isolated in `app/services/vision_service.py`, which is
fully mockable — see `tests/test_vision.py`.

---

### See the Past: Historical Images

**Product rule: historical photographs are never generated with GenAI.** These endpoints
only ever serve curated/verified records from `app/data/historical_images.json`. Until the
content team sources and rights-clears real archival images, that file holds **sample
placeholder records only** — every record is a stand-in for the eventual real data, not a
real photograph, and every response makes that explicit.

| Method | Path                                        | Description                                             |
|--------|-----------------------------------------------|-----------------------------------------------------------|
| GET    | `/api/history/landmarks/<landmark_id>`       | All curated historical-image records for a landmark. Optional `?tag=` filter |
| GET    | `/api/history/images/<image_id>`             | A single curated historical-image record                |

`?tag=` accepts one of: `architecture`, `fashion`, `daily_life`, `event`.

**Record shape:**

```json
{
  "id": "hist-hegra-1",
  "landmark_id": "lm-hegra",
  "title": "[SAMPLE] Early expedition photograph, Hegra — placeholder",
  "image_path": "static/history-samples/hist-hegra-1.jpg",
  "image_url": null,
  "year_or_period": "Unverified — placeholder only",
  "source": "Sample placeholder record — no archival source has been verified yet",
  "source_url": null,
  "description": "Placeholder entry reserved for a future verified early-expedition-era photograph...",
  "tags": ["architecture"],
  "rights": {
    "license": "Unknown",
    "usage_note": "Sample data only. Not cleared for any use. Do not publish or treat as authentic..."
  },
  "is_sample": true
}
```

- `image_path` — a local prototype path (no actual file is bundled yet); `image_url` is
  used instead once a real, hosted, rights-cleared image exists. Exactly one of the two is
  expected to be populated for a real (non-sample) record.
- `source` / `source_url` — every current sample record intentionally leaves `source_url`
  as `null` and `source` as an explicit "sample placeholder" string. **No historical source
  URL is ever fabricated** — when the real archive/citation isn't known, the field stays
  empty rather than pointing at a made-up link.
- `rights` — `license` + `usage_note`. Sample records are always `"Unknown"` / "not cleared
  for any use" — they exist to prototype the shape of the data, not to be published.
- `is_sample` — `true` for every record until the content team replaces it with a real,
  verified one. `GET /api/history/landmarks/<id>` also adds a response-level
  `sample_data: "all" | "some" | "none"` (plus `sample_data_notice`, `null` when `"none"`) so
  the frontend can surface a "sample data" label without inspecting every record — including
  the case where a landmark's images are a mix of verified and placeholder records. An empty
  result set (no images yet for that landmark) reports `"none"`.

**Adding real images:** once the content team has a rights-cleared image and a verified
citation, replace the corresponding entry in `app/data/historical_images.json` — set
`is_sample: false`, fill in the real `year_or_period`, `source`, `source_url`, and `rights`,
and point `image_url` (or `image_path`, if self-hosted) at the actual asset. No code changes
are needed; `history_service.py` reads whatever's in that file.

**Hidden Gems → See the Past handoff:** `POST /api/vision/analyze` returns
`possible_landmark_id` when it can confidently identify a landmark. The frontend can then
call `GET /api/history/landmarks/<possible_landmark_id>` to show that landmark's curated
historical images alongside the recognition result — separately from
`GET /api/v1/guide/landmarks/<possible_landmark_id>`, which gives the general curated
description/era/UNESCO info and present-day photos.

### SiraTech TTS (Text-to-Speech)

| Method | Path        | Description                          |
|--------|-------------|----------------------------------------|
| POST   | `/api/tts`  | Synthesize speech audio from text     |

**Two providers are implemented**, selected via `TTS_PROVIDER` in `.env`. All vendor-specific
code lives in `app/services/tts_service.py`, isolated the same way `gemini_service.py` and
`vision_service.py` are — routes never talk to a TTS vendor directly.

- `TTS_PROVIDER=gemini` — **real, natural-sounding speech**, in Arabic and English, via the
  Gemini TTS model (`GEMINI_TTS_MODEL`, default `gemini-2.5-flash-preview-tts`). Reuses the
  same `GEMINI_API_KEY` already required for `/api/guide/chat` and `/api/vision/analyze` — no
  second credential to provision. Voice is a prebuilt Gemini voice name (e.g. `Kore`, `Puck`,
  `Zephyr`); set `TTS_DEFAULT_VOICE_AR`/`TTS_DEFAULT_VOICE_EN` or pass `voice` per-request. The
  model returns raw PCM audio, which this service wraps into a standard WAV file before
  base64-encoding it in the response — the frontend doesn't need to know that detail.
- `TTS_PROVIDER=none` (default) — the **dev fallback**: a short, valid, *silent* WAV clip,
  with no credentials or network call required. Useful for offline development and for the
  test suite, which never makes a real TTS API call.

**Request body:**

```json
{
  "text": "Hegra was Saudi Arabia's first UNESCO World Heritage Site.",
  "language": "en",
  "voice": "narrator-1"
}
```

- `text` (required) — up to `TTS_MAX_TEXT_LENGTH` characters (default 1000, set in `.env`).
- `language` (required) — `"ar"` or `"en"`.
- `voice` (optional) — a vendor-specific voice name/id (a prebuilt Gemini voice name, when
  `TTS_PROVIDER=gemini`). Falls back to `TTS_DEFAULT_VOICE_AR`/`TTS_DEFAULT_VOICE_EN` when
  omitted.

**Response body — and how the frontend should use it:**

```json
{
  "audio_base64": "UklGRi...",
  "mime_type": "audio/wav",
  "provider": "none",
  "voice": "dev-silent-en",
  "language": "en",
  "fallback": true
}
```

The response is JSON, not a raw audio stream, so metadata (`provider`, `voice`, `fallback`)
can travel alongside the audio in one call. `audio_base64` is the base64-encoded audio file
itself; `mime_type` says how to interpret it. To play it in a browser:

```js
const res = await fetch("/api/tts", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ text: "...", language: "en" }),
});
const { audio_base64, mime_type } = await res.json();
new Audio(`data:${mime_type};base64,${audio_base64}`).play();
```

For longer clips, decode to a `Blob` (via `atob` + `Uint8Array`) and `URL.createObjectURL`
instead of a data URL, to avoid building a huge string.

- `fallback: true` means no real TTS provider is configured (or `TTS_PROVIDER=none`) — the
  audio is a short silent clip, not real speech. With `TTS_PROVIDER=gemini` and a valid
  `GEMINI_API_KEY`, `fallback` is `false`, `provider` is `"gemini"`, and the audio is real
  synthesized speech.
- Credentials (`GEMINI_API_KEY`, `TTS_API_KEY`, etc.) are read from `.env` inside
  `tts_service.py` and never appear in any response, log line, or error message surfaced to
  the client — a provider failure (missing key, upstream error, malformed audio) comes back
  as a clean `503 AI_SERVICE_UNAVAILABLE`, same pattern as `/api/guide/chat` and
  `/api/vision/analyze`.

**Adding another provider:** add its credentials to `Config`/`.env.example`, write a
`_synthesize_<provider>(text, language, voice)` function in `tts_service.py` (same return
shape as `_synthesize_fallback`), register it in `_PROVIDERS`, and set `TTS_PROVIDER`
accordingly. No route or validation code needs to change.

### Gamification: XP, discoveries & badges

| Method | Path                                 | Description                                              |
|--------|-----------------------------------------|--------------------------------------------------------------|
| GET    | `/api/gamification/profile/<user_id>`   | Get a user's XP, discovery counts, and unlocked badges       |
| POST   | `/api/gamification/discover`            | Record a discovery; awards XP and returns newly unlocked badges |

**`POST /api/gamification/discover` request body:**

```json
{
  "user_id": "visitor-123",
  "type": "landmark",
  "item_id": "lm-diriyah",
  "location_id": "loc-riyadh"
}
```

- `user_id` (required) — any client-chosen identifier for the visitor.
- `type` (required) — one of `landmark`, `hidden_gem`, `historical_image`, `story`.
- `item_id` (required) — id of the thing discovered. For `landmark` and
  `historical_image`, this must match a real record (404 if not) and its
  location is looked up automatically. For `hidden_gem` and `story` — which
  aren't necessarily tied to the seed data — any non-empty id is accepted.
- `location_id` (optional) — only used for `hidden_gem`/`story` discoveries,
  to credit progress toward the Saudi Heritage Explorer badge.

**Response body:**

```json
{
  "already_discovered": false,
  "xp_awarded": 10,
  "newly_unlocked_badges": [
    {"code": "heritage_explorer", "name": "Heritage Explorer", "description": "Discovered 3 landmarks."}
  ],
  "profile": {
    "user_id": "visitor-123",
    "total_xp": 30,
    "discovered_landmarks": {"count": 3, "item_ids": ["lm-diriyah", "lm-hegra", "lm-albalad"]},
    "hidden_gems": {"count": 0, "item_ids": []},
    "historical_images_viewed": {"count": 0, "item_ids": []},
    "stories_listened": {"count": 0, "item_ids": []},
    "distinct_locations_explored": ["loc-alula", "loc-jeddah", "loc-riyadh"],
    "badges": [{"code": "heritage_explorer", "name": "Heritage Explorer", "description": "Discovered 3 landmarks."}]
  }
}
```

The same discovery (same `user_id` + `type` + `item_id`) is never rewarded twice —
repeating the call above returns `already_discovered: true` and `xp_awarded: 0`,
with the profile totals unchanged.

**Badges:**

| Badge | Unlocks when |
|-------|--------------|
| Heritage Explorer | 3 distinct landmarks discovered |
| Hidden Gem Hunter | 3 distinct hidden gems identified |
| Time Traveler | 3 distinct historical images viewed |
| Story Listener | 3 distinct stories listened to |
| Saudi Heritage Explorer | Landmarks discovered across 4+ distinct SiraTech locations |

**Storage:** a small SQLite prototype store
(`app/services/gamification_repository.py`), file path set by
`GAMIFICATION_DB_PATH` (defaults to `instance/gamification.sqlite3`,
git-ignored, auto-created). All XP values and badge rules live in
`app/services/gamification_service.py`, which only talks to the repository
through a handful of plain methods (`record_discovery`, `count_by_type`,
`unlock_badge`, ...) — swapping in a production database later means
rewriting just that one repository module.

---

## Frontend Integration Notes: End-to-End Discovery Flow

This is the flow the mobile/web frontend drives end-to-end, and the exact
SiraTech endpoints that back each step:

```
1. Map selects "Historic Jeddah"
     GET /api/v1/guide/locations/loc-jeddah
     -> location + all of its landmarks (e.g. lm-albalad, Al-Balad Historic District)

2. Guide details
     GET /api/v1/guide/landmarks/lm-albalad
     -> landmark + location + present-day photos, everything needed for the detail screen

3. Gemini Guide (AI Q&A about the landmark)
     POST /api/guide/chat  { landmark_id, user_message, language, context? }
     -> { answer, short_answer_for_speech, grounding }

4. TTS (narrate the answer)
     POST /api/tts  { text: answer.short_answer_for_speech, language }
     -> { audio_base64, mime_type } — decode and play; see the TTS section above
        for the exact browser snippet

5. Camera -> Vision analysis ("Hidden Gems")
     POST /api/vision/analyze  (multipart/form-data: image, language, optional landmark_id/lat/lon)
     -> { identified_name, possible_landmark_id, confidence, uncertain }

6. Historical database / "See the Past"
     GET /api/history/landmarks/<possible_landmark_id || lm-albalad>
     -> curated historical-image records (sample/placeholder until the content
        team adds verified archival images — see `is_sample`/`sample_data_notice`)

7. XP / badge
     POST /api/gamification/discover  { user_id, type: "landmark", item_id: "lm-albalad" }
     POST /api/gamification/discover  { user_id, type: "historical_image", item_id: <hist id from step 6> }
     -> { xp_awarded, newly_unlocked_badges, profile }
     GET  /api/gamification/profile/<user_id>  -> full XP/badge state, any time
```

Notes for whoever wires this up on the frontend:

- **Steps 3 and 5 need `GEMINI_API_KEY`.** Until it's set in `.env`, both return a clean
  `503 AI_SERVICE_UNAVAILABLE` — build the UI to handle that (e.g. "AI guide unavailable,
  try again shortly") rather than assuming they always succeed.
- **Step 5's output feeds step 6**: when `/api/vision/analyze` returns a non-null
  `possible_landmark_id`, use *that* id for the "See the Past" and gamification calls
  instead of whatever landmark the visitor thought they were at — it's been cross-checked
  against SiraTech's own data.
- **Step 7 is safe to call optimistically.** Recording the same discovery twice (e.g. the
  visitor reopens the landmark) is a no-op server-side (`already_discovered: true`,
  `xp_awarded: 0`) — no need to track "have I already sent this?" client-side.
- **`user_id`** is entirely client-chosen (a device id, a session id, an account id —
  whatever the frontend already has). The gamification store doesn't manage auth or
  identity itself.
- This full sequence — `guide → chat → tts → vision → history → gamification`, using
  `loc-jeddah`/`lm-albalad` exactly as above — is what `tests/test_flow_integration.py`
  exercises end-to-end, so it's a good reference implementation to read alongside this
  section.

## Verification

Confirmed on this review pass (and enforced going forward by
`tests/test_flow_integration.py`):

- **No API key or credential is ever exposed.** `GEMINI_API_KEY`, `TTS_API_KEY`,
  `TTS_API_REGION`, and `API_KEY` are read only from server-side config inside
  `gemini_service.py` / `vision_service.py` / `tts_service.py`, are never placed in a
  returned dict, and every upstream failure is normalized to a generic
  `503 AI_SERVICE_UNAVAILABLE` with a human-readable (non-secret) `details.reason` —
  never a raw SDK exception that could embed a key or request URL. `.env` itself is
  git-ignored (see `.gitignore`).
- **No itinerary, pricing, packages, hotels/accommodation, transportation, or booking
  feature exists anywhere in this service.** There is no route, service, or data file
  for any of them. The AI Guide Chat's system prompt (`gemini_service.py`) additionally
  instructs Gemini to decline those topics if a visitor asks, and redirect back to the
  selected landmark — a defensive second layer, not the only one. This is checked
  statically (route table has no matching endpoints) and dynamically (no response body
  in the full flow contains those words) by `test_flow_integration.py`.



```
app/
  __init__.py       # app factory: config, CORS, blueprints, error handlers
  config.py         # all settings read from .env
  errors.py         # APIError + JSON error handlers
  data/             # seed JSON: locations, landmarks, images, historical_images (sample data)
  services/         # business logic (no Flask imports) — data_loader, locations,
                     # landmarks, images, guide (search + combined lookups),
                     # gemini_service (chat), vision_service + vision_analyze_service
                     # (Hidden Gems landmark recognition), history_service (See the Past),
                     # tts_service (text-to-speech, swappable provider),
                     # gamification_service + gamification_repository (XP/badges, SQLite prototype)
  routes/           # thin Flask blueprints — validate input, call services
  utils/            # query-param validation helpers
tests/              # pytest suite covering every endpoint + error case
run.py              # loads .env, starts the dev server
requirements.txt
.env.example
```

**Why this split:** routes never touch the JSON data directly, and services never
import Flask. That means the two of you can work on routes and data/logic in
parallel without stepping on each other, and it's easy to swap the JSON files
for a real database later without touching the route layer.

## Adding more seed data

Edit the JSON files under `app/data/`. Each `landmark` needs a valid `location_id`
that exists in `locations.json`, and each `image` needs a valid `landmark_id` that
exists in `landmarks.json` — the service layer will 404 cleanly if a reference is
missing or wrong.

---

## Quick Reference: Commands to Run & Test the Backend

```bash
# --- one-time setup ---
cd SiraTech-backend
python3 -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                   # then fill in GEMINI_API_KEY etc. if you have one

# --- run it ---
python run.py                          # serves on http://localhost:5000
curl http://localhost:5000/health      # sanity check in another terminal

# --- test it ---
pytest                                 # full suite: every endpoint, error case, and
                                        # the end-to-end flow in test_flow_integration.py
pytest -v                              # same, with per-test names
pytest tests/test_flow_integration.py  # just the Map->Guide->Chat->TTS->Vision->
                                        # History->Gamification flow
pytest tests/test_gamification.py      # just XP/badges
pytest -k cors                         # just the CORS allowlist checks

# --- manually exercise the required flow (server must be running) ---
curl http://localhost:5000/api/v1/guide/locations/loc-jeddah
curl http://localhost:5000/api/v1/guide/landmarks/lm-albalad
curl -X POST http://localhost:5000/api/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Welcome to Al-Balad.", "language": "en"}'
curl http://localhost:5000/api/history/landmarks/lm-albalad
curl -X POST http://localhost:5000/api/gamification/discover \
  -H "Content-Type: application/json" \
  -d '{"user_id": "demo", "type": "landmark", "item_id": "lm-albalad"}'
curl http://localhost:5000/api/gamification/profile/demo
```
