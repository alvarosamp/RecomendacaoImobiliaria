"""Populacao do Censo 2022 por setor censitario, distribuida nas celulas H3.

Fontes (IBGE, dados abertos, sem chave):

* malha de setores censitarios por UF (GeoPackage), com um poligono por setor;
* agregados por setor, tabela "basico" (CSV nacional dentro de um ZIP):
  ``V0001`` total de pessoas e ``V0007`` domicilios particulares ocupados.

Cada setor e repartido entre as celulas H3 que ele cobre, proporcionalmente a area
da interseccao. A parcela de cada setor e normalizada pela area que cai dentro da
grade, entao a populacao total e conservada e nenhuma celula recebe mais gente do
que o setor tem. O resultado vai para ``geo.census_h3`` (o que o diagnostico de
governo ja le) e para ``geo.features.pop_estimated``.

Limite conhecido: a divisao e por area, sem considerar onde ha casas dentro do
setor. Em setores urbanos (pequenos) o erro e baixo; em setores rurais grandes a
populacao fica espalhada por toda a area, inclusive mata e lavoura.
"""
from __future__ import annotations

import hashlib
import io
import re
import zipfile
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

GEO_URL = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/"
    "malhas_de_setores_censitarios__divisoes_intramunicipais/censo_2022/setores/gpkg/UF/{uf}/{uf}_setores_CD2022.gpkg"
)
AGGREGATES_DIR = (
    "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/Agregados_por_Setores_Censitarios/Agregados_por_Setor_csv/"
)
# Usado se a listagem da pasta nao puder ser lida; o nome muda quando o IBGE revisa o arquivo.
AGGREGATES_FALLBACK = AGGREGATES_DIR + "Agregados_por_setores_basico_BR_20260520.zip"
SIDRA_POPULATION_URL = "https://apisidra.ibge.gov.br/values/t/4709/n6/{code}/v/93/p/2022"
CENSUS_REFERENCE_DATE = date(2022, 8, 1)
DEFAULT_CACHE_DIR = Path("data/cache/censo2022")
SOURCE_NAME = "IBGE Censo Demografico 2022 - agregados por setor censitario"

UF_BY_CODE = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO", "21": "MA", "22": "PI",
    "23": "CE", "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES",
    "33": "RJ", "35": "SP", "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF",
}
_HEADERS = {"User-Agent": "urbia-census-collector/1.0"}


def check_ibge_code(ibge_code: str) -> str:
    code = str(ibge_code).strip()
    if not re.fullmatch(r"\d{7}", code):
        raise ValueError(f"Codigo IBGE de municipio deve ter 7 digitos: {ibge_code!r}")
    if code[:2] not in UF_BY_CODE:
        raise ValueError(f"Codigo IBGE com UF desconhecida: {ibge_code!r}")
    return code


def uf_of(ibge_code: str) -> str:
    return UF_BY_CODE[check_ibge_code(ibge_code)[:2]]


# ---------------------------------------------------------------------------
# Download com cache
# ---------------------------------------------------------------------------

def latest_aggregates_url(listing_html: str) -> str | None:
    """Arquivo ``Agregados_por_setores_basico_BR*.zip`` mais recente de uma listagem de pasta."""
    names = re.findall(r'href="(Agregados_por_setores_basico_BR[^"/]*\.zip)"', listing_html)
    if not names:
        return None
    dated = [(re.search(r"_(\d{8})\.zip$", name), name) for name in names]
    dated = [(match.group(1), name) for match, name in dated if match]
    return AGGREGATES_DIR + (max(dated)[1] if dated else sorted(names)[-1])


