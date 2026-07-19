"""Database entity design for the future PostgreSQL migration.

DESIGN ONLY — this module is not imported by the running app and creates no
engine, session, or tables. Today the app persists to JSON files (cities.json,
weather_<city>.json, site_content.json, app_settings.json, admin_config.json).
These SQLAlchemy models mirror that data so the move to Postgres later is a
straight mapping. When we activate the database we will add the engine, the
session, Alembic migrations, and the repository code that reads/writes these
tables instead of the JSON files.

Requires `sqlalchemy` (and a driver such as `psycopg[binary]`) once enabled;
neither is added to requirements yet, on purpose.

Entity overview:
    City            1 --- *  WeatherSnapshot
    City            1 --- 1  CollectionStatus
    ContentEntry    (language, key) bilingual site copy
    SharedSetting   key/value for donate_url, icon_data_url, ...
    AppSetting      key/value for interval, coordinates, ...
    AdminUser       admin credentials
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (Boolean, DateTime, Enum, Float, ForeignKey, Index,
                        Integer, String, Text, UniqueConstraint, func)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class WeatherSource(str, enum.Enum):
    OPEN_METEO = "open-meteo"
    OPENWEATHER = "openweather"


class City(Base):
    __tablename__ = "cities"

    # Slug id (e.g. "tehran"), matching the current JSON registry.
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    country: Mapped[str] = mapped_column(String(120), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    snapshots: Mapped[List["WeatherSnapshot"]] = relationship(
        back_populates="city", cascade="all, delete-orphan")
    status: Mapped[Optional["CollectionStatus"]] = relationship(
        back_populates="city", cascade="all, delete-orphan", uselist=False)


class WeatherSnapshot(Base):
    """One collected reading for a city (replaces a record in weather_*.json)."""

    __tablename__ = "weather_snapshots"
    __table_args__ = (
        # Fast "latest N records for this city, newest first" queries.
        Index("ix_snapshot_city_recorded", "city_id", "recorded_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    city_id: Mapped[str] = mapped_column(ForeignKey("cities.id", ondelete="CASCADE"), nullable=False)

    # When the source observed it (OpenWeather dt / Open-Meteo time) and when
    # we stored it (the old "timestamp" field).
    observed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False)
    source: Mapped[WeatherSource] = mapped_column(
        Enum(WeatherSource), default=WeatherSource.OPENWEATHER, nullable=False)

    # Core weather (units match what the app stores: temp °C, wind km/h, dir °)
    temperature: Mapped[Optional[float]] = mapped_column(Float)
    windspeed: Mapped[Optional[float]] = mapped_column(Float)
    winddirection: Mapped[Optional[float]] = mapped_column(Float)
    weathercode: Mapped[Optional[int]] = mapped_column(Integer)
    is_day: Mapped[Optional[bool]] = mapped_column(Boolean)

    # Extended weather (present depending on the source)
    humidity: Mapped[Optional[float]] = mapped_column(Float)
    apparent_temperature: Mapped[Optional[float]] = mapped_column(Float)
    pressure: Mapped[Optional[float]] = mapped_column(Float)
    temp_min: Mapped[Optional[float]] = mapped_column(Float)
    temp_max: Mapped[Optional[float]] = mapped_column(Float)
    visibility: Mapped[Optional[int]] = mapped_column(Integer)
    clouds: Mapped[Optional[float]] = mapped_column(Float)
    precipitation: Mapped[Optional[float]] = mapped_column(Float)
    condition_main: Mapped[Optional[str]] = mapped_column(String(60))
    condition_desc: Mapped[Optional[str]] = mapped_column(String(120))
    condition_icon: Mapped[Optional[str]] = mapped_column(String(10))

    # Air quality (OpenWeather air pollution)
    aqi: Mapped[Optional[int]] = mapped_column(Integer)
    co: Mapped[Optional[float]] = mapped_column(Float)
    no: Mapped[Optional[float]] = mapped_column(Float)
    no2: Mapped[Optional[float]] = mapped_column(Float)
    o3: Mapped[Optional[float]] = mapped_column(Float)
    so2: Mapped[Optional[float]] = mapped_column(Float)
    pm2_5: Mapped[Optional[float]] = mapped_column(Float)
    pm10: Mapped[Optional[float]] = mapped_column(Float)
    nh3: Mapped[Optional[float]] = mapped_column(Float)

    city: Mapped["City"] = relationship(back_populates="snapshots")


class CollectionStatus(Base):
    """Per-city collection health (replaces the scheduler's in-memory status)."""

    __tablename__ = "collection_status"

    city_id: Mapped[str] = mapped_column(
        ForeignKey("cities.id", ondelete="CASCADE"), primary_key=True)
    last_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[Optional[str]] = mapped_column(Text)
    failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    city: Mapped["City"] = relationship(back_populates="status")


class ContentEntry(Base):
    """Bilingual site copy (replaces the en/fa blocks of site_content.json)."""

    __tablename__ = "content_entries"
    __table_args__ = (UniqueConstraint("language", "key", name="uq_content_lang_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    language: Mapped[str] = mapped_column(String(5), nullable=False)  # "en" / "fa"
    key: Mapped[str] = mapped_column(String(60), nullable=False)      # site_name, tagline, ...
    value: Mapped[str] = mapped_column(Text, default="", nullable=False)


class SharedSetting(Base):
    """Language-independent content settings (donate_url, icon_data_url)."""

    __tablename__ = "shared_settings"

    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="", nullable=False)


class AppSetting(Base):
    """Runtime app settings (interval, coordinates) as key/value."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="", nullable=False)


class AdminUser(Base):
    """Admin credentials (replaces admin_config.json)."""

    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    password_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
