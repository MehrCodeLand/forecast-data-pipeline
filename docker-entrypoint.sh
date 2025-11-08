#!/bin/bash

echo "Starting cron service..."
cron

echo "Running initial weather data fetch..."
python /app/fetch_weather.py

echo "Starting FastAPI server..."
exec uvicorn apis:app --host 0.0.0.0 --port 8000