# Fees Tracker System web demo

A browser-based public demo of the school fees tracker. The demo uses
synthetic records, is read-only, and stores its database separately from the
desktop app.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe webapp.py
```

Open <http://127.0.0.1:5000>.

## Deploy to Render

This branch contains the Render Blueprint in `render.yaml`.

1. In Render, choose **New > Blueprint**.
2. Connect this repository and select the `fees-tracker-system` branch.
3. Apply the Blueprint. Render will build the Flask app and provide its URL.

The public deployment is configured with `DEMO_MODE=true` and
`READ_ONLY_DEMO=true`. It uses sample data only. Its database is temporary
and may reset when the service restarts; do not use this configuration for
real student records.

## Project contents

- `webapp.py` — Flask routes and demo configuration
- `templates/` and `static/` — browser interface
- `backend/` and `database/` — fee operations and isolated web database
- `render.yaml` — Render deployment configuration

The portfolio site from the `main` branch remains unchanged.
