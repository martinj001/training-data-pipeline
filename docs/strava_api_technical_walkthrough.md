# Strava API — Technical Walkthrough
*Session: 2026-09-20 | Project: Training Data Pipeline*

---

## Overview: Two Files Working Together

Same shape as the Whoop integration (see `docs/whoop_api_technical_walkthrough.md`) —
Strava also uses OAuth 2.0, so most of this will look familiar:

- **`src/strava/auth.py`** — run once to authenticate and save tokens
- **`src/strava/client.py`** — used every time you want to fetch data

---

## `auth.py` — The One-Time Setup

### Step 1 — Load credentials from `.env`
```python
CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
```
Same pattern as Whoop — see `docs/setup-strava.md` for how to get these from
`strava.com/settings/api`.

### Step 2 — Build the login URL and open it
```python
params = {"client_id": ..., "scope": "activity:read_all", ...}
webbrowser.open(url)
```
`scope=activity:read_all` is important — without `_all`, Strava only shares activities
you've marked public, which would silently drop most of your real history.

### Step 3 — Catch the callback
Identical mechanism to Whoop — a tiny local web server on `localhost:8001` (a different
port than Whoop's `8000`, purely so the two don't collide if you ever run both flows
back to back) catches Strava's redirect and grabs the `code` parameter.

### Step 4 — Exchange the code for tokens
```python
response = requests.post(TOKEN_URL, data={"code": auth_code, ...})
json.dump(tokens, f)  # saves to .strava_tokens
```
Same idea as Whoop, saved to a separate file (`.strava_tokens`, not `.tokens`) so the
two integrations' tokens don't overwrite each other.

---

## `client.py` — Every API Call After That

Same four pieces as Whoop's client: `load_tokens()`/`save_tokens()`, `get_headers()`,
a central `strava_get()` that refreshes-and-retries once on a 401, and thin per-endpoint
wrapper functions. Two real differences worth knowing:

### Difference 1 — Strava rotates the refresh token
```python
def refresh_access_token():
    ...
    new_tokens = response.json()
    save_tokens(new_tokens)   # <- must save the WHOLE response
```
With Whoop, you could in principle reuse the same `refresh_token` indefinitely. Strava
issues a **new** `refresh_token` every time you refresh — if you only saved the new
`access_token` and kept the old `refresh_token`, the *next* refresh would fail. Always
persist the full response.

### Difference 2 — Pagination and dates work differently
Whoop pages through results with a `next_token` string. Strava uses plain page numbers:
```python
def fetch_activities(after=None, before=None, per_page=200):
    page = 1
    while True:
        params = {"per_page": per_page, "page": page, "after": after, "before": before}
        batch = strava_get("/athlete/activities", params=params)
        activities.extend(batch)
        if len(batch) < per_page:
            break   # short page means we've reached the end
        page += 1
```
And `after`/`before` are **epoch seconds** (seconds since 1970-01-01), not ISO date
strings like `"2026-08-25"` — a common gotcha, since most other APIs in this project
(Whoop, the old Intervals.icu one) took plain dates. `src/strava/sync.py`'s `to_epoch()`
does that conversion.

---

## The Full Flow in Plain English

```
auth.py (run once):
  You → Strava login/consent page → Strava issues a one-time code →
  Code + Secret exchanged for tokens → tokens saved to .strava_tokens

sync.py (run anytime):
  Load token → attach to request header → page through /athlete/activities
    → 200 OK: collect the page, ask for the next page if it was full
    → 401 Expired: refresh (save the NEW refresh_token too) → retry → continue
```

---

## Available Endpoints (v3 API)

| Method | Endpoint | Data |
|---|---|---|
| GET | `/athlete/activities` | List of activities (summary fields, paginated) |
| GET | `/activities/{id}` | Full detail for one activity (not used here — not needed for anything the pipeline reads today) |

Base URL: `https://www.strava.com/api/v3`

---

## Key Terms

- **`sport_type` vs `type`** — Strava has two activity-type fields. `type` is a legacy,
  coarser field (e.g. everything on a bike is `"Ride"`). `sport_type` is more specific
  (`"MountainBikeRide"`, `"VirtualRide"`, `"GravelRide"`, etc.) — the pipeline stores
  `sport_type` in the `type` column so the existing pillar-classification logic
  (originally written against Intervals.icu's vocabulary) keeps working unchanged.
- **Rate limit** — Strava allows 200 requests per 15 minutes and 2,000 per day, per
  app. A full historical backfill or daily incremental sync uses at most a handful of
  requests, well under either limit.
- **Epoch seconds** — Strava's `after`/`before` query params, unlike most dates in this
  project, count seconds since 1970-01-01 rather than using an ISO date string.
