# Forecast Data Pipeline

Collects current weather for Tehran from the [Open-Meteo API](https://open-meteo.com/) on a schedule, stores it as JSON, and serves analysis (temperature, wind, summaries) over a FastAPI backend with a small dashboard frontend.

## How data collection works

Collection is handled by an **in-app scheduler** (`scheduler.py`) — no cron needed. When the API starts, `WeatherScheduler` runs as an asyncio background task inside the FastAPI process: it fetches a snapshot immediately, then every `FETCH_INTERVAL_MINUTES` (default 60), appending each record to the JSON data file.

Scheduler endpoints:

- `GET /health` — API liveness + whether the scheduler is running
- `GET /scheduler/status` — run counts, failures, last run/success time, last error
- `POST /scheduler/collect-now` — trigger a collection immediately

A one-off manual collection is still possible with `python fetch_weather.py`.

## Admin panel

The API serves an admin panel on a custom URL, configured in `admin_config.json` (default `/wx-admin`, e.g. `http://localhost:8342/wx-admin`). Credentials also live in that file — no database in this version:

```json
{
  "admin_path": "/wx-admin",
  "username": "admin",
  "password_sha256": "<sha256 hex of the password>",
  "session_hours": 8
}
```

Default login is `admin` / `admin123`. **Change it before deploying**: pick a new password, generate its hash with `python -c "import hashlib; print(hashlib.sha256(b'yourpassword').hexdigest())"`, and put it in `admin_config.json`. Changing `admin_path` moves the whole panel to a different URL.

From the panel an admin can:

- See scheduler status (runs, failures, last success/error) and collected-data stats
- Change the collection location (latitude/longitude) and interval; changes apply immediately and persist to `data/app_settings.json`
- Trigger an immediate collection
- View the full report in the browser (HTML) or download it as PDF
- Download the complete dataset as JSON or CSV

The full report (`{admin_path}/report`) includes collection status, weather summaries over the last 6/24/72/168 records, and the latest records table.

## Configuration (environment variables)

| Variable | Default | Description |
|---|---|---|
| `WEATHER_LAT` | `35.685017` | Latitude (Tehran) |
| `WEATHER_LON` | `51.389693` | Longitude (Tehran) |
| `FETCH_INTERVAL_MINUTES` | `60` | Minutes between collections |
| `DATA_FILE` | `data/forecast_data_tehran.json` | Where records are stored |

## Running

With Docker:

```bash
docker compose up --build
# API on http://localhost:8342, frontend on http://localhost:8038
```

Locally:

```bash
pip install -r requirements.txt
uvicorn apis:app --port 8000
```

`main.py` is a local demo that prints a summary of the collected data.

## Project layout

- `apis.py` — FastAPI app; starts/stops the scheduler via lifespan
- `scheduler.py` — periodic in-process weather collection
- `fetch_weather.py` — Open-Meteo client + one-shot collection
- `analyse.py` — analytics over the most recent records
- `data_json_manager.py` — JSON file storage with ids/timestamps
- `data_type_convertor.py` — pandas DataFrame conversion
- `config.py` — settings from env vars, with runtime overrides persisted to JSON
- `admin_routes.py` / `admin_auth.py` / `admin_ui/` — admin panel (custom URL, JSON-based credentials)
- `report.py` — full report generation (HTML and PDF)
- `admin_config.json` — admin credentials and panel URL
- `frontend/` — static public dashboard (nginx)
