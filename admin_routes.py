"""Admin panel routes, mounted under the custom path from admin_config.json."""

import io
from pathlib import Path
from typing import Dict, List, Optional

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
import payments
from content import content_store
from news import news_store
from payments import payment_store, tier_store
from report import build_report_data, render_report_html, render_report_pdf
from scheduler import WeatherScheduler

ADMIN_PATH = admin_config["admin_path"]
UI_DIR = Path(__file__).parent / "admin_ui"

# Air-quality fields stored per snapshot (OpenWeather AQI + pollutants).
AQI_FIELDS = ["aqi", "pm2_5", "pm10", "o3", "no2", "so2", "co", "no", "nh3"]


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
    icon_data_url: Optional[str] = None
    en: Optional[Dict[str, str]] = None
    fa: Optional[Dict[str, str]] = None


class CoffeeTier(BaseModel):
    id: str = Field(min_length=1, max_length=30)
    name_en: str = Field(min_length=1, max_length=60)
    name_fa: str = Field(min_length=1, max_length=60)
    toman: int = Field(ge=payments.MIN_TIER_TOMAN, le=payments.MAX_TIER_TOMAN)
    enabled: bool = True


class CoffeeTiersRequest(BaseModel):
    """The complete tier list; it replaces whatever is stored."""
    tiers: List[CoffeeTier] = Field(min_length=1, max_length=10)


class NewsBlock(BaseModel):
    title: Optional[str] = Field(default=None, max_length=160)
    summary: Optional[str] = Field(default=None, max_length=400)
    body: Optional[str] = Field(default=None, max_length=8000)


