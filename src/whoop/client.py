import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

TOKENS_PATH = os.path.join(os.path.dirname(__file__), "../../.tokens")
BASE_URL = "https://api.prod.whoop.com/developer/v2"


def load_tokens():
    with open(TOKENS_PATH) as f:
        return json.load(f)


def get_headers():
    tokens = load_tokens()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def get_profile():
    response = requests.get(f"{BASE_URL}/user/profile/basic", headers=get_headers())
    return response.json()


def get_recovery(limit=10):
    response = requests.get(f"{BASE_URL}/recovery", headers=get_headers(), params={"limit": limit})
    return response.json()


def get_sleep(limit=10):
    response = requests.get(f"{BASE_URL}/activity/sleep", headers=get_headers(), params={"limit": limit})
    return response.json()


def get_workouts(limit=10):
    response = requests.get(f"{BASE_URL}/activity/workout", headers=get_headers(), params={"limit": limit})
    return response.json()


if __name__ == "__main__":
    print("Fetching your Whoop profile...\n")
    profile = get_profile()
    print(json.dumps(profile, indent=2))

    print("\nFetching your last 10 recovery scores...\n")
    recovery = get_recovery(limit=10)
    print(json.dumps(recovery, indent=2))
