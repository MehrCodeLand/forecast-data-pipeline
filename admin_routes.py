"""Admin panel routes, mounted under the custom path from admin_config.json."""

import io
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from loguru import logger
from pydantic import BaseModel, Field

from admin_auth import (SESSION_COOKIE, admin_config, create_session,
                        destroy_session, is_valid_session, require_admin,
                        verify_credentials)
from analyse import Analyse
from cities import CityStore
from config import settings
from content import content_store
from report import build_report_data, render_report_html, render_report_pdf
from scheduler import WeatherScheduler

ADMIN_PATH = admin_config["admin_path"]
UI_DIR = Path(__file__).parent / "admin_ui"


class LoginRequest(BaseModel):
    username: str
    password: str


class CityCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    country: str = Field(min_length=1, max_length=80)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class CityUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=80)
    country: Optional[str] = Field(default=None, min_length=1, max_length=80)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    enabled: Optional[bool] = None


class SettingsRequest(BaseModel):
    fetch_interval_minutes: int = Field(ge=1, le=1440)


class ContentRequest(BaseModel):
    donate_url: Optional[str] = None
    en: Optional[Dict[str, str]] = None
    fa: Optional[Dict[str, str]] = None


def _page(name: str) -> HTMLResponse:
    html = (UI_DIR / name).read_text().replace("{{ADMIN_PATH}}", ADMIN_PATH)
    return HTMLResponse(html)


def _is_authed(request: Request) -> bool:
    return is_valid_session(request.cookies.get(SESSION_COOKIE))


