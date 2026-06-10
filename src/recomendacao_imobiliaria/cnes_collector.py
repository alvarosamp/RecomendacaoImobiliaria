"""
Coleta estabelecimentos de saúde do CNES (Cadastro Nacional de
Estabelecimentos de Saúde — DataSUS) e insere em geo.osm_pois.

Tenta o endpoint público do site CNES. Se indisponível, cai para
uma query OSM com a tag `healthcare` (osmnx), que captura
estabelecimentos não rotulados em `amenity=pharmacy/hospital`.

Os registros CNES/healthcare são inseridos com category='cnes' para
diferenciar da fonte OSM padrão (category='amenity' / 'shop').
"""
from __future__ import annotations

import logging
import time
from typing import Optional

import requests
from sqlalchemy import text

from .config import Settings, load_settings
from .db import db_engine

log = logging.getLogger(__name__)

# Código IBGE 6-dígitos do município (sem dígito verificador)
POUSO_ALEGRE_MUN_CODE = "315180"

# Tentativas de endpoint do site CNES (podem mudar com o tempo)
_CNES_ENDPOINTS = [
    "https://cnes.datasus.gov.br/services/estabelecimentos",
    "https://apidadosnet.datasus.gov.br/api/estabelecimentos",
]

_CNES_TIPO_MAP = {
    "FARMACIA": "pharmacy",
    "DROGARIA": "pharmacy",
    "HOSPITAL": "hospital",
    "UBS": "clinic",
    "CLINICA": "clinic",
    "LABORATORIO": "clinic",
    "POSTO DE SAUDE": "clinic",
    "CENTRO DE SAUDE": "clinic",
    "UNIDADE BASICA": "clinic",
    "UPA": "hospital",
    "PRONTO SOCORRO": "hospital",
}

_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


def _try_cnes_api(mun_code: str = POUSO_ALEGRE_MUN_CODE) -> list[dict]:
    """
    Tenta baixar estabelecimentos via API do site CNES.
    Retorna lista de dicts com {name, subcategory, lat, lon}.
    Retorna [] se a API não estiver disponível ou sem coordenadas.
    """
    params = {"municipio": mun_code, "page": 0, "size": 500, "fl_ativo": "S"}
    headers = {"Accept": "application/json", "User-Agent": "recomendacao-imobiliaria/1.0"}

    for url in _CNES_ENDPOINTS:
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=20)
            if resp.status_code not in (200, 201):
                continue
            data = resp.json()

            # Normaliza: aceita {content: [...]} ou lista direta
            items = data if isinstance(data, list) else data.get("content", data.get("items", []))
            if not items:
                continue

            results = []
            for item in items:
                lat = item.get("latDecimal") or item.get("latitude") or item.get("lat")
                lon = item.get("lonDecimal") or item.get("longitude") or item.get("lng") or item.get("lon")
                if not lat or not lon:
                    continue

                nome = item.get("noFantasia") or item.get("nome") or item.get("noCNES", "")
                tipo_raw = (item.get("tipoUnidade") or item.get("dstipoUnidade") or "").upper()
                subcategory = next(
                    (v for k, v in _CNES_TIPO_MAP.items() if k in tipo_raw),
                    "clinic",
                )
                results.append({
                    "name": nome,
                    "subcategory": subcategory,
                    "lat": float(lat),
                    "lon": float(lon),
                })

            if results:
                log.info("CNES API (%s): %d estabelecimentos com coordenadas.", url, len(results))
                return results
        except Exception as exc:
            log.debug("CNES endpoint %s falhou: %s", url, exc)

    return []


def _geocode_address(address: str, city: str = "Pouso Alegre, MG") -> Optional[tuple[float, float]]:
    """Geocodifica um endereço via Nominatim. Respeita o rate-limit (1 req/s)."""
    try:
        time.sleep(1.1)  # Nominatim policy: 1 req/s
        resp = requests.get(
            _NOMINATIM_URL,
            params={"q": f"{address}, {city}, Brasil", "format": "json", "limit": 1},
            headers={"User-Agent": "recomendacao-imobiliaria/1.0"},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception as exc:
        log.debug("Geocoding falhou para '%s': %s", address, exc)
    return None


def _cnes_via_osm_healthcare(settings: Settings) -> list[dict]:
    """
    Fallback: busca estabelecimentos de saúde via OSM com a tag `healthcare`.
    Captura farmácias/hospitais/clínicas que não usam `amenity=*`.
    """
    import pandas as pd
    import osmnx as ox

    try:
        boundary = pd.read_sql(
            "SELECT ST_AsText(ST_Union(geom)) AS wkt FROM geo.city_boundary",
            _engine_from(settings),
        )
        if boundary.empty or not boundary.loc[0, "wkt"]:
            return []

        from shapely import wkt
        geom = wkt.loads(boundary.loc[0, "wkt"])

        healthcare_map = {
            "pharmacy": "pharmacy",
            "hospital": "hospital",
            "clinic": "clinic",
            "doctor": "clinic",
            "dentist": "clinic",
            "laboratory": "clinic",
        }
        pois = ox.features_from_polygon(geom, tags={"healthcare": list(healthcare_map.keys())})
        if pois.empty:
            return []

        results = []
        for _, row in pois.reset_index().iterrows():
            geom_pt = row.geometry
            if geom_pt is None or geom_pt.is_empty:
                continue
            if geom_pt.geom_type != "Point":
                geom_pt = geom_pt.representative_point()
            hc_val = str(row.get("healthcare", "clinic")).lower()
            subcategory = healthcare_map.get(hc_val, "clinic")
            results.append({
                "name": str(row.get("name", "")) or None,
                "subcategory": subcategory,
                "lat": geom_pt.y,
                "lon": geom_pt.x,
            })
        return results
    except Exception as exc:
        log.warning("OSM healthcare fallback falhou: %s", exc)
        return []


def _engine_from(settings: Settings):
    from .db import make_engine
    return make_engine(settings)


# ---------------------------------------------------------------------------
# public function
# ---------------------------------------------------------------------------


def fetch_cnes_establishments(settings: Settings | None = None) -> int:
    """
    Busca estabelecimentos de saúde (CNES ou OSM healthcare) e insere em geo.osm_pois.

    Ordem de tentativa:
    1. API pública do site CNES (com coordenadas)
    2. OSM com tag `healthcare` via osmnx

    Retorna número de registros inseridos.
    """
    from shapely.geometry import Point

    settings = settings or load_settings()

    log.info("Buscando estabelecimentos de saude CNES...")
    records = _try_cnes_api()

    if not records:
        log.info("CNES API sem resultado — tentando OSM healthcare...")
        records = _cnes_via_osm_healthcare(settings)

    if not records:
        log.warning("Nenhum estabelecimento CNES/healthcare encontrado.")
        return 0

    with db_engine(settings) as engine:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM geo.osm_pois WHERE category = 'cnes'"))
            count = 0
            for rec in records:
                point = Point(rec["lon"], rec["lat"])
                conn.execute(
                    text("""
                        INSERT INTO geo.osm_pois (name, category, subcategory, geom)
                        VALUES (
                            :name, 'cnes', :subcategory,
                            ST_SetSRID(ST_GeomFromText(:wkt), 4326)
                        )
                    """),
                    {"name": rec.get("name"), "subcategory": rec["subcategory"], "wkt": point.wkt},
                )
                count += 1

    log.info("CNES/healthcare: %d estabelecimentos inseridos.", count)
    return count
