from contextlib import asynccontextmanager
from typing import Dict, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from admin_routes import create_admin_router
from analyse import Analyse
from cities import city_store
from content import content_store
from scheduler import WeatherScheduler

logger.add('logs/api.txt', rotation="1 week")

scheduler = WeatherScheduler(city_store)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    yield
    await scheduler.stop()


app = FastAPI(
    title="Weather Analysis API",
    description="Weather data collection and analysis for cities around the world",
    version="2.0.0",
    lifespan=lifespan
)

# The public site is served by nginx on another port, so browsers make
# cross-origin requests to this API. Without CORS every page call fails.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(create_admin_router(city_store, scheduler))


def get_city_or_404(city_id: str) -> Dict:
    city = city_store.get(city_id)
    if city is None:
        raise HTTPException(status_code=404, detail=f"Unknown city: {city_id}")
    return city


def analyser_for(city: Dict) -> Analyse:
    return Analyse(json_manager=city_store.data_manager(city))


@app.get("/")
async def root():
    return {
        "message": "Weather Analysis API",
        "endpoints": {
            "health": "/health",
            "scheduler": "/scheduler/status",
            "content": "/content",
            "cities": "/cities",
            "city": "/cities/{city_id}",
            "city_data": "/cities/{city_id}/data",
            "city_summary": "/cities/{city_id}/summary",
            "city_records": "/cities/{city_id}/records",
            "city_temperature": "/cities/{city_id}/temperature/*",
            "city_wind": "/cities/{city_id}/wind/*",
        }
    }


@app.get("/health")
async def health():
    return {"status": "ok", "scheduler_running": scheduler.running}


@app.get("/scheduler/status")
async def scheduler_status():
    return scheduler.status()


@app.get("/content")
async def site_content():
    return content_store.get()


@app.get("/cities")
async def list_cities():
    cities = []
    for city in city_store.enabled():
        data = await city_store.data_manager(city).read_data()
        cities.append({
            "id": city["id"],
            "name": city["name"],
            "country": city["country"],
            "latitude": city["latitude"],
            "longitude": city["longitude"],
            "records": len(data),
            "latest": data[-1] if data else None,
        })
    return {"count": len(cities), "cities": cities}


@app.get("/cities/{city_id}")
async def city_detail(city_id: str):
    city = get_city_or_404(city_id)
    data = await city_store.data_manager(city).read_data()
    return {
        "id": city["id"],
        "name": city["name"],
        "country": city["country"],
        "latitude": city["latitude"],
        "longitude": city["longitude"],
        "records": len(data),
        "first_record": data[0].get("timestamp") if data else None,
        "last_record": data[-1].get("timestamp") if data else None,
        "latest": data[-1] if data else None,
    }


@app.get("/cities/{city_id}/data")
async def city_data(city_id: str,
                    limit: Optional[int] = Query(None, ge=1, description="Limit number of records")):
    city = get_city_or_404(city_id)
    try:
        data = await city_store.data_manager(city).read_data()
        if not data:
            raise HTTPException(status_code=404, detail="No data available for this city yet")

        total = len(data)
        data = list(reversed(data))  # newest first
        if limit:
            data = data[:limit]

        return JSONResponse(content={"total": total, "count": len(data), "data": data})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in city_data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cities/{city_id}/summary")
