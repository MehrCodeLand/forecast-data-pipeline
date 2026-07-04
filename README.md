# Forecast Data Pipeline

Collects current weather for Tehran from the [Open-Meteo API](https://open-meteo.com/) on a schedule, stores it as JSON, and serves analysis (temperature, wind, summaries) over a FastAPI backend with a small dashboard frontend.

## How data collection works

Collection is handled by an **in-app scheduler** (`scheduler.py`) — no cron needed. When the API starts, `WeatherScheduler` runs as an asyncio background task inside the FastAPI process: it fetches a snapshot immediately, then every `FETCH_INTERVAL_MINUTES` (default 60), appending each record to the JSON data file.

Scheduler endpoints:

- `GET /health` — API liveness + whether the scheduler is running
- `GET /scheduler/status` — run counts, failures, last run/success time, last error
- `POST /scheduler/collect-now` — trigger a collection immediately

A one-off manual collection is still possible with `python fetch_weather.py`.

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
- `config.py` — env-based settings
- `frontend/` — static dashboard (nginx)
