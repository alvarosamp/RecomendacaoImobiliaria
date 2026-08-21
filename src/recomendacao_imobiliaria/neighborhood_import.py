"""Importação de polígonos de bairros, com prioridade para a fonte oficial."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from sqlalchemy import text

from .config import load_settings
from .data_registry import ensure_data_schema, record_data_source
from .db import make_engine


NAME_COLUMNS = ("nm_bairro", "bairro", "neighborhood", "nome", "name", "ds_bairro")
CITY_COLUMNS = ("nm_mun", "municipio", "cidade", "city", "nm_municip")
CODE_COLUMNS = ("cd_mun", "cod_mun", "municipality_code", "codigo_ibge")


@dataclasses.dataclass
class NeighborhoodImportResult:
    neighborhoods_imported: int
    cells_assigned: int
    source_file: str
    source_name: str


def default_neighborhood_file() -> Path:
    for path in (
        Path("data/official/bairros/bairros_oficiais.gpkg"),
        Path("data/official/bairros/bairros_oficiais.geojson"),
        Path("data/official/ibge/MG_bairros_CD2022.gpkg"),
    ):
        if path.exists():
            return path
    raise FileNotFoundError("Nenhum arquivo de bairros encontrado em data/official/bairros ou data/official/ibge.")


def import_neighborhoods(
    filepath: str | Path,
    *,
    municipality: str = "Pouso Alegre",
    municipality_code: str = "3152501",
    source_name: str = "oficial",
    settings=None,
) -> NeighborhoodImportResult:
    import geopandas as gpd

    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo de bairros não encontrado: {path}")
    gdf = gpd.read_file(path)
    if gdf.empty or gdf.crs is None:
        raise ValueError("A camada de bairros está vazia ou sem CRS.")
    columns = {str(column).lower(): str(column) for column in gdf.columns}
    name_column = next((columns[item] for item in NAME_COLUMNS if item in columns), None)
    if name_column is None:
        raise ValueError(f"Não encontrei nome do bairro. Colunas disponíveis: {', '.join(gdf.columns)}")
    city_column = next((columns[item] for item in CITY_COLUMNS if item in columns), None)
    code_column = next((columns[item] for item in CODE_COLUMNS if item in columns), None)
    if code_column:
        selected = gdf[gdf[code_column].astype(str).str.replace(".0", "", regex=False) == str(municipality_code)]
    elif city_column:
        selected = gdf[gdf[city_column].astype(str).str.casefold() == municipality.casefold()]
    else:
        selected = gdf
    selected = selected[selected.geometry.notna()].copy().to_crs(epsg=4326)
    selected = selected[selected.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].copy()
    if selected.empty:
        raise ValueError("Nenhum bairro encontrado para o município informado.")
    selected["name"] = selected[name_column].astype(str).str.strip()
    selected = selected[selected["name"] != ""].dissolve(by="name", as_index=False)

    active_settings = settings or load_settings()
    ensure_data_schema(active_settings)
    engine = make_engine(active_settings)
    try:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM geo.neighborhoods WHERE municipality_code = :code AND source_name = :source"), {"code": municipality_code, "source": source_name})
            for _, row in selected.iterrows():
                geom = row.geometry
                if geom.geom_type == "Polygon":
                    from shapely.geometry import MultiPolygon
                    geom = MultiPolygon([geom])
                conn.execute(text("""
                    INSERT INTO geo.neighborhoods
                    (name, municipality, municipality_code, source_name, source_file, geom)
                    VALUES (:name, :municipality, :code, :source, :file,
                            ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326))
                """), {"name": row["name"], "municipality": municipality, "code": municipality_code,
                       "source": source_name, "file": str(path), "geom": json.dumps(geom.__geo_interface__)})
            conn.execute(text("UPDATE geo.features SET neighborhood = NULL, neighborhood_source = NULL"))
            assigned = conn.execute(text("""
                UPDATE geo.features f
                SET neighborhood = n.name, neighborhood_source = n.source_name
                FROM geo.grid_h3 g
                JOIN geo.neighborhoods n ON ST_Covers(n.geom, ST_Centroid(g.geom))
                WHERE f.h3_id = g.h3_id
            """)).rowcount
    finally:
        engine.dispose()
    record_data_source("neighborhoods", source_name, source_uri=str(path), row_count=len(selected), details={"municipality": municipality, "municipality_code": municipality_code}, settings=active_settings)
    return NeighborhoodImportResult(len(selected), int(assigned or 0), str(path), source_name)
