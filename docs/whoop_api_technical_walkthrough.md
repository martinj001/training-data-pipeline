# Whoop API — Technical Walkthrough
*Session: 2026-04-19 | Project: Training Data Pipeline*

---

## Overview: Two Files Working Together

The Whoop API connection is split across two files:

- **`src/whoop/auth.py`** — run once to authenticate and save tokens
- **`src/whoop/client.py`** — used every time you want to fetch data

---

## `auth.py` — The One-Time Setup

### Step 1 — Load credentials from `.env`
```python
CLIENT_ID = os.getenv("WHOOP_CLIENT_ID")
CLIENT_SECRET = os.getenv("WHOOP_CLIENT_SECRET")
```
`load_dotenv()` reads your `.env` file and puts those values into memory at runtime. The real credentials are never hardcoded in the script.

### Step 2 — Build the login URL and open it
```python
state = secrets.token_urlsafe(16)   # random security string
params = { "client_id": ..., "scope": ..., "state": state, ... }
webbrowser.open(url)
```
Builds a URL pointing at Whoop's login page with your app's details baked in. `state` is a random string Whoop requires to prevent attackers from faking the callback.

### Step 3 — Catch the callback
```python
server = HTTPServer(("localhost", 8000), CallbackHandler)
server.handle_request()
```
Spins up a tiny temporary web server on your machine at `localhost:8000`. After you log in, Whoop redirects your browser to `http://localhost:8000/callback?code=ABC123...` — the mini server catches that request, grabs the `code` parameter, and shuts down.

### Step 4 — Exchange the code for tokens
```python
response = requests.post(TOKEN_URL, data={"code": auth_code, ...})
json.dump(tokens, f)  # saves to .tokens file
```
Sends the code + Client Secret to Whoop's token URL. In return we get:
- **`access_token`** — valid for ~1 hour, used in every API call
- **`refresh_token`** — used to get new access tokens without logging in again

Both are saved locally to `.tokens` (gitignored — never pushed to GitHub).

---

## `client.py` — Every API Call After That

### Step 1 — Load tokens and credentials
```python
TOKENS_PATH = os.path.join(os.path.dirname(__file__), "../../.tokens")

def load_tokens():
    with open(TOKENS_PATH) as f:
        return json.load(f)
```
`load_tokens()` reads `.tokens` from the project root — the file `auth.py` saved earlier. `os.path.dirname(__file__)` means "find the path relative to wherever `client.py` lives", so it works regardless of where you run the script from.

### Step 2 — Build the auth header
```python
def get_headers():
    tokens = load_tokens()
    return {"Authorization": f"Bearer {tokens['access_token']}"}
```
Every request to Whoop must include this header. Like showing your ID card — Whoop sees the token, confirms it's valid, and hands over your data. `Bearer` is just the standard format for sending an OAuth token in a header.

### Step 3 — The central request function
```python
def whoop_get(endpoint, params=None):
    response = requests.get(f"{BASE_URL}{endpoint}", headers=get_headers(), params=params)
    if response.status_code == 401:
        refresh_access_token()
        response = requests.get(f"{BASE_URL}{endpoint}", headers=get_headers(), params=params)
    return response.json()
```
All data calls go through `whoop_get()`. It sends the request and checks the response status code:
- **200** — success, return the data
- **401** — token expired, automatically refresh and retry once

A **status code** is a number Whoop sends back with every response to say how things went. 200 = OK, 401 = Unauthorized (token problem), 404 = Not Found.

### Step 4 — Automatic token refresh
```python
def refresh_access_token():
    tokens = load_tokens()
    response = requests.post(TOKEN_URL, data={
        "grant_type": "refresh_token",
        "refresh_token": tokens["refresh_token"],
        "client_id": os.getenv("WHOOP_CLIENT_ID"),
        "client_secret": os.getenv("WHOOP_CLIENT_SECRET"),
    })
    new_tokens = response.json()
    save_tokens(new_tokens)
```
When the access token expires (~1 hour), this function uses the `refresh_token` to get a new one from Whoop — without opening a browser or asking you to log in again. The new tokens overwrite `.tokens` on disk. This happens automatically inside `whoop_get()` whenever a 401 is received.

### Step 5 — Data fetch functions
```python
def get_recovery(limit=10):
    return whoop_get("/recovery", params={"limit": limit})
```
Each function is a thin wrapper around `whoop_get()`. `limit=10` tells Whoop to return 10 records, newest first. The `params` dictionary gets added to the URL automatically as `?limit=10`.

### The `limit` parameter and pagination
The response includes a `next_token`:
```json
"next_token": "eyIkIjoib0AxIiwibyI6MTB9"
```
Passing that token back in a follow-up request fetches the *next* 10 records. This pattern — called **pagination** — is how APIs handle large datasets without sending everything at once.

---

## The Full Flow in Plain English

```
auth.py (run once):
  You → Whoop login page → Whoop issues a one-time code →
  Code + Secret exchanged for tokens → tokens saved to .tokens

client.py (run anytime):
  Load token from .tokens → attach to request header →
  Send request to Whoop API
    → 200 OK: return data
    → 401 Expired: use refresh_token to get new access_token →
      save new tokens → retry request → return data
```

---

## Available Endpoints (v2 API)

| Method | Endpoint | Data |
|---|---|---|
| GET | `/user/profile/basic` | Name, email, user ID |
| GET | `/user/measurement/body` | Height, weight, max heart rate |
| GET | `/recovery` | Recovery score, HRV, RHR, SpO2, skin temp |
| GET | `/activity/sleep` | Sleep duration, start/end times |
| GET | `/activity/workout` | Activity type, strain, heart rate |
| GET | `/cycle` | Daily physiological cycles and strain |

Base URL: `https://api.prod.whoop.com/developer/v2`

---

## Key Terms

- **OAuth 2.0** — The industry-standard login flow used here. You log in once; the app gets tokens to act on your behalf.
- **Access Token** — Short-lived credential (~1 hour) sent with every API request
- **Refresh Token** — Long-lived credential used to get a new access token without logging in again
- **Bearer Token** — The format for sending the access token in a request header: `Authorization: Bearer <token>`
- **Scope** — Permissions granted to the app (e.g. `read:recovery`, `read:sleep`)
- **Pagination** — API pattern for returning large datasets in chunks, using a `next_token` to fetch the next page
- **`.env`** — Local file storing credentials, never committed to GitHub
- **`.tokens`** — Local file storing OAuth tokens, never committed to GitHub
- **Status Code** — Number in every API response indicating success or failure (200 = OK, 401 = Unauthorized, 404 = Not Found)
- **`whoop_get()`** — Central request function that handles token refresh automatically on 401 responses