class NewsRequest(BaseModel):
    tag: Optional[str] = Field(default=None, max_length=40)
    published: Optional[bool] = None
    published_at: Optional[str] = None
    en: Optional[NewsBlock] = None
    fa: Optional[NewsBlock] = None


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
        aqi_records_total = 0
        for city in city_store.all():
            data = await city_store.data_manager(city).read_data()
            city_sched = scheduler_status["cities"].get(city["id"], {})
            latest = data[-1] if data else {}
            aqi_count = sum(1 for r in data if isinstance(r.get("aqi"), (int, float)))
            aqi_records_total += aqi_count
            cities.append({
                **city,
                "records": len(data),
                "aqi_records": aqi_count,
                "last_record": latest.get("timestamp"),
                "last_success_at": city_sched.get("last_success_at"),
                "last_error": city_sched.get("last_error"),
                "collection_failures": city_sched.get("failures", 0),
                # Latest air-quality reading for the monitor table.
                "air": {k: latest.get(k) for k in AQI_FIELDS if latest.get(k) is not None},
            })
        return {
            "settings": {"fetch_interval_minutes": settings.fetch_interval_minutes},
            "scheduler": scheduler_status,
            "cities": cities,
            "aqi_records_total": aqi_records_total,
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

    # ----- news posts -----

    @router.get("/api/news", dependencies=[Depends(require_admin)])
    async def list_news():
        """Every post, drafts included."""
        return {"items": news_store.all()}

    @router.post("/api/news", dependencies=[Depends(require_admin)])
    async def create_news(body: NewsRequest):
        try:
            post = news_store.add(body.model_dump(exclude_none=True))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"created": True, "post": post}

    @router.put("/api/news/{post_id}", dependencies=[Depends(require_admin)])
    async def update_news(post_id: str, body: NewsRequest):
        try:
            post = news_store.update(post_id, body.model_dump(exclude_none=True))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        if post is None:
            raise HTTPException(status_code=404, detail=f"Unknown post: {post_id}")
        return {"updated": True, "post": post}

    @router.delete("/api/news/{post_id}", dependencies=[Depends(require_admin)])
    async def delete_news(post_id: str):
        if not news_store.delete(post_id):
            raise HTTPException(status_code=404, detail=f"Unknown post: {post_id}")
        return {"deleted": True, "post_id": post_id}

    # ----- coffee tiers ("buy me a coffee" prices) -----

    @router.get("/api/coffee-tiers", dependencies=[Depends(require_admin)])
    async def get_coffee_tiers():
        return {
            "tiers": tier_store.all(),
            "min_toman": payments.MIN_TIER_TOMAN,
            "max_toman": payments.MAX_TIER_TOMAN,
        }

    @router.put("/api/coffee-tiers", dependencies=[Depends(require_admin)])
    async def update_coffee_tiers(body: CoffeeTiersRequest):
        """Replace the whole tier list. Prices take effect immediately; they
        never change what an already-recorded payment was charged."""
        try:
            tiers = tier_store.replace([t.model_dump() for t in body.tiers])
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"updated": True, "tiers": tiers}

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

    @router.get("/api/download/all-csv", dependencies=[Depends(require_admin)])
    async def download_all_csv():
        """One CSV with every city's records combined, prefixed by city columns."""
        frames = []
        for city in city_store.all():
            data = await city_store.data_manager(city).read_data()
            if not data:
                continue
            df = pd.DataFrame(data)
            df.insert(0, "city_name", city["name"])
            df.insert(0, "city_id", city["id"])
            frames.append(df)
        if not frames:
            raise HTTPException(status_code=404, detail="No data collected for any city yet")
        combined = pd.concat(frames, ignore_index=True, sort=False)
        buffer = io.StringIO()
        combined.to_csv(buffer, index=False)
        return Response(
            content=buffer.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="weather_data_all_cities.csv"'},
        )

    def _aqi_rows(city: Dict, records: list) -> list:
        """AQI-only rows (city + timestamp + pollutants) for records that
        actually carry an air-quality reading."""
        rows = []
        for r in records:
            if not isinstance(r.get("aqi"), (int, float)):
                continue
            row = {
                "city_id": city["id"],
                "city_name": city["name"],
                "time": r.get("time"),
                "timestamp": r.get("timestamp"),
            }
            for field in AQI_FIELDS:
                row[field] = r.get(field)
            rows.append(row)
        return rows

    # ----- payments -----

    @router.get("/api/payments", dependencies=[Depends(require_admin)])
    async def list_payments():
        """All payment attempts, newest first, plus totals."""
        items = payment_store.all()
        items.reverse()
        return {"stats": payment_store.stats(), "payments": items}

    @router.post("/api/payments/{track_id}/recheck", dependencies=[Depends(require_admin)])
    async def recheck_payment(track_id: str):
        """Re-verify a payment that was left pending (e.g. the callback's
        verify call could not reach the gateway)."""
        try:
            record = await payments.verify_payment(track_id)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except RuntimeError as e:
            raise HTTPException(status_code=502, detail=str(e))
        return {"rechecked": True, "payment": record}

    @router.get("/api/download/payments-csv", dependencies=[Depends(require_admin)])
    async def download_payments_csv(only_paid: bool = Query(False)):
        rows = payment_store.paid() if only_paid else payment_store.all()
        if not rows:
            raise HTTPException(status_code=404, detail="No payments recorded yet")
        columns = ["created_at", "paid_at", "first_name", "last_name", "tier_name",
                   "amount_toman", "amount_rial", "status", "order_id", "track_id",
                   "ref_number", "card_number", "zibal_status", "message"]
        df = pd.DataFrame(rows).reindex(columns=columns)
        # Missing values in an int column make pandas emit floats ("123.0");
        # keep reference/status numbers readable as plain integers.
        for col in ("ref_number", "zibal_status", "track_id"):
            df[col] = df[col].map(lambda v: "" if pd.isna(v) else str(int(v))
                                  if isinstance(v, (int, float)) else str(v))
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)
        return Response(
            content=buffer.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="payments.csv"'},
        )

    @router.get("/api/download/aqi-csv", dependencies=[Depends(require_admin)])
    async def download_aqi_csv(city: str = Query("all", description="City id or 'all'")):
        """Export all stored Air Quality data (all days) as CSV. `city=all`
        combines every city; otherwise a single city."""
        if city == "all":
            targets = city_store.all()
            filename = "air_quality_all_cities.csv"
        else:
            targets = [city_or_404(city)]
            filename = f"air_quality_{city}.csv"

        rows = []
        for c in targets:
            data = await city_store.data_manager(c).read_data()
            rows.extend(_aqi_rows(c, data))

        if not rows:
            raise HTTPException(status_code=404, detail="No air-quality data collected yet")

        columns = ["city_id", "city_name", "time", "timestamp"] + AQI_FIELDS
        buffer = io.StringIO()
        pd.DataFrame(rows, columns=columns).to_csv(buffer, index=False)
        return Response(
            content=buffer.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return router
