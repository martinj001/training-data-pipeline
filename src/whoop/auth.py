import os
import secrets
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv
import requests

load_dotenv()

CLIENT_ID = os.getenv("WHOOP_CLIENT_ID")
CLIENT_SECRET = os.getenv("WHOOP_CLIENT_SECRET")
REDIRECT_URI = os.getenv("WHOOP_REDIRECT_URI")

AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"

SCOPES = [
    "read:recovery",
    "read:cycles",
    "read:sleep",
    "read:workout",
    "read:profile",
    "read:body_measurement",
    "offline",
]

auth_code = None


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        print(f"Callback received: {self.path}")
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        print(f"Params: {params}")
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
        "scope": " ".join(SCOPES),
        "state": state,
    }
    url = f"{AUTH_URL}?{urllib.parse.urlencode(params)}"

    print("Opening Whoop login in your browser...")
    webbrowser.open(url)

    print("Waiting for authentication...")
    server = HTTPServer(("localhost", 8000), CallbackHandler)
    server.handle_request()

    if not auth_code:
        print("Authentication failed — no code received.")
        return None

    response = requests.post(TOKEN_URL, data={
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    })

    import json
    print(f"Token response status: {response.status_code}")
    print(f"Token response: {response.text}")

    tokens = response.json()

    tokens_path = os.path.join(os.path.dirname(__file__), "../../.tokens")
    with open(tokens_path, "w") as f:
        json.dump(tokens, f)

    print("Authentication successful! Tokens saved to .tokens")
    return tokens


if __name__ == "__main__":
    get_access_token()
