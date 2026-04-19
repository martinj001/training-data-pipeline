import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

TOKENS_PATH = os.path.join(os.path.dirname(__file__), "../../.tokens")
BASE_URL = "https://api.prod.whoop.com/developer/v2"
TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"


def load_tokens():
    with open(TOKENS_PATH) as f:
        return json.load(f)


def save_tokens(tokens):
    with open(TOKENS_PATH, "w") as f:
        json.dump(tokens, f)


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
    print("Access token refreshed.")
    return new_tokens


def get_headers():
    tokens = load_tokens()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def whoop_get(endpoint, params=None):
    response = requests.get(f"{BASE_URL}{endpoint}", headers=get_headers(), params=params)
    if response.status_code == 401:
        refresh_access_token()
        response = requests.get(f"{BASE_URL}{endpoint}", headers=get_headers(), params=params)
    return response.json()


def get_profile():
    return whoop_get("/user/profile/basic")


def get_recovery(limit=10):
    return whoop_get("/recovery", params={"limit": limit})


def get_sleep(limit=10):
    return whoop_get("/activity/sleep", params={"limit": limit})


def get_workouts(limit=10):
    return whoop_get("/activity/workout", params={"limit": limit})


if __name__ == "__main__":
    print("Fetching your Whoop profile...\n")
    profile = get_profile()
    print(json.dumps(profile, indent=2))

    print("\nFetching your last 10 recovery scores...\n")
    recovery = get_recovery(limit=10)
    print(json.dumps(recovery, indent=2))
