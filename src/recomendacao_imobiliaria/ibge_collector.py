"""
Coleta dados populacionais do IBGE para enriquecer features H3.

Estratégias em cascata (a mais robusta primeiro):
1. Setores censitários (IBGE Mesh API) + população por setor (SIDRA)
   com join espacial via PostGIS.
2. Distribuição por NDBI (proxy de densidade urbana × população municipal).
3. Distribuição uniforme como último recurso.

Nunca levanta exceção para o caller — registra warning e retorna 0 em
caso de falha total.
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

IBGE_CITY_CODE = 3151800
_POUSO_ALEGRE_POP_2022 = 161_093  # Censo 2022 — fallback hardcoded

_MESH_URL = (
    "https://servicodados.ibge.gov.br/api/v3/malhas/municipios/{code}"
    "?resolucao=8&formato=geojson"
)
# Tries two SIDRA table candidates for population by setor censitário
_SIDRA_URLS = [
    "https://apisidra.ibge.gov.br/values/t/4709/n9/in%20N6%20{code}/v/93/p/2022",
    "https://apisidra.ibge.gov.br/values/t/9514/n9/in%20N6%20{code}/v/93/p/2022",
]
_IBGE_PROJ_URL = (
    "https://servicodados.ibge.gov.br/api/v1/pesquisas/indicadores/29171/resultados/{code}"
)


# ── helpers ────────────────────────────────────────────────────────────────


def _get_municipality_population(city_code: int = IBGE_CITY_CODE) -> int:
    """Retorna estimativa de população municipal (IBGE) com fallback hardcoded."""
    try:
        resp = requests.get(_IBGE_PROJ_URL.format(code=city_code), timeout=20)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list) and data:
            serie = data[0].get("series", [{}])[0].get("serie", {})
            if serie:
                latest = max(serie.keys())
                raw = serie[latest].replace(".", "").replace(",", "")
                return int(raw)
    except Exception as exc:
        log.debug("IBGE projections API falhou: %s", exc)
    return _POUSO_ALEGRE_POP_2022


def _fetch_setor_boundaries(city_code: int = IBGE_CITY_CODE) -> dict:
    """
    Baixa polígonos de setores do IBGE Mesh API.
    Retorna {codarea: shapely_geom}. Levanta exceção em falha.
    """
    from shapely.geometry import shape

    url = _MESH_URL.format(code=city_code)
    resp = requests.get(url, timeout=90)
    resp.raise_for_status()
    data = resp.json()

    out: dict = {}
    for feat in data.get("features", []):
        codarea = feat.get("properties", {}).get("codarea")
        geom_data = feat.get("geometry")
        if codarea and geom_data:
            try:
                out[codarea] = shape(geom_data)
            except Exception:
                pass
    if not out:
        raise ValueError("Nenhum setor retornado pela Mesh API")
    return out


def _fetch_setor_population(city_code: int = IBGE_CITY_CODE) -> dict:
    """
    Tenta SIDRA para população por setor. Retorna {} em falha (não levanta).
    """
    for url_tpl in _SIDRA_URLS:
        url = url_tpl.format(code=city_code)
        try:
            resp = requests.get(url, timeout=45)
            if resp.status_code != 200:
                continue
            data = resp.json()
            if not isinstance(data, list) or len(data) < 2:
                continue

            pop_map: dict = {}
            for row in data[1:]:  # row 0 = header
                # SIDRA returns different key names — try all known patterns
                cod = (
                    row.get("D1C") or row.get("codarea") or
                    row.get("D1N") or ""
                ).strip()
                val = str(row.get("V", "")).strip()
                if cod and val.isdigit():
                    pop_map[cod] = int(val)
            if pop_map:
                log.info("SIDRA: %d setores com população.", len(pop_map))
                return pop_map
        except Exception as exc:
            log.debug("SIDRA URL %s falhou: %s", url, exc)

    return {}


# ── strategies ─────────────────────────────────────────────────────────────


def _try_setor_approach(settings: Settings) -> int:
    """
    Join espacial setores × H3 via Python (shapely).
    Retorna count de células atualizadas. Levanta exceção em falha.
    """
    import shapely.wkt

    setor_geoms = _fetch_setor_boundaries()
    setor_pop   = _fetch_setor_population()

    # Without per-setor population, fall back to distributing municipality
    # total proportionally to setor area within each cell.
    total_mun = _get_municipality_population() if not setor_pop else None

    with db_engine(settings) as engine:
        h3_df = pd.read_sql(
            "SELECT h3_id, ST_AsText(geom) AS wkt FROM geo.grid_h3",
            engine,
        )
        if h3_df.empty:
            raise ValueError("grid_h3 vazio")

        h3_df["geom"] = h3_df["wkt"].apply(shapely.wkt.loads)
        total_setor_area = sum(g.area for g in setor_geoms.values()) or 1.0

        updates: list[dict] = []
        for _, row in h3_df.iterrows():
            h3_geom = row["geom"]
            cell_pop = 0.0
            for codarea, s_geom in setor_geoms.items():
                if not h3_geom.intersects(s_geom):
                    continue
                try:
                    overlap = h3_geom.intersection(s_geom)
                    frac = overlap.area / max(s_geom.area, 1e-14)
                    frac = min(frac, 1.0)
                    if setor_pop:
                        cell_pop += setor_pop.get(codarea, 0) * frac
                    else:
                        # area-proportional share of total municipality pop
                        cell_pop += total_mun * (s_geom.area / total_setor_area) * frac
                except Exception:
                    pass
            updates.append({"h3_id": row["h3_id"], "pop_estimated": max(1, int(cell_pop))})

        _upsert_pop(engine, updates)
    return len(updates)


def _ndbi_proxy_approach(settings: Settings, total_pop: int) -> int:
    """
    Distribui total_pop proporcionalmente ao NDBI de cada célula.
    NDBI ≈ densidade urbana (quanto mais alto, mais construído).
    """
    with db_engine(settings) as engine:
        feat = pd.read_sql(
            "SELECT h3_id, COALESCE(ndbi_mean_90, 0) AS ndbi FROM geo.features",
            engine,
        )
        if feat.empty:
            # No features yet → uniform approach
            grid = pd.read_sql("SELECT h3_id FROM geo.grid_h3", engine)
            if grid.empty:
                return 0
            per_cell = max(1, total_pop // len(grid))
            updates = [{"h3_id": r, "pop_estimated": per_cell} for r in grid["h3_id"]]
        else:
            # Shift NDBI up so all weights are positive
            feat["weight"] = feat["ndbi"].clip(lower=0) + 0.01
            denom = feat["weight"].sum() or 1.0
            feat["pop_estimated"] = ((feat["weight"] / denom) * total_pop).astype(int).clip(lower=1)
            updates = feat[["h3_id", "pop_estimated"]].to_dict(orient="records")

        _upsert_pop(engine, updates)
    return len(updates)


def _upsert_pop(engine, updates: list[dict]) -> None:
    """Upsert pop_estimated into geo.features, adding the column if missing."""
    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE geo.features ADD COLUMN IF NOT EXISTS pop_estimated INT"
        ))
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


# ── public entry point ─────────────────────────────────────────────────────


def estimate_h3_population(settings: Settings | None = None) -> int:
    """
    Estima população por célula H3 e salva em geo.features.pop_estimated.
    Nunca levanta exceção — usa a melhor estratégia disponível.
    Retorna número de células atualizadas (0 se tudo falhar).
    """
    settings = settings or load_settings()
    total_pop = _get_municipality_population()

    # Strategy 1 — setor spatial join (best precision)
    try:
        count = _try_setor_approach(settings)
        if count > 0:
            log.info("pop_estimated via setores censitários: %d células.", count)
            return count
    except Exception as exc:
        log.warning("Estratégia por setores falhou (%s) — usando proxy NDBI.", exc)

    # Strategy 2 — NDBI proxy
    try:
        count = _ndbi_proxy_approach(settings, total_pop)
        log.info("pop_estimated via NDBI proxy: %d células.", count)
        return count
    except Exception as exc:
        log.warning("Proxy NDBI falhou (%s) — distribuição uniforme.", exc)

    # Strategy 3 — uniform fallback
    try:
        with db_engine(settings) as engine:
            grid = pd.read_sql("SELECT h3_id FROM geo.grid_h3", engine)
            if grid.empty:
                return 0
            per_cell = max(1, total_pop // len(grid))
            updates = [{"h3_id": r, "pop_estimated": per_cell} for r in grid["h3_id"]]
            _upsert_pop(engine, updates)
        log.info("pop_estimated uniforme (%d/célula): %d células.", per_cell, len(updates))
        return len(updates)
    except Exception as exc:
        log.error("Todas as estratégias falharam: %s", exc)
        return 0
