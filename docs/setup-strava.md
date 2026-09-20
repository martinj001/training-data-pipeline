# Setting up Strava API access

Follow these steps once to let the pipeline pull activities directly from Strava.

## 1. Register a personal API application

1. Go to <https://www.strava.com/settings/api> (log in to Strava if prompted).
2. Fill in the form:
   - **Application Name**: anything, e.g. `training-data-pipeline`
   - **Category**: `Training`
   - **Club**: leave blank
   - **Website**: anything, e.g. your GitHub repo URL
   - **Authorization Callback Domain**: `localhost`
3. Submit. Strava shows you a **Client ID** and **Client Secret** — keep this page open,
   you'll need both in the next step.

This creates a private app that only you authorize, for reading your own data. It's the
standard way to use Strava's API for a personal project.

## 2. Add credentials to `.env`

In the repo's `.env` file (copy from `.env.example` if you don't have one yet), add:

```
STRAVA_CLIENT_ID=your_client_id_here
STRAVA_CLIENT_SECRET=your_client_secret_here
STRAVA_REDIRECT_URI=http://localhost:8001/callback
```

`.env` is git-ignored — these values never get committed.

## 3. Run the one-time login

```
python src/strava/auth.py
```

This opens a Strava login/consent page in your browser. Approve access — a tiny local
web server catches the response and saves your tokens to `.strava_tokens` (also
git-ignored). You only need to do this once; after that, `src/strava/client.py`
refreshes the access token automatically as needed.

## 4. Run a sync

```
python sync.py strava
```

First run pulls your full activity history from Strava. After that, `python sync.py all`
(or `python sync.py strava`) does an incremental sync.
