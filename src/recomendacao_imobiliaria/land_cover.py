"""Amostragem de cobertura do solo MapBiomas por centro de célula H3."""
from __future__ import annotations

import rasterio
from sqlalchemy import text

from .config import Settings, load_settings
from .db import db_engine

MAPBIOMAS_URL = "https://storage.googleapis.com/mapbiomas-public/initiatives/brasil/collection_10/lulc/coverage/brazil_coverage_{year}.tif"
CLASS_NAMES = {3: "formacao florestal", 4: "formacao savanica", 5: "mangue", 9: "floresta plantada", 11: "campo alagado", 12: "formacao campestre", 15: "pastagem", 18: "agricultura", 19: "lavoura temporaria", 20: "cana", 21: "mosaico de usos", 22: "area nao vegetada", 23: "praia e duna", 24: "area urbanizada", 25: "outras areas nao vegetadas", 29: "afloramento rochoso", 33: "corpo dagua", 39: "soja", 40: "arroz", 41: "outras lavouras", 46: "cafe", 49: "restinga arborea", 50: "restinga herbacea"}


def collect_mapbiomas_land_cover(year: int = 2024, settings: Settings | None = None) -> int:
    settings = settings or load_settings()
    with db_engine(settings) as engine, engine.connect() as conn:
        cells = conn.execute(text("SELECT h3_id, ST_X(ST_Centroid(geom)), ST_Y(ST_Centroid(geom)) FROM geo.grid_h3")).all()
    url = MAPBIOMAS_URL.format(year=year)
    with rasterio.Env(CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif"):
        with rasterio.open(url) as dataset:
            samples = list(dataset.sample([(float(x), float(y)) for _, x, y in cells]))
    with db_engine(settings) as engine, engine.begin() as conn:
        for (h3_id, _, _), sample in zip(cells, samples):
            code = int(sample[0])
            conn.execute(text("""
              INSERT INTO geo.land_cover_h3_history(h3_id,reference_year,class_code,class_name,collected_at)
              VALUES (:h3,:year,:code,:name,now())
              ON CONFLICT (h3_id,reference_year) DO UPDATE SET class_code=EXCLUDED.class_code,class_name=EXCLUDED.class_name,collected_at=now()
            """), {"h3": h3_id, "code": code, "name": CLASS_NAMES.get(code, f"classe {code}"), "year": year})
            conn.execute(text("""
              INSERT INTO geo.land_cover_h3(h3_id,class_code,class_name,reference_year,updated_at)
              VALUES (:h3,:code,:name,:year,now())
              ON CONFLICT (h3_id) DO UPDATE SET class_code=EXCLUDED.class_code,class_name=EXCLUDED.class_name,reference_year=EXCLUDED.reference_year,updated_at=now()
            """), {"h3": h3_id, "code": code, "name": CLASS_NAMES.get(code, f"classe {code}"), "year": year})
    return len(cells)