def resolve_aggregates_url(progress=print) -> str:
    import requests

    try:
        response = requests.get(AGGREGATES_DIR, headers=_HEADERS, timeout=40)
        response.raise_for_status()
        url = latest_aggregates_url(response.text)
        if url:
            return url
    except Exception as exc:  # a listagem e uma conveniencia; o nome fixo ainda vale
        progress(f"  aviso: listagem do IBGE indisponivel ({exc}); usando o arquivo conhecido.")
    return AGGREGATES_FALLBACK


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def download(url: str, target: Path, *, kind: str, refresh: bool = False, progress=print) -> Path:
    """Baixa ``url`` para ``target`` (escrita atomica), validando o tipo do arquivo."""
    import requests

    if target.exists() and target.stat().st_size > 0 and not refresh:
        progress(f"  {target.name}: ja em cache")
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + ".part")
    progress(f"  baixando {url} ...")
    with requests.get(url, headers=_HEADERS, stream=True, timeout=(15, 120)) as response:
        response.raise_for_status()
        with partial.open("wb") as stream:
            for block in response.iter_content(1 << 20):
                stream.write(block)
    if kind == "zip" and not zipfile.is_zipfile(partial):
        partial.unlink(missing_ok=True)
        raise RuntimeError(f"O arquivo baixado de {url} nao e um ZIP valido.")
    if kind == "gpkg" and partial.read_bytes()[:15] != b"SQLite format 3":
        partial.unlink(missing_ok=True)
        raise RuntimeError(f"O arquivo baixado de {url} nao e um GeoPackage valido.")
    partial.replace(target)
    return target


# ---------------------------------------------------------------------------
# Leitura
# ---------------------------------------------------------------------------

def read_sector_population(zip_path: Path | str, ibge_code: str) -> pd.DataFrame:
    """Populacao e domicilios ocupados por setor de um municipio (colunas cd_setor, population, households)."""
    code = check_ibge_code(ibge_code)
    pieces = []
    with zipfile.ZipFile(zip_path) as archive:
        names = [name for name in archive.namelist() if name.lower().endswith(".csv")]
        if not names:
            raise RuntimeError("O ZIP de agregados nao contem CSV.")
        with archive.open(names[0]) as raw:
            reader = pd.read_csv(raw, sep=";", encoding="latin-1", dtype=str, chunksize=100_000,
                                 usecols=lambda column: column.lower() in {"cd_setor", "cd_mun", "v0001", "v0007"})
            for chunk in reader:
                chunk.columns = [column.lower() for column in chunk.columns]
                pieces.append(chunk[chunk["cd_mun"] == code])
    frame = pd.concat(pieces, ignore_index=True) if pieces else pd.DataFrame(columns=["cd_setor", "cd_mun", "v0001", "v0007"])
    if frame.empty:
        raise RuntimeError(f"Nenhum setor encontrado para o municipio {code} nos agregados do Censo 2022.")
    # O IBGE marca valor ausente/sigiloso com "." ou "X".
    numeric = lambda column: pd.to_numeric(frame[column].where(~frame[column].isin([".", "X", "-", ""])), errors="coerce")  # noqa: E731
    result = pd.DataFrame({
        "cd_setor": frame["cd_setor"].astype(str).str.strip(),
        "population": numeric("v0001"),
        "households": numeric("v0007"),
    })
    return result.drop_duplicates("cd_setor").reset_index(drop=True)


def read_sector_geometry(gpkg_path: Path | str, ibge_code: str):
    """Poligonos dos setores de um municipio, em WGS84."""
    import pyogrio

    code = check_ibge_code(ibge_code)
    sectors = pyogrio.read_dataframe(str(gpkg_path), where=f"CD_MUN = '{code}'", columns=["CD_SETOR", "CD_MUN", "SITUACAO"])
    if sectors.empty:
        raise RuntimeError(f"Nenhum poligono de setor para o municipio {code} na malha do IBGE.")
    sectors = sectors.rename(columns={"CD_SETOR": "cd_setor"})
    sectors["cd_setor"] = sectors["cd_setor"].astype(str).str.strip()
    sectors["geometry"] = sectors.geometry.make_valid()
    return sectors.to_crs(4326)


def official_population(ibge_code: str) -> int | None:
    """Populacao total do Censo 2022 do municipio (SIDRA, tabela 4709); None se a API falhar."""
    import requests

    try:
        response = requests.get(SIDRA_POPULATION_URL.format(code=check_ibge_code(ibge_code)), headers=_HEADERS, timeout=40)
        response.raise_for_status()
        return int(float(response.json()[1]["V"]))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Distribuicao nas celulas
