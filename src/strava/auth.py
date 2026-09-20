import os
import json
import secrets
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv
import requests

load_dotenv()

CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
REDIRECT_URI = os.getenv("STRAVA_REDIRECT_URI")

AUTH_URL = "https://www.strava.com/oauth/authorize"
TOKEN_URL = "https://www.strava.com/oauth/token"

# activity:read_all is required to read private activities, not just public ones.
SCOPES = ["activity:read_all"]

TOKENS_PATH = os.path.join(os.path.dirname(__file__), "../../.strava_tokens")

auth_code = None


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        print(f"Callback received: {self.path}")
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        auth_code = params.get("code", [None])[0]
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"<h1>Authentication successful! You can close this tab.</h1>")

    def log_message(self, format, *args):
        pass


def get_access_token():
    state = secrets.token_urlsafe(16)
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "approval_prompt": "auto",
        "scope": ",".join(SCOPES),
        "state": state,
    }
    url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"

    print("Opening Strava login in your browser...")
    webbrowser.open(url)

    print("Waiting for authentication...")
    # Port must match STRAVA_REDIRECT_URI and the app's Authorization Callback Domain.
    server = HTTPServer(("localhost", 8001), CallbackHandler)
    server.handle_request()

    if not auth_code:
        print("Authentication failed — no code received.")
        return None

    response = requests.post(TOKEN_URL, data={
        "grant_type": "authorization_code",
        "code": auth_code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    })

    print(f"Token response status: {response.status_code}")
    tokens = response.json()

    if "access_token" not in tokens:
        print(f"Token exchange failed: {tokens}")
        return None

    # Strava's response includes access_token, refresh_token, and expires_at —
    # save the whole thing. Every future refresh also returns a NEW refresh_token
    # that must overwrite this one (Strava rotates it), handled in client.py.
    with open(TOKENS_PATH, "w") as f:
        json.dump(tokens, f)

    print(f"Authentication successful! Tokens saved to {TOKENS_PATH}")
    return tokens


if __name__ == "__main__":
    get_access_token()