def create_admin_router(city_store: CityStore, scheduler: WeatherScheduler) -> APIRouter:
    router = APIRouter(prefix=ADMIN_PATH, tags=["admin"])

    def city_or_404(city_id: str) -> Dict:
        city = city_store.get(city_id)
        if city is None:
            raise HTTPException(status_code=404, detail=f"Unknown city: {city_id}")
        return city

    # ----- pages -----

    @router.get("", include_in_schema=False)
    async def admin_root(request: Request):
        if _is_authed(request):
            return RedirectResponse(f"{ADMIN_PATH}/dashboard", status_code=302)
        return _page("login.html")

    @router.get("/dashboard", include_in_schema=False)
    async def admin_dashboard(request: Request):
        if not _is_authed(request):
            return RedirectResponse(ADMIN_PATH, status_code=302)
        return _page("dashboard.html")

    @router.get("/static/admin.css", include_in_schema=False)
    async def admin_css():
        return FileResponse(UI_DIR / "admin.css", media_type="text/css")

    @router.get("/report", include_in_schema=False)
    async def report_html(request: Request, city: str = Query("tehran")):
        if not _is_authed(request):
            return RedirectResponse(ADMIN_PATH, status_code=302)
        city_record = city_or_404(city)
        data_manager = city_store.data_manager(city_record)
        report = await build_report_data(
            city_record, data_manager, Analyse(json_manager=data_manager), scheduler.status())
        return HTMLResponse(render_report_html(report, ADMIN_PATH))

    @router.get("/report/pdf", include_in_schema=False)
    async def report_pdf(request: Request, city: str = Query("tehran")):
        if not _is_authed(request):
            return RedirectResponse(ADMIN_PATH, status_code=302)
        city_record = city_or_404(city)
        data_manager = city_store.data_manager(city_record)
        report = await build_report_data(
            city_record, data_manager, Analyse(json_manager=data_manager), scheduler.status())
        return Response(
            content=render_report_pdf(report),
            media_type="application/pdf",
            headers={"Content-Disposition":
                     f'attachment; filename="weather_report_{city_record["id"]}.pdf"'},
        )

    # ----- auth API -----

    @router.post("/api/login")
    async def login(body: LoginRequest):
        if not verify_credentials(body.username, body.password):
            logger.warning(f"Failed admin login attempt for user '{body.username}'")
            raise HTTPException(status_code=401, detail="Invalid username or password")

        token = create_session()
        response = Response(content='{"logged_in": true}', media_type="application/json")
        response.set_cookie(
            SESSION_COOKIE, token, httponly=True, samesite="lax",
            max_age=int(float(admin_config.get("session_hours", 8)) * 3600), path="/",
        )
        return response

    @router.post("/api/logout")
    async def logout(request: Request):
        destroy_session(request.cookies.get(SESSION_COOKIE))
        response = Response(content='{"logged_in": false}', media_type="application/json")
        response.delete_cookie(SESSION_COOKIE, path="/")
        return response

    # ----- overview -----

    @router.get("/api/overview", dependencies=[Depends(require_admin)])
    async def overview():
        scheduler_status = scheduler.status()
        cities = []
        for city in city_store.all():
            data = await city_store.data_manager(city).read_data()
            city_sched = scheduler_status["cities"].get(city["id"], {})
            cities.append({
                **city,
                "records": len(data),
                "last_record": data[-1].get("timestamp") if data else None,
                "last_success_at": city_sched.get("last_success_at"),
                "last_error": city_sched.get("last_error"),
                "collection_failures": city_sched.get("failures", 0),
            })
        return {
            "settings": {"fetch_interval_minutes": settings.fetch_interval_minutes},
            "scheduler": scheduler_status,
            "cities": cities,
        }

    # ----- city management -----

    @router.post("/api/cities", dependencies=[Depends(require_admin)])
    async def add_city(body: CityCreateRequest):
        city = city_store.add(body.name, body.country, body.latitude, body.longitude)
        # Collect a first snapshot right away so the new city is not empty
        # until the next scheduled run (which could be up to an hour later).
        collected = await scheduler.collect_city(city)
        error = None if collected else scheduler.city_status.get(city["id"], {}).get("last_error")
        return {"created": True, "city": city, "collected": collected, "error": error}

    @router.put("/api/cities/{city_id}", dependencies=[Depends(require_admin)])
    async def update_city(city_id: str, body: CityUpdateRequest):
        city_or_404(city_id)
        city = city_store.update(city_id, **body.model_dump(exclude_none=True))
        return {"updated": True, "city": city}

    @router.delete("/api/cities/{city_id}", dependencies=[Depends(require_admin)])
    async def delete_city(city_id: str):
        city_or_404(city_id)
        if len(city_store.all()) <= 1:
            raise HTTPException(status_code=400, detail="Cannot delete the last city")
        city_store.delete(city_id)
        return {"deleted": True, "city_id": city_id}

    @router.post("/api/cities/{city_id}/collect-now", dependencies=[Depends(require_admin)])
    async def collect_city_now(city_id: str):
        city = city_or_404(city_id)
        success = await scheduler.collect_city(city)
        if not success:
            error = scheduler.city_status.get(city_id, {}).get("last_error")
            raise HTTPException(status_code=502, detail=f"Collection failed: {error}")
        return {"collected": True, "city_id": city_id}

    @router.post("/api/collect-now", dependencies=[Depends(require_admin)])
    async def collect_all_now():
        results = await scheduler.collect_all()
        return {"results": results, "scheduler": scheduler.status()}

    # ----- site content management -----

    @router.get("/api/content", dependencies=[Depends(require_admin)])
    async def get_content():
        return content_store.get()

    @router.put("/api/content", dependencies=[Depends(require_admin)])
    async def update_content(body: ContentRequest):
        updated = content_store.update(body.model_dump(exclude_none=True))
        return {"updated": True, "content": updated}

    # ----- settings -----

    @router.post("/api/settings", dependencies=[Depends(require_admin)])
    async def update_settings(body: SettingsRequest):
        interval_changed = body.fetch_interval_minutes != settings.fetch_interval_minutes
        settings.update(fetch_interval_minutes=body.fetch_interval_minutes)
        if interval_changed:
            await scheduler.set_interval(body.fetch_interval_minutes)
        logger.info(f"Admin updated settings: interval={body.fetch_interval_minutes}m")
        return {"updated": True, "settings": {"fetch_interval_minutes": settings.fetch_interval_minutes}}

    # ----- downloads -----

    @router.get("/api/download/json", dependencies=[Depends(require_admin)])
    async def download_json(city: str = Query("tehran")):
        city_record = city_or_404(city)
        data_file = Path(city_record["data_file"])
        if not data_file.exists():
            raise HTTPException(status_code=404, detail="No data collected for this city yet")
        return FileResponse(data_file, media_type="application/json",
                            filename=f"weather_data_{city_record['id']}.json")

    @router.get("/api/download/csv", dependencies=[Depends(require_admin)])
    async def download_csv(city: str = Query("tehran")):
        city_record = city_or_404(city)
        data = await city_store.data_manager(city_record).read_data()
        if not data:
            raise HTTPException(status_code=404, detail="No data collected for this city yet")
        buffer = io.StringIO()
        pd.DataFrame(data).to_csv(buffer, index=False)
        return Response(
            content=buffer.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition":
                     f'attachment; filename="weather_data_{city_record["id"]}.csv"'},
        )

    return router
