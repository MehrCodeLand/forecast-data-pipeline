from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from loguru import logger

from analyse import Analyse
from config import settings
from data_json_manager import JSONDataManager
from scheduler import WeatherScheduler

logger.add('logs/api.txt', rotation="1 week")

data_manager = JSONDataManager(settings.data_file)
analyser = Analyse(json_manager=data_manager)
scheduler = WeatherScheduler(data_manager)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    yield
    await scheduler.stop()


app = FastAPI(
    title="Weather Analysis API",
    description="API for weather data collection and analysis in Tehran",
    version="1.1.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    return {
        "message": "Weather Analysis API",
        "endpoints": {
            "health": "/health",
            "scheduler": "/scheduler/*",
            "data": "/data",
            "temperature": "/temperature/*",
            "wind": "/wind/*",
            "summary": "/summary"
        }
    }


@app.get("/health")
async def health():
    return {"status": "ok", "scheduler_running": scheduler.running}


@app.get("/scheduler/status")
async def scheduler_status():
    return scheduler.status()


@app.post("/scheduler/collect-now")
async def scheduler_collect_now():
    success = await scheduler.collect_now()
    if not success:
        raise HTTPException(status_code=502, detail=f"Collection failed: {scheduler.last_error}")
    return {"collected": True, "status": scheduler.status()}


@app.get("/data")
async def get_all_data(limit: Optional[int] = Query(None, ge=1, description="Limit number of records")):
    try:
        data = await data_manager.read_data()
        if not data:
            raise HTTPException(status_code=404, detail="No data available")
        
        if limit:
            data = data[:limit]
        
        return JSONResponse(content={"count": len(data), "data": data})
    except Exception as e:
        logger.error(f"Error in get_all_data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/temperature/average")
async def get_average_temperature(period: int = Query(24, ge=1, description="Period in hours")):
    try:
        result = await analyser.get_avg(period)
        if result is None:
            raise HTTPException(status_code=404, detail="Unable to calculate average")
        
        return {"period": period, "average_temperature": result, "unit": "celsius"}
    except Exception as e:
        logger.error(f"Error in get_average_temperature: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/temperature/range")
async def get_temperature_range(period: int = Query(24, ge=1, description="Period in hours")):
    try:
        result = await analyser.get_temperature_range(period)
        if result is None:
            raise HTTPException(status_code=404, detail="Unable to calculate range")
        
        return {"period": period, "temperature_range": result, "unit": "celsius"}
    except Exception as e:
        logger.error(f"Error in get_temperature_range: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/temperature/rate-of-change")
async def get_temperature_rate_of_change(hours: int = Query(10, ge=2, description="Hours to analyze")):
    try:
        result = await analyser.estimate_avg_of_rate_of_change(hours)
        if result is None:
            raise HTTPException(status_code=404, detail="Unable to calculate rate of change")
        
        return {"hours": hours, "avg_rate_of_change": result, "unit": "celsius/hour"}
    except Exception as e:
        logger.error(f"Error in get_temperature_rate_of_change: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/temperature/delta")
async def get_temperature_delta(hours: int = Query(10, ge=1, description="Hours to analyze")):
    try:
        result = await analyser.estimate_delta(hours)
        if result is None:
            raise HTTPException(status_code=404, detail="Unable to calculate delta")
        
        return {"hours": hours, "delta_per_hour": result, "unit": "celsius/hour"}
    except Exception as e:
        logger.error(f"Error in get_temperature_delta: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/wind/average-speed")
async def get_average_windspeed(period: int = Query(24, ge=1, description="Period in hours")):
    try:
        result = await analyser.get_avg_windspeed(period)
        if result is None:
            raise HTTPException(status_code=404, detail="Unable to calculate average windspeed")
        
        return {"period": period, "average_windspeed": result, "unit": "km/h"}
    except Exception as e:
        logger.error(f"Error in get_average_windspeed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/wind/peak-speed")
async def get_peak_windspeed(period: int = Query(24, ge=1, description="Period in hours")):
    try:
        result = await analyser.get_peak_windspeed(period)
        if result is None:
            raise HTTPException(status_code=404, detail="Unable to calculate peak windspeed")
        
        return {"period": period, "peak_windspeed": result, "unit": "km/h"}
    except Exception as e:
        logger.error(f"Error in get_peak_windspeed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/wind/dominant-direction")
async def get_dominant_wind_direction(period: int = Query(24, ge=1, description="Period in hours")):
    try:
        result = await analyser.get_dominant_wind_direction(period)
        if result is None:
            raise HTTPException(status_code=404, detail="Unable to calculate dominant direction")
        
        return {"period": period, "dominant_direction": result, "unit": "degrees"}
    except Exception as e:
        logger.error(f"Error in get_dominant_wind_direction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/wind/direction-variability")
async def get_wind_direction_variability(period: int = Query(24, ge=2, description="Period in hours")):
    try:
        result = await analyser.get_wind_direction_variability(period)
        if result is None:
            raise HTTPException(status_code=404, detail="Unable to calculate variability")
        
        return {"period": period, "direction_variability": result, "unit": "degrees_std_dev"}
    except Exception as e:
        logger.error(f"Error in get_wind_direction_variability: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/wind/calm-periods")
async def get_calm_periods(
    period: int = Query(24, ge=1, description="Period in hours"),
    threshold: float = Query(5.0, ge=0, description="Windspeed threshold for calm")
):
    try:
        result = await analyser.get_calm_periods(period, threshold)
        if result is None:
            raise HTTPException(status_code=404, detail="Unable to calculate calm periods")
        
        return {"period": period, "threshold": threshold, "result": result, "unit": "km/h"}
    except Exception as e:
        logger.error(f"Error in get_calm_periods: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/summary")
async def get_weather_summary(period: int = Query(24, ge=1, description="Period in hours")):
    try:
        result = await analyser.get_weather_summary(period)
        if result is None:
            raise HTTPException(status_code=404, detail="Unable to generate summary")
        
        return {"period": period, "summary": result}
    except Exception as e:
        logger.error(f"Error in get_weather_summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("apis:app", host="0.0.0.0", port=8000)