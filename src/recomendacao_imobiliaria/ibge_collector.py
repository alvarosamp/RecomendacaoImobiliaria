"""
Coleta dados populacionais do IBGE para enriquecer features H3.

Fontes:
- IBGE Malhas API v3 (limites de setores censitários)
- IBGE SIDRA API (Censo 2022, tabela 9514, variável 93 = pessoas)

Fallback: quando o SIDRA não está disponível, a população municipal
é distribuída proporcionalmente ao NDBI (proxy de densidade urbana).
"""
from __future__ import annotations

import logging
from typing import Optional

import pandas as pd
import requests
from sqlalchemy import text

from .config import Settings, load_settings
from .db import db_engine

log = logging.getLogger(__name__)

IBGE_CITY_CODE = 3151800  # Pouso Alegre, MG

_MESH_URL = (
    "https://servicodados.ibge.gov.br/api/v3/malhas/municipios/{code}"
    "?resolucao=8&formato=geojson"
)
_SIDRA_SETORES_URL = (
    "https://apisidra.ibge.gov.br/values/t/9514/n9/in%20N6%20{code}/v/93/p/2022"
)
_IBGE_PROJ_URL = (
    "https://servicodados.ibge.gov.br/api/v1/pesquisas/indicadores/29171/resultados/{code}"
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _get_municipality_population(city_code: int = IBGE_CITY_CODE) -> int:
    """Retorna a estimativa de população municipal mais recente do IBGE."""
    try:
        resp = requests.get(_IBGE_PROJ_URL.format(code=city_code), timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if data and isinstance(data, list):
            serie = data[0].get("series", [{}])[0].get("serie", {})
            if serie:
                latest = max(serie.keys())
                raw = serie[latest].replace(".", "").replace(",", "")
                return int(raw)
    except Exception as exc:
        log.warning("IBGE projections API falhou: %s", exc)
    return 161_093  # resultado oficial Censo 2022 Pouso Alegre


def _fetch_setor_boundaries(city_code: int = IBGE_CITY_CODE) -> dict:
    """
    Baixa os polígonos de setores censitários do IBGE Malhas API.
    Retorna {codarea: shapely_geometry}.
    """
    from shapely.geometry import shape

    url = _MESH_URL.format(code=city_code)
    log.info("Baixando setores censitarios de %s ...", url)
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    data = resp.json()

    boundaries: dict = {}
    for feature in data.get("features", []):
        codarea = feature.get("properties", {}).get("codarea")
        geom_data = feature.get("geometry")
        if codarea and geom_data:
            try:
                boundaries[codarea] = shape(geom_data)
            except Exception:
                pass
    return boundaries


def _fetch_setor_population(city_code: int = IBGE_CITY_CODE) -> dict:
    """
    Busca a população por setor censitário via IBGE SIDRA (Censo 2022).
    Retorna {codarea: int}. Retorna {} em caso de falha.
    """
    url = _SIDRA_SETORES_URL.format(code=city_code)
    log.info("Consultando SIDRA para populacao por setor (%s)...", url)
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list) or len(data) < 2:
            return {}

        pop_map: dict = {}
        for row in data[1:]:  # primeiro elemento é cabeçalho
            # SIDRA usa chaves como D1C (código territorial) e V (valor)
            cod = row.get("D1C", "").strip()
            val = row.get("V", "").strip()
            if cod and val.isdigit():
                pop_map[cod] = int(val)
        log.info("  %d setores com dados de populacao.", len(pop_map))
        return pop_map
    except Exception as exc:
        log.warning("SIDRA setor population falhou: %s", exc)
        return {}


# ---------------------------------------------------------------------------
# public function
# ---------------------------------------------------------------------------


def estimate_h3_population(settings: Settings | None = None) -> int:
    """
    Calcula pop_estimated para cada célula H3 e salva em geo.features.

    Estratégia:
    1. Baixar limites de setores censitários (IBGE Mesh API).
    2. Buscar população por setor (SIDRA Censo 2022).
    3. Fallback: distribuir população municipal proporcionalmente ao NDBI.
    4. Intersecção espacial setores × H3 → pop_estimated por célula.

    Retorna número de células atualizadas.
    """
    import shapely.wkt

    settings = settings or load_settings()

    setor_geoms = _fetch_setor_boundaries()
    log.info("  %d setores encontrados.", len(setor_geoms))

    setor_pop = _fetch_setor_population()
    use_ndbi_proxy = len(setor_pop) == 0

    total_mun_pop: Optional[int] = None
    if use_ndbi_proxy:
        total_mun_pop = _get_municipality_population()
        log.info("SIDRA indisponivel — distribuicao por NDBI. Pop. municipal: %d", total_mun_pop)

    with db_engine(settings) as engine:
        with engine.begin() as conn:
            conn.execute(text(
                "ALTER TABLE geo.features ADD COLUMN IF NOT EXISTS pop_estimated INT"
            ))

        h3_df = pd.read_sql(
            "SELECT h3_id, ST_AsText(geom) AS wkt FROM geo.grid_h3",
            engine,
        )
        if h3_df.empty:
            log.warning("grid_h3 vazio — execute build-grid primeiro.")
            return 0

        if use_ndbi_proxy:
            feat_df = pd.read_sql(
                "SELECT h3_id, COALESCE(ndbi_mean_90, 0) AS ndbi FROM geo.features",
                engine,
            )
            denom = feat_df["ndbi"].sum() or 1.0
            feat_df["pop_estimated"] = (
                (feat_df["ndbi"] / denom) * total_mun_pop
            ).astype(int).clip(lower=1)
            updates = feat_df[["h3_id", "pop_estimated"]].to_dict(orient="records")
        else:
            h3_df["geom"] = h3_df["wkt"].apply(shapely.wkt.loads)
            updates = []
            for _, row in h3_df.iterrows():
                h3_geom = row["geom"]
                total = 0.0
                for codarea, setor_geom in setor_geoms.items():
                    if h3_geom.intersects(setor_geom):
                        try:
                            overlap = h3_geom.intersection(setor_geom)
                            frac = overlap.area / max(setor_geom.area, 1e-12)
                            total += setor_pop.get(codarea, 0) * frac
                        except Exception:
                            pass
                updates.append({"h3_id": row["h3_id"], "pop_estimated": max(1, int(total))})

        with engine.begin() as conn:
            for upd in updates:
                conn.execute(
                    text("""
                        INSERT INTO geo.features (h3_id, pop_estimated)
                        VALUES (:h3_id, :pop_estimated)
                        ON CONFLICT (h3_id) DO UPDATE
                            SET pop_estimated = EXCLUDED.pop_estimated
                    """),
                    upd,
                )

    log.info("pop_estimated atualizado para %d celulas.", len(updates))
    return len(updates)
