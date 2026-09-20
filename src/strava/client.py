import os
import json
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv

load_dotenv()

TOKENS_PATH = os.path.join(os.path.dirname(__file__), "../../.strava_tokens")
BASE_URL = "https://www.strava.com/api/v3"
TOKEN_URL = "https://www.strava.com/oauth/token"
REQUEST_TIMEOUT = 30

# Retries transient connection resets/timeouts (same pattern used for the Whoop
# API) with exponential backoff instead of crashing the sync.
_session = requests.Session()
_session.mount("https://", HTTPAdapter(max_retries=Retry(
    total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504],
)))


def load_tokens():
    with open(TOKENS_PATH) as f:
        return json.load(f)


def save_tokens(tokens):
    with open(TOKENS_PATH, "w") as f:
        json.dump(tokens, f)


def refresh_access_token():
    tokens = load_tokens()
    response = _session.post(TOKEN_URL, data={
        "grant_type": "refresh_token",
        "refresh_token": tokens["refresh_token"],
        "client_id": os.getenv("STRAVA_CLIENT_ID"),
        "client_secret": os.getenv("STRAVA_CLIENT_SECRET"),
    }, timeout=REQUEST_TIMEOUT)
    new_tokens = response.json()
    if "access_token" not in new_tokens:
        raise RuntimeError(f"Token refresh failed: {new_tokens}")
    # Strava issues a new refresh_token on every refresh -- save the full
    # response (not just the access_token) or the next refresh will fail.
    save_tokens(new_tokens)
    print("Access token refreshed.")
    return new_tokens


def get_headers():
    tokens = load_tokens()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def strava_get(endpoint, params=None):
    response = _session.get(f"{BASE_URL}{endpoint}", headers=get_headers(), params=params, timeout=REQUEST_TIMEOUT)
    if response.status_code == 401:
        refresh_access_token()
        response = _session.get(f"{BASE_URL}{endpoint}", headers=get_headers(), params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    if not response.content:
        return []
    return response.json()


def fetch_activities(after=None, before=None, per_page=200):
    """Fetch all activities in [after, before] (epoch seconds), paginated.

    after/before are epoch seconds, not ISO dates -- Strava's API convention
    differs from Intervals.icu's (which took plain YYYY-MM-DD strings).
    """
    activities = []
    page = 1
    while True:
        params = {"per_page": per_page, "page": page}
        if after is not None:
            params["after"] = after
        if before is not None:
            params["before"] = before

        batch = strava_get("/athlete/activities", params=params)
        activities.extend(batch)
        if len(batch) < per_page:
            break
        page += 1

    return activities
