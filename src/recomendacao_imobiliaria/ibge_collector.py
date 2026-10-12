"""
Coleta dados populacionais do IBGE para enriquecer features H3.

Estratégias em cascata (a mais robusta primeiro):
1. Setores censitários (IBGE Mesh API) + população por setor (SIDRA)
   com join espacial via PostGIS.
2. Distribuição por NDBI (proxy de densidade urbana × população municipal).
3. Distribuição uniforme como último recurso.

Falhas de disponibilidade retornam 0; identidade municipal divergente e
falhas de registro de procedencia interrompem a operacao.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

import pandas as pd
import requests
from sqlalchemy import text

from .config import Settings, load_settings
from .db import db_engine
from .municipality import MUNICIPALITY, MunicipalityMismatch
from .data_registry import ensure_data_schema, record_data_source

log = logging.getLogger(__name__)

IBGE_CITY_CODE = int(MUNICIPALITY.ibge_code)
_POUSO_ALEGRE_POP_2022 = 152_217  # Censo 2022, segunda apuracao publicada em 22/12/2023
_CENSUS_REFERENCE_URI = (
    "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/"
    "Populacao_e_domicilios_Primeiros_resultados/Resultados_da_2a_apuracao_20231027/"
    "POP2022_Municipios_Primeiros_Resultados_20231222.pdf"
)

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


@dataclass(frozen=True)
class PopulationEstimate:
    value: int
    source: str
    reference_year: int
    quality: str
    source_uri: str | None = None


def _get_population_estimate(city_code: int = IBGE_CITY_CODE) -> PopulationEstimate:
    """Mantem origem e ano inclusive quando a API nao esta disponivel."""
    MUNICIPALITY.validate_code(city_code)
    try:
        resp = requests.get(_IBGE_PROJ_URL.format(code=city_code), timeout=20)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list) and data:
            series = data[0].get("series") or []
            if not series:
                raise ValueError("IBGE sem serie populacional")
            returned_code = series[0].get("localidade", {}).get("id")
            if returned_code is not None:
                MUNICIPALITY.validate_code(returned_code)
            serie = series[0].get("serie", {})
            if serie:
                latest = max(serie.keys())
                raw = serie[latest].replace(".", "").replace(",", "")
                population = int(raw)
                if population <= 0:
                    raise ValueError("Populacao municipal invalida")
                return PopulationEstimate(population, "IBGE API", int(latest), "provider_estimate",
                                          _IBGE_PROJ_URL.format(code=city_code))
    except MunicipalityMismatch:
        raise
    except Exception as exc:
        log.debug("IBGE projections API falhou: %s", exc)
    log.warning("Usando referencia populacional fixa de 2022; nao e observacao atual.")
    return PopulationEstimate(_POUSO_ALEGRE_POP_2022, "referencia fixa Censo 2022", 2022,
                              "static_reference", _CENSUS_REFERENCE_URI)


def _get_municipality_population(city_code: int = IBGE_CITY_CODE) -> int:
    """Compatibilidade para callers que precisam somente do valor."""
    return _get_population_estimate(city_code).value


def _fetch_setor_boundaries(city_code: int = IBGE_CITY_CODE) -> dict:
    """
    Baixa polígonos de setores do IBGE Mesh API.
    Retorna {codarea: shapely_geom}. Levanta exceção em falha.
    """
    from shapely.geometry import shape

    MUNICIPALITY.validate_code(city_code)
    url = _MESH_URL.format(code=city_code)
    resp = requests.get(url, timeout=90)
    resp.raise_for_status()
    data = resp.json()

    out: dict = {}
    for feat in data.get("features", []):
        codarea = feat.get("properties", {}).get("codarea")
        geom_data = feat.get("geometry")
        if codarea and geom_data:
            codarea = str(codarea)
            MUNICIPALITY.validate_sector(codarea)
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
    MUNICIPALITY.validate_code(city_code)
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
                    MUNICIPALITY.validate_sector(cod)
                    pop_map[cod] = int(val)
            if pop_map:
                log.info("SIDRA: %d setores com população.", len(pop_map))
                return pop_map
        except MunicipalityMismatch:
            raise
        except Exception as exc:
            log.debug("SIDRA URL %s falhou: %s", url, exc)

    return {}


# ── strategies ─────────────────────────────────────────────────────────────


def _try_setor_approach(settings: Settings, estimate: PopulationEstimate | None = None) -> int:
    """
    Join espacial setores × H3 via Python (shapely).
    Retorna count de células atualizadas. Levanta exceção em falha.
    """
    import shapely.wkt

    setor_geoms = _fetch_setor_boundaries()
    setor_pop   = _fetch_setor_population()

    # Without per-setor population, fall back to distributing municipality
    # total proportionally to setor area within each cell.
    estimate = estimate or _get_population_estimate()
    total_mun = estimate.value if not setor_pop else None
    if setor_pop and not (set(setor_geoms) & set(setor_pop)):
        raise ValueError("Setores e populacao nao possuem identificadores em comum")

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
            updates.append({"h3_id": row["h3_id"], "pop_estimated": max(0, int(cell_pop))})

        _upsert_pop(engine, updates, settings=settings,
                    method="sector_intersection" if setor_pop else "sector_area_proxy", estimate=estimate)
    return len(updates)


def _allocate_population(weights: pd.Series, total_pop: int) -> pd.Series:
    """Arredondamento por maiores restos: conserva o total, inclusive com zeros."""
    if total_pop < 0 or weights.empty:
        raise ValueError("Total ou pesos populacionais invalidos")
    weights = pd.to_numeric(weights, errors="coerce").fillna(0).clip(lower=0)
    if not weights.sum():
        weights = pd.Series(1.0, index=weights.index)
    shares = weights / weights.sum() * total_pop
    counts = shares.astype(int)
    remainder = total_pop - int(counts.sum())
    order = (shares - counts).sort_values(ascending=False, kind="stable").index[:remainder]
    counts.loc[order] += 1
    return counts


def _ndbi_proxy_approach(settings: Settings, total_pop: int, estimate: PopulationEstimate) -> int:
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
            grid["pop_estimated"] = _allocate_population(pd.Series(1.0, index=grid.index), total_pop)
            updates = grid[["h3_id", "pop_estimated"]].to_dict(orient="records")
            method = "uniform_proxy"
        else:
            # Shift NDBI up so all weights are positive
            feat["weight"] = feat["ndbi"].clip(lower=0) + 0.01
            feat["pop_estimated"] = _allocate_population(feat["weight"], total_pop)
            updates = feat[["h3_id", "pop_estimated"]].to_dict(orient="records")
            method = "ndbi_proxy"

        _upsert_pop(engine, updates, settings=settings, method=method, estimate=estimate)
    return len(updates)


def _upsert_pop(engine, updates: list[dict], *, settings: Settings, method: str, estimate: PopulationEstimate) -> None:
    """Upsert pop_estimated into geo.features, adding the column if missing."""
    ensure_data_schema(settings)
    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE geo.features ADD COLUMN IF NOT EXISTS pop_estimated INT"
        ))
        if updates:
            conn.execute(
                text("""
                    INSERT INTO geo.features (h3_id, pop_estimated)
                    VALUES (:h3_id, :pop_estimated)
                    ON CONFLICT (h3_id) DO UPDATE
                        SET pop_estimated = EXCLUDED.pop_estimated
                """),
                updates,
            )
        _record_population(settings, len(updates), method, estimate, connection=conn)


# ── public entry point ─────────────────────────────────────────────────────


def estimate_h3_population(settings: Settings | None = None) -> int:
    """
    Estima população por célula H3 e salva em geo.features.pop_estimated.
    Disponibilidade pode usar proxies declarados; municipio divergente e rejeitado.
    Retorna número de células atualizadas (0 se tudo falhar).
    """
    settings = settings or load_settings()
    estimate = _get_population_estimate()
    total_pop = estimate.value

    # Strategy 1 — setor spatial join (best precision)
    try:
        count = _try_setor_approach(settings, estimate)
        if count > 0:
            log.info("pop_estimated via setores censitários: %d células.", count)
            return count
    except MunicipalityMismatch:
        raise
    except Exception as exc:
        log.warning("Estratégia por setores falhou (%s) — usando proxy NDBI.", exc)

    # Strategy 2 — NDBI proxy
    try:
        count = _ndbi_proxy_approach(settings, total_pop, estimate)
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
            grid["pop_estimated"] = _allocate_population(pd.Series(1.0, index=grid.index), total_pop)
            updates = grid[["h3_id", "pop_estimated"]].to_dict(orient="records")
            _upsert_pop(engine, updates, settings=settings, method="uniform_proxy", estimate=estimate)
        log.info("pop_estimated uniforme: %d moradores distribuidos em %d celulas.", total_pop, len(updates))
        return len(updates)
    except Exception as exc:
        log.error("Todas as estratégias falharam: %s", exc)
        return 0


def _record_population(settings: Settings, count: int, method: str, estimate: PopulationEstimate, *, connection=None) -> None:
    record_data_source(
        "h3_population", estimate.source, row_count=count,
        source_uri=estimate.source_uri,
        reference_date=date(estimate.reference_year, 1, 1), settings=settings, connection=connection,
        details={"municipality_code": MUNICIPALITY.ibge_code, "method": method,
                 "quality": "estimated", "total_population": estimate.value,
                 "total_source_quality": estimate.quality, "reference_year": estimate.reference_year},
    )
