"""Rastreabilidade e estrutura comum para as atualizações de dados."""
from __future__ import annotations

import json
from datetime import date

from sqlalchemy import text

from .config import Settings, load_settings
from .db import make_engine


def ensure_data_schema(settings: Settings | None = None) -> None:
    """Cria estruturas novas também em bancos já inicializados pelo Docker."""
    engine = make_engine(settings or load_settings())
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS market"))
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS ops"))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS geo.neighborhoods (
                    id BIGSERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    municipality TEXT,
                    municipality_code TEXT,
                    source_name TEXT NOT NULL,
                    source_file TEXT,
                    reference_date DATE,
                    imported_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    geom geometry(MultiPolygon, 4326) NOT NULL,
                    UNIQUE (name, municipality_code, source_name)
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS neighborhoods_geom_gix ON geo.neighborhoods USING GIST (geom)"))
            conn.execute(text("ALTER TABLE geo.features ADD COLUMN IF NOT EXISTS neighborhood TEXT"))
            conn.execute(text("ALTER TABLE geo.features ADD COLUMN IF NOT EXISTS neighborhood_source TEXT"))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS market.listings (
                    id BIGSERIAL PRIMARY KEY,
                    source_name TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    collected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    listed_at DATE,
                    title TEXT,
                    url TEXT,
                    price NUMERIC,
                    area_m2 NUMERIC,
                    price_per_m2 NUMERIC,
                    property_type TEXT,
                    neighborhood TEXT,
                    city TEXT,
                    state TEXT,
                    geom geometry(Point, 4326),
                    raw JSONB NOT NULL DEFAULT '{}'::jsonb,
                    UNIQUE (source_name, external_id)
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS listings_geom_gix ON market.listings USING GIST (geom)"))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS ops.data_sources (
                    id BIGSERIAL PRIMARY KEY,
                    dataset TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    source_uri TEXT,
                    reference_date DATE,
                    collected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    row_count INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'ok',
                    details JSONB NOT NULL DEFAULT '{}'::jsonb
                )
            """))
    finally:
        engine.dispose()


def record_data_source(
    dataset: str,
    source_name: str,
    *,
    source_uri: str | None = None,
    reference_date: date | None = None,
    row_count: int = 0,
    status: str = "ok",
    details: dict[str, object] | None = None,
    settings: Settings | None = None,
) -> None:
    ensure_data_schema(settings)
    engine = make_engine(settings or load_settings())
    try:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO ops.data_sources
                    (dataset, source_name, source_uri, reference_date, row_count, status, details)
                    VALUES (:dataset, :source_name, :source_uri, :reference_date, :row_count, :status,
                            CAST(:details AS jsonb))
                """),
                {
                    "dataset": dataset, "source_name": source_name, "source_uri": source_uri,
                    "reference_date": reference_date, "row_count": row_count, "status": status,
                    "details": json.dumps(details or {}, ensure_ascii=False),
                },
            )
    finally:
        engine.dispose()
