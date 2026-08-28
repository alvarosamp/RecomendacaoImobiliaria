"""Importador das cartas oficiais de suscetibilidade do SGB/CPRM."""
from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import urlopen

from sqlalchemy import text

from .config import Settings, load_settings
from .db import db_engine

BASE_URL = "https://geoservicos.sgb.gov.br/ogcapi/collections/gestao-territorial/suscetibilidade"
COLLECTIONS = ("inundacao", "movimento-de-massa")


def sync_sgb_susceptibility(settings: Settings | None = None) -> int:
    """Baixa as feicoes oficiais do municipio e substitui a copia local."""
    settings = settings or load_settings()
    with db_engine(settings) as engine, engine.connect() as conn:
        city = conn.execute(text("SELECT name FROM geo.city_boundary LIMIT 1")).scalar()
    if not city:
        raise RuntimeError("Limite municipal ausente.")
    municipality = str(city).split(",")[0].upper()
    features: list[tuple[str, dict]] = []
    for collection in COLLECTIONS:
        query = urlencode({"municipio": municipality, "limit": 10000, "f": "json"})
        url = f"{BASE_URL}/{collection}/items?{query}"
        with urlopen(url, timeout=90) as response:  # nosec B310 - dominio publico fixo
            payload = json.load(response)
        features.extend((url, feature) for feature in payload.get("features", []) if feature.get("geometry"))
    with db_engine(settings) as engine, engine.begin() as conn:
        conn.execute(text("TRUNCATE geo.official_susceptibility RESTART IDENTITY"))
        for url, feature in features:
            props = feature.get("properties", {})
            conn.execute(text("""
                INSERT INTO geo.official_susceptibility
                  (process_type, susceptibility_class, reference_year, source_url, properties, geom)
                VALUES (:process, :klass, :year, :url, CAST(:properties AS jsonb),
                        ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326))
            """), {
                "process": props.get("processo", "Suscetibilidade"),
                "klass": props.get("classe", "Não informado"),
                "year": props.get("ano"), "url": url,
                "properties": json.dumps(props, ensure_ascii=False),
                "geom": json.dumps(feature["geometry"]),
            })
    return len(features)
