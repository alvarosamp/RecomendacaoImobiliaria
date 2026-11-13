"""
Coleta dados populacionais do IBGE para enriquecer features H3.

Estratégias em cascata (a mais robusta primeiro):
1. Censo 2022 por setor censitário (malha em GeoPackage + agregados em CSV),
   repartido nas células H3 por área (ver ``census_population``).
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

IBGE_CITY_CODE = 3152501  # Pouso Alegre/MG (3151800 é Poços de Caldas)
_POUSO_ALEGRE_POP_2022 = 152_217  # Censo 2022 (SIDRA 4709, var. 93) — fallback hardcoded

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
            serie = _extract_population_series(data[0])
            if serie:
                latest = max(serie.keys())
                raw = str(serie[latest]).replace(".", "").replace(",", "")
                return int(raw)
    except Exception as exc:
        log.debug("IBGE projections API falhou: %s", exc)
    return _POUSO_ALEGRE_POP_2022


def _extract_population_series(item: dict) -> dict:
    """Série {ano: valor} do indicador 29171.

    A API de pesquisas devolve ``res[].res``; o formato ``series[].serie``
    é aceito por compatibilidade com respostas no padrão SIDRA.
    """
    for outer, inner in (("res", "res"), ("series", "serie")):
        blocks = item.get(outer) or []
        if blocks and isinstance(blocks[0], dict):
            serie = blocks[0].get(inner) or {}
            serie = {year: value for year, value in serie.items() if value not in (None, "", "-", "...")}
            if serie:
                return serie
    return {}


# ── strategies ─────────────────────────────────────────────────────────────


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

    # Strategy 1 — Censo 2022 por setor censitário (população real, conserva o total)
    try:
        from .census_population import collect_census_population

        report = collect_census_population(settings=settings, progress=log.info)
        log.info("pop_estimated via setores do Censo 2022: %d células.", report["cells"])
        return int(report["cells"])
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
