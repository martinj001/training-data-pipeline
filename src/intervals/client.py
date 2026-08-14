import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://intervals.icu/api/v1"
API_KEY = os.getenv("INTERVALS_API_KEY")
ATHLETE_ID = os.getenv("INTERVALS_ATHLETE_ID")
REQUEST_TIMEOUT = 30

# Retries transient connection resets/timeouts (seen against both the Whoop
# and Intervals.icu APIs) with exponential backoff instead of crashing the sync.
_session = requests.Session()
_session.mount("https://", HTTPAdapter(max_retries=Retry(
    total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504],
)))


def intervals_get(endpoint, params=None):
    url = f"{BASE_URL}/athlete/{ATHLETE_ID}/{endpoint}"
    r = _session.get(url, auth=("API_KEY", API_KEY), params=params, timeout=REQUEST_TIMEOUT)
    r.raise_for_status()
    return r.json()


def fetch_activities(oldest=None, newest=None, limit=500):
    params = {"limit": limit}
    if oldest:
        params["oldest"] = oldest
    if newest:
        params["newest"] = newest
    return intervals_get("activities", params=params)