# ---------------------------------------------------------------------------

def metric_crs(geometries) -> int:
    """UTM da zona central dos dados, para calcular areas."""
    center = geometries.union_all().centroid if hasattr(geometries, "union_all") else geometries.unary_union.centroid
    zone = int((center.x + 180) // 6) + 1
    return (32700 if center.y < 0 else 32600) + zone


def allocate_to_cells(sectors, cells) -> tuple[pd.DataFrame, dict[str, object]]:
    """Reparte populacao e domicilios de cada setor entre as celulas, por area de interseccao.

    ``sectors``: GeoDataFrame com ``cd_setor``, ``population`` e ``households``.
    ``cells``: GeoDataFrame com ``h3_id``. Ambos no mesmo CRS (em metros).
    """
    import geopandas as gpd

    sectors = sectors[["cd_setor", "population", "households", "geometry"]].copy()
    sectors["population"] = sectors["population"].fillna(0.0)
    sectors["households"] = sectors["households"].fillna(0.0)
    pieces = gpd.overlay(sectors, cells[["h3_id", "geometry"]], how="intersection", keep_geom_type=True)
    pieces["piece_area"] = pieces.geometry.area
    pieces = pieces[pieces["piece_area"] > 0]
    covered = pieces.groupby("cd_setor")["piece_area"].transform("sum")
    pieces["share"] = pieces["piece_area"] / covered
    pieces["population"] = pieces["population"] * pieces["share"]
    pieces["households"] = pieces["households"] * pieces["share"]
    per_cell = pieces.groupby("h3_id")[["population", "households"]].sum()
    result = pd.DataFrame({"h3_id": cells["h3_id"].values}).merge(per_cell, on="h3_id", how="left").fillna(0.0)

    placed = set(pieces["cd_setor"])
    orphan = sectors[~sectors["cd_setor"].isin(placed)]
    area = sectors.geometry.area
    covered_area = pieces.groupby("cd_setor")["piece_area"].sum().reindex(sectors["cd_setor"]).fillna(0.0).values
    summary = {
        "sectors": int(len(sectors)),
        "population_sectors": float(sectors["population"].sum()),
        "population_allocated": float(result["population"].sum()),
        "households_sectors": float(sectors["households"].sum()),
        "households_allocated": float(result["households"].sum()),
        "sectors_outside_grid": int(len(orphan)),
        "population_outside_grid": float(orphan["population"].sum()),
        "sectors_partly_outside_grid": int(((covered_area / area.values) < 0.95).sum() - len(orphan)),
    }
    return result, summary


def round_preserving_total(values: np.ndarray) -> np.ndarray:
    """Arredonda para inteiros mantendo a soma (maiores restos)."""
    values = np.asarray(values, dtype=float)
    floors = np.floor(values).astype(int)
    missing = int(round(values.sum())) - int(floors.sum())
    if missing > 0:
        order = np.argsort(-(values - floors), kind="stable")
        floors[order[:missing]] += 1
    return floors


# ---------------------------------------------------------------------------
# Persistencia
# ---------------------------------------------------------------------------

def _load_cells(settings):
    import geopandas as gpd
    from shapely import wkt

    from .db import db_engine

    with db_engine(settings) as engine:
        grid = pd.read_sql("SELECT h3_id, ST_AsText(geom) AS wkt FROM geo.grid_h3", engine)
    if grid.empty:
        raise RuntimeError("Grade H3 vazia. Rode fetch-boundary e build-grid antes.")
    return gpd.GeoDataFrame({"h3_id": grid["h3_id"]}, geometry=[wkt.loads(item) for item in grid["wkt"]], crs=4326)


def collect_census_population(ibge_code: str | None = None, *, settings=None, cache_dir: Path | str | None = None,
                              refresh: bool = False, tolerance_pct: float = 0.5, progress=print) -> dict[str, object]:
    """Baixa o Censo 2022 por setor, distribui nas celulas H3 e grava em geo.census_h3 e geo.features."""
    from sqlalchemy import text

    from .config import load_settings
    from .data_registry import ensure_data_schema, record_data_source
    from .db import db_engine

    settings = settings or load_settings()
    code = check_ibge_code(ibge_code or settings.city_ibge_code)
    cache = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
    uf = uf_of(code)

    aggregates_url = resolve_aggregates_url(progress)
    gpkg = download(GEO_URL.format(uf=uf), cache / f"{uf}_setores_CD2022.gpkg", kind="gpkg", refresh=refresh, progress=progress)
    zipped = download(aggregates_url, cache / Path(aggregates_url).name, kind="zip", refresh=refresh, progress=progress)

    progress("  lendo setores...")
    population = read_sector_population(zipped, code)
    geometry = read_sector_geometry(gpkg, code)
    sectors = geometry.merge(population, on="cd_setor", how="left")
    without_data = int(sectors["population"].isna().sum())
    without_polygon = int((~population["cd_setor"].isin(geometry["cd_setor"])).sum())
    official = official_population(code)
    sector_total = float(population["population"].sum())
    if official is not None and abs(sector_total - official) > official * tolerance_pct / 100:
        raise RuntimeError(f"Soma dos setores ({sector_total:.0f}) difere do total oficial do municipio ({official}).")

    cells = _load_cells(settings)
    crs = metric_crs(cells)
    allocated, summary = allocate_to_cells(sectors.to_crs(crs), cells.to_crs(crs))
    lost = summary["population_sectors"] - summary["population_allocated"]
    if abs(lost) > max(1.0, summary["population_sectors"] * tolerance_pct / 100):
        raise RuntimeError(
            f"{lost:.0f} habitantes ficaram fora da grade H3 ({summary['sectors_outside_grid']} setores sem celula). "
            "Confira o limite municipal e a grade."
        )

    allocated["pop_int"] = round_preserving_total(allocated["population"].values)
    ensure_data_schema(settings)
    with db_engine(settings) as engine, engine.begin() as conn:
        for row in allocated.itertuples():
            conn.execute(text("""
                INSERT INTO geo.census_h3 (h3_id, population_2022, occupied_households_2022, source_name, updated_at)
                VALUES (:h3, :pop, :hh, :source, now())
                ON CONFLICT (h3_id) DO UPDATE SET population_2022 = EXCLUDED.population_2022,
                    occupied_households_2022 = EXCLUDED.occupied_households_2022,
                    source_name = EXCLUDED.source_name, updated_at = now()
            """), {"h3": row.h3_id, "pop": float(row.population), "hh": float(row.households), "source": SOURCE_NAME})
        conn.execute(text("ALTER TABLE geo.features ADD COLUMN IF NOT EXISTS pop_estimated INT"))
        for row in allocated.itertuples():
            conn.execute(text("""
                INSERT INTO geo.features (h3_id, pop_estimated) VALUES (:h3, :pop)
                ON CONFLICT (h3_id) DO UPDATE SET pop_estimated = EXCLUDED.pop_estimated
            """), {"h3": row.h3_id, "pop": int(row.pop_int)})

    report = {
        "ibge_code": code,
        "uf": uf,
        "cells": int(len(allocated)),
        "cells_with_population": int((allocated["population"] > 0).sum()),
        "official_population_2022": official,
        "sectors_without_data": without_data,
        "sectors_without_polygon": without_polygon,
        **{key: (round(value, 1) if isinstance(value, float) else value) for key, value in summary.items()},
        "max_cell_population": round(float(allocated["population"].max()), 1),
        "sources": {"geometry": GEO_URL.format(uf=uf), "aggregates": aggregates_url},
    }
    record_data_source(
        "census_h3", SOURCE_NAME, source_uri=aggregates_url, reference_date=CENSUS_REFERENCE_DATE,
        row_count=len(allocated), details={**report, "geometry_sha256": sha256_of(gpkg)},
        checksum_sha256=sha256_of(zipped), license_name="IBGE - dados abertos (citar a fonte)",
        schema_version="census-sectors-v1", settings=settings,
    )
    return report
