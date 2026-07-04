"""Admin panel routes, mounted under the custom path from admin_config.json."""

import io
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from loguru import logger
from pydantic import BaseModel, Field

from admin_auth import (SESSION_COOKIE, admin_config, create_session,
                        destroy_session, is_valid_session, require_admin,
                        verify_credentials)
from analyse import Analyse
from config import settings
from data_json_manager import JSONDataManager
from report import build_report_data, render_report_html, render_report_pdf
from scheduler import WeatherScheduler

ADMIN_PATH = admin_config["admin_path"]
UI_DIR = Path(__file__).parent / "admin_ui"


class LoginRequest(BaseModel):
    username: str
    password: str


class SettingsRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    fetch_interval_minutes: int = Field(ge=1, le=1440)


def _page(name: str) -> HTMLResponse:
    html = (UI_DIR / name).read_text().replace("{{ADMIN_PATH}}", ADMIN_PATH)
    return HTMLResponse(html)


def _is_authed(request: Request) -> bool:
    return is_valid_session(request.cookies.get(SESSION_COOKIE))


def create_admin_router(data_manager: JSONDataManager, analyser: Analyse,
                        scheduler: WeatherScheduler) -> APIRouter:
    router = APIRouter(prefix=ADMIN_PATH, tags=["admin"])

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
    async def report_html(request: Request):
        if not _is_authed(request):
            return RedirectResponse(ADMIN_PATH, status_code=302)
        report = await build_report_data(data_manager, analyser, scheduler.status())
        return HTMLResponse(render_report_html(report, ADMIN_PATH))

    @router.get("/report/pdf", include_in_schema=False)
    async def report_pdf(request: Request):
        if not _is_authed(request):
            return RedirectResponse(ADMIN_PATH, status_code=302)
        report = await build_report_data(data_manager, analyser, scheduler.status())
        pdf_bytes = render_report_pdf(report)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="weather_report.pdf"'},
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

    # ----- management API (all protected) -----

    @router.get("/api/overview", dependencies=[Depends(require_admin)])
    async def overview():
        data = await data_manager.read_data()
        return {
            "settings": settings.as_dict(),
            "scheduler": scheduler.status(),
            "data": {
                "total_records": len(data),
                "first_record": data[0].get("timestamp") if data else None,
                "last_record": data[-1].get("timestamp") if data else None,
            },
            "summary": await analyser.get_weather_summary(24),
        }

    @router.post("/api/settings", dependencies=[Depends(require_admin)])
    async def update_settings(body: SettingsRequest):
        interval_changed = body.fetch_interval_minutes != settings.fetch_interval_minutes
        settings.update(
            latitude=body.latitude,
            longitude=body.longitude,
            fetch_interval_minutes=body.fetch_interval_minutes,
        )
        if interval_changed:
            await scheduler.set_interval(body.fetch_interval_minutes)
        logger.info(f"Admin updated settings: {settings.as_dict()}")
        return {"updated": True, "settings": settings.as_dict()}

    @router.post("/api/collect-now", dependencies=[Depends(require_admin)])
    async def collect_now():
        success = await scheduler.collect_now()
        if not success:
            raise HTTPException(status_code=502,
                                detail=f"Collection failed: {scheduler.last_error}")
        return {"collected": True, "scheduler": scheduler.status()}

    # ----- downloads (protected) -----

    @router.get("/api/download/json", dependencies=[Depends(require_admin)])
    async def download_json():
        data_file = Path(settings.data_file)
        if not data_file.exists():
            raise HTTPException(status_code=404, detail="No data collected yet")
        return FileResponse(data_file, media_type="application/json",
                            filename="weather_data.json")

    @router.get("/api/download/csv", dependencies=[Depends(require_admin)])
    async def download_csv():
        data = await data_manager.read_data()
        if not data:
            raise HTTPException(status_code=404, detail="No data collected yet")
        buffer = io.StringIO()
        pd.DataFrame(data).to_csv(buffer, index=False)
        return Response(
            content=buffer.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="weather_data.csv"'},
        )

    return router
