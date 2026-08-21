"""Persistência e atualização auditável da base de anúncios."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from .config import load_settings
from .data_registry import ensure_data_schema, record_data_source
from .db import make_engine
from .listings_import import normalize_listings


def import_listings_csv(input_csv: str, *, source_name: str = "portal_csv", settings=None) -> dict[str, object]:
    normalized_path = str(Path(input_csv).with_suffix(".normalized.csv"))
    result = normalize_listings(input_csv, normalized_path)
    frame = pd.read_csv(normalized_path, low_memory=False)
    active_settings = settings or load_settings()
    ensure_data_schema(active_settings)
    engine = make_engine(active_settings)
    imported = 0
    try:
        with engine.begin() as conn:
            for row in frame.to_dict(orient="records"):
                external_id = str(row.get("ml_id") or row.get("id") or row.get("url") or _row_hash(row))
                price, area = _number(row.get("price")), _number(row.get("area_m2"))
                lat, lon = _number(row.get("lat")), _number(row.get("lon"))
                conn.execute(text("""
                    INSERT INTO market.listings
                    (source_name, external_id, title, url, price, area_m2, price_per_m2, property_type,
                     neighborhood, city, state, geom, raw)
                    VALUES (:source, :external_id, :title, :url, :price, :area, :ppm, :property_type,
                            :neighborhood, :city, :state,
                            CASE WHEN :lat IS NOT NULL AND :lon IS NOT NULL
                                 THEN ST_SetSRID(ST_MakePoint(:lon, :lat), 4326) END,
                            CAST(:raw AS jsonb))
                    ON CONFLICT (source_name, external_id) DO UPDATE SET
                      collected_at = now(), price = EXCLUDED.price, area_m2 = EXCLUDED.area_m2,
                      price_per_m2 = EXCLUDED.price_per_m2, neighborhood = EXCLUDED.neighborhood,
                      geom = COALESCE(EXCLUDED.geom, market.listings.geom), raw = EXCLUDED.raw
                """), {"source": source_name, "external_id": external_id, "title": row.get("title"), "url": row.get("url"),
                           "price": price, "area": area, "ppm": price / area if price and area else None,
                           "property_type": row.get("property_type"), "neighborhood": row.get("neighborhood"),
                           "city": row.get("city"), "state": row.get("state"), "lat": lat, "lon": lon,
                           "raw": json.dumps(row, ensure_ascii=False, default=str)})
                imported += 1
    finally:
        engine.dispose()
    record_data_source("listings", source_name, source_uri=input_csv, row_count=imported, details={"normalized_file": normalized_path, "rows_read": result.rows_read}, settings=active_settings)
    return {"rows_read": result.rows_read, "rows_imported": imported, "normalized_path": normalized_path, "missing_columns": result.missing_columns}


def sync_listings(city_query: str = "Pouso Alegre MG", settings=None) -> dict[str, object]:
    """Atualiza anúncios reais sem promover dados demonstrativos a dados de mercado."""
    source_file = Path("data/ml_listings.csv")
    if not source_file.exists() and os.environ.get("ML_ACCESS_TOKEN"):
        from .api_collector import fetch_ml_listings
        fetch_ml_listings(city_query=city_query, output_csv=str(source_file))
    if source_file.exists() and source_file.stat().st_size > 0:
        return import_listings_csv(str(source_file), source_name="mercadolivre", settings=settings)
    record_data_source("listings", "mercadolivre", status="waiting_credentials", details={"hint": "defina ML_ACCESS_TOKEN ou coloque data/ml_listings.csv"}, settings=settings)
    return {"rows_imported": 0, "status": "waiting_credentials"}


def _number(value):
    if value is None or pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _row_hash(row: dict[str, object]) -> str:
    return hashlib.sha256(json.dumps(row, sort_keys=True, default=str).encode()).hexdigest()
