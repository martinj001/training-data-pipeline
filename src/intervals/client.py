import os
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://intervals.icu/api/v1"
API_KEY = os.getenv("INTERVALS_API_KEY")
ATHLETE_ID = os.getenv("INTERVALS_ATHLETE_ID")


def intervals_get(endpoint, params=None):
    url = f"{BASE_URL}/athlete/{ATHLETE_ID}/{endpoint}"
    r = requests.get(url, auth=("API_KEY", API_KEY), params=params)
    r.raise_for_status()
    return r.json()


def fetch_activities(oldest=None, newest=None, limit=500):
    params = {"limit": limit}
    if oldest:
        params["oldest"] = oldest
    if newest:
        params["newest"] = newest
    return intervals_get("activities", params=params)
