# Forecast Data Pipeline

## Data sources and third parties

- **Weather data**: [Open-Meteo](https://open-meteo.com/) — free, open-source weather API, no API key required. We call one endpoint: `https://api.open-meteo.com/v1/forecast` (current weather + humidity, apparent temperature, precipitation, pressure). This is the only external service the backend talks to.
- **World map geometry**: [Natural Earth](https://www.naturalearthdata.com/) (public domain), converted once at build time via the `world-atlas` npm package into a static SVG path — no map/tile service is used at runtime.
- **Persian font**: [Vazirmatn](https://github.com/rastikerdar/vazirmatn) (SIL OFL license), bundled locally in `frontend/fonts/`.

Everything else (API, frontend, admin panel, PWA assets) is self-hosted; the public site makes no runtime requests to any third-party host.

Collects current weather for cities around the world from the [Open-Meteo API](https://open-meteo.com/) on a schedule, stores every snapshot as JSON, and serves per-city analytics (temperature, wind, summaries) over a FastAPI backend with an installable PWA frontend.

## How data collection works

Collection is handled by an **in-app scheduler** (`scheduler.py`) — no cron needed. When the API starts, `WeatherScheduler` runs as an asyncio background task inside the FastAPI process: every `FETCH_INTERVAL_MINUTES` (default 60) it fetches a snapshot for **every enabled city** and appends it to that city's data file (`data/weather_<city>.json`).

Cities are managed from the admin panel and stored in `data/cities.json`. The default seed is Tehran, pointing at the pre-existing data file so old data is kept.

## Public site

Served by nginx (`frontend/`):

- **Home** (`index.html`) — intro about the project (admin-editable), tracked-city cards, what we measure
- **Cities** (`cities.html`) — a **live world map** (static Natural Earth SVG, no external tiles) with every tracked city as a dot — hover for latest conditions, click to open the dashboard — plus the city cards
- **City dashboard** (`city.html?city=<id>`) — summary, trends charts, records, temperature/wind analytics, calm periods and recent raw data
- **Compare** (`compare.html`) — pick 2-4 cities and see their metrics side by side plus overlaid temperature/wind charts
- **Info** (`info.html`) — about the project, mission, data description, developers and contact (all admin-editable)

The site supports **light and dark themes**: the default follows the visitor's system preference and a navbar toggle overrides it (persisted per device).

The site is a **PWA**: it ships a web manifest, icons and a service worker (`sw.js`), so visitors can install it on their phone ("Add to Home Screen"). The app shell works offline and the last seen data is served when the network is gone.

The site is **bilingual (Farsi/English)**: Farsi is the default (with full RTL layout and Persian dates); visitors switch languages with the navbar toggle and the choice is remembered. UI strings live in `frontend/i18n.js`; the admin-managed content is stored per language. A **"Buy me a coffee" donate button** is shown in the navbar; its target URL is set from the admin panel (Site Content section). The info page credits the developers (Mehrshad Asadi, Sepehr Sedigh) with LinkedIn links.

## What we collect per snapshot

Each snapshot stores the classic fields — temperature, wind speed, wind direction, day/night flag and weather code — plus, when the API provides them, **humidity, apparent ("feels like") temperature, precipitation and surface pressure**. These extra fields were added later: existing keys are never renamed, so records collected before the fields existed remain fully readable and every metric that uses a new field simply ignores records that lack it. No migration of old data is needed.

## Charts and records

- Each city dashboard shows **time-series charts** (temperature and wind over the selected window), drawn as dependency-free inline SVG that reads left-to-right even on the RTL Farsi site.
- Each city has an all-time **Records & Milestones** section: hottest, coldest and windiest readings, longest calm streak, and (once such data exists) wettest and most-humid readings — computed over the city's entire collected history.

## Public API

- `GET /cities` — tracked cities with latest snapshot
- `GET /cities/{id}` — city detail
- `GET /cities/{id}/data?limit=` — raw records, newest first
- `GET /cities/{id}/summary?period=` — includes optional humidity/feels-like/precipitation/pressure when present
- `GET /cities/{id}/records?threshold=` — all-time records and milestones
- `GET /cities/{id}/temperature/average|range|rate-of-change|delta`
- `GET /cities/{id}/wind/average-speed|peak-speed|dominant-direction|direction-variability|calm-periods`
- `GET /content` — admin-managed site content
- `GET /health`, `GET /scheduler/status`

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

- **Manage cities**: add any city in the world (name, country, coordinates), enable/disable, delete, or collect a snapshot immediately (per city or all at once)
- **Manage site content**: every text block on the public main page and info page (site name, tagline, intro, about, mission, data description, contact, footer), separately for Farsi and English, plus the donate (Buy me a coffee) URL
- Change the global collection interval; applies immediately and persists to `data/app_settings.json`
- View per-city full reports in the browser (HTML) or download them as PDF
- Download each city's dataset as JSON or CSV

The full report (`{admin_path}/report?city=<id>`) includes collection status, weather summaries over the last 6/24/72/168 records, and the latest records table.

## Configuration (environment variables)

| Variable | Default | Description |
|---|---|---|
| `FETCH_INTERVAL_MINUTES` | `60` | Minutes between collection runs |
| `WEATHER_LAT` / `WEATHER_LON` | Tehran | Seed coordinates for the default city |
| `DATA_FILE` | `data/forecast_data_tehran.json` | Seed data file for the default city |
| `CITIES_FILE` | `data/cities.json` | City registry |
| `CONTENT_FILE` | `data/site_content.json` | Admin-managed site content |
| `SETTINGS_FILE` | `data/app_settings.json` | Persisted runtime settings |
| `ADMIN_CONFIG_FILE` | `admin_config.json` | Admin credentials and panel URL |

## Running

With Docker:

```bash
docker compose up --build
# API + admin on http://localhost:8342, public site on http://localhost:8038
```

Locally:

```bash
pip install -r requirements.txt
uvicorn apis:app --port 8000
```

`main.py` is a local demo that prints a summary of the collected data per city.

## Project layout

- `apis.py` — FastAPI app; public city-scoped endpoints; starts/stops the scheduler via lifespan
- `scheduler.py` — periodic in-process collection for all enabled cities
- `cities.py` — city registry (JSON-backed)
- `content.py` — admin-editable site content (JSON-backed)
- `fetch_weather.py` — Open-Meteo client + one-shot collection
- `analyse.py` — analytics over the most recent records
- `data_json_manager.py` — JSON file storage with ids/timestamps
- `data_type_convertor.py` — pandas DataFrame conversion
- `config.py` — settings from env vars, with runtime overrides persisted to JSON
- `admin_routes.py` / `admin_auth.py` / `admin_ui/` — admin panel (custom URL, JSON-based credentials)
- `report.py` — per-city full report generation (HTML and PDF)
- `admin_config.json` — admin credentials and panel URL
- `frontend/` — public site + PWA (nginx)