async def city_summary(city_id: str,
                       period: int = Query(24, ge=1, description="Period in records")):
    city = get_city_or_404(city_id)
    try:
        result = await analyser_for(city).get_weather_summary(period)
        if result is None:
            raise HTTPException(status_code=404, detail="Unable to generate summary")
        return {"city": city["id"], "period": period, "summary": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in city_summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/cities/{city_id}/records")
async def city_records(city_id: str,
                       threshold: float = Query(5.0, ge=0, description="Calm windspeed threshold")):
    city = get_city_or_404(city_id)
    result = await analyser_for(city).get_records(calm_threshold=threshold)
    if result is None:
        raise HTTPException(status_code=404, detail="No data available for this city yet")
    return {"city": city["id"], "records": result}


@app.get("/cities/{city_id}/temperature/average")
async def city_avg_temperature(city_id: str, period: int = Query(24, ge=1)):
    city = get_city_or_404(city_id)
    result = await analyser_for(city).get_avg(period)
    if result is None:
        raise HTTPException(status_code=404, detail="Unable to calculate average")
    return {"city": city["id"], "period": period, "average_temperature": result, "unit": "celsius"}


@app.get("/cities/{city_id}/temperature/range")
async def city_temperature_range(city_id: str, period: int = Query(24, ge=1)):
    city = get_city_or_404(city_id)
    result = await analyser_for(city).get_temperature_range(period)
    if result is None:
        raise HTTPException(status_code=404, detail="Unable to calculate range")
    return {"city": city["id"], "period": period, "temperature_range": result, "unit": "celsius"}


@app.get("/cities/{city_id}/temperature/rate-of-change")
async def city_temperature_rate(city_id: str, hours: int = Query(10, ge=2)):
    city = get_city_or_404(city_id)
    result = await analyser_for(city).estimate_avg_of_rate_of_change(hours)
    if result is None:
        raise HTTPException(status_code=404, detail="Unable to calculate rate of change")
    return {"city": city["id"], "hours": hours, "avg_rate_of_change": result, "unit": "celsius/hour"}


@app.get("/cities/{city_id}/temperature/delta")
async def city_temperature_delta(city_id: str, hours: int = Query(10, ge=1)):
    city = get_city_or_404(city_id)
    result = await analyser_for(city).estimate_delta(hours)
    if result is None:
        raise HTTPException(status_code=404, detail="Unable to calculate delta")
    return {"city": city["id"], "hours": hours, "delta_per_hour": result, "unit": "celsius/hour"}


@app.get("/cities/{city_id}/wind/average-speed")
async def city_avg_windspeed(city_id: str, period: int = Query(24, ge=1)):
    city = get_city_or_404(city_id)
    result = await analyser_for(city).get_avg_windspeed(period)
    if result is None:
        raise HTTPException(status_code=404, detail="Unable to calculate average windspeed")
    return {"city": city["id"], "period": period, "average_windspeed": result, "unit": "km/h"}


@app.get("/cities/{city_id}/wind/peak-speed")
async def city_peak_windspeed(city_id: str, period: int = Query(24, ge=1)):
    city = get_city_or_404(city_id)
    result = await analyser_for(city).get_peak_windspeed(period)
    if result is None:
        raise HTTPException(status_code=404, detail="Unable to calculate peak windspeed")
    return {"city": city["id"], "period": period, "peak_windspeed": result, "unit": "km/h"}


@app.get("/cities/{city_id}/wind/dominant-direction")
async def city_dominant_direction(city_id: str, period: int = Query(24, ge=1)):
    city = get_city_or_404(city_id)
    result = await analyser_for(city).get_dominant_wind_direction(period)
    if result is None:
        raise HTTPException(status_code=404, detail="Unable to calculate dominant direction")
    return {"city": city["id"], "period": period, "dominant_direction": result, "unit": "degrees"}


@app.get("/cities/{city_id}/wind/direction-variability")
async def city_direction_variability(city_id: str, period: int = Query(24, ge=2)):
    city = get_city_or_404(city_id)
    result = await analyser_for(city).get_wind_direction_variability(period)
    if result is None:
        raise HTTPException(status_code=404, detail="Unable to calculate variability")
    return {"city": city["id"], "period": period, "direction_variability": result, "unit": "degrees_std_dev"}


@app.get("/cities/{city_id}/wind/calm-periods")
async def city_calm_periods(city_id: str, period: int = Query(24, ge=1),
                            threshold: float = Query(5.0, ge=0)):
    city = get_city_or_404(city_id)
    result = await analyser_for(city).get_calm_periods(period, threshold)
    if result is None:
        raise HTTPException(status_code=404, detail="Unable to calculate calm periods")
    return {"city": city["id"], "period": period, "threshold": threshold, "result": result, "unit": "km/h"}


if __name__ == "__main__":
    uvicorn.run("apis:app", host="0.0.0.0", port=8000)
