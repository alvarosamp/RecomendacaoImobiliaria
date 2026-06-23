"""Import official zoning data from GeoJSON/Shapefile into PostGIS and assign zones to H3 cells."""
from __future__ import annotations

import dataclasses
from pathlib import Path


@dataclasses.dataclass
class ZoningImportResult:
    zones_imported: int
    cells_assigned: int
    unmatched_cells: int
    source_file: str


def import_zoning_file(filepath: str | Path, settings=None) -> ZoningImportResult:
    """Import a GeoJSON or Shapefile with zoning polygons into geo.zoning.

    The file must have a column named 'zona', 'zone', 'sigla', or 'codigo'
    containing the zone code (e.g. 'ZMC', 'ZEU', 'ZEIS').
    After import, each H3 cell in geo.grid_h3 is spatially assigned its zone.
    """
    import geopandas as gpd

    from sqlalchemy import text

    from .config import Settings
    from .db import make_engine

    if settings is None:
        settings = Settings()

    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(
            f"Arquivo de zoneamento nao encontrado: {path}. "
            "Coloque o arquivo oficial em data/official/ ou gere um exemplo com gen-sample-zoning."
        )
    if path.suffix.lower() not in {".geojson", ".json", ".shp", ".gpkg", ".kml"}:
        raise ValueError(
            "Formato nao suportado para zoneamento. Use GeoJSON, Shapefile, GeoPackage ou KML."
        )
    gdf = gpd.read_file(path)
    if gdf.empty:
        raise ValueError("Arquivo de zoneamento lido, mas sem geometrias.")
    if gdf.crs is None:
        raise ValueError(
            "Arquivo de zoneamento esta sem CRS/SRID. Defina o sistema de coordenadas no QGIS antes de importar."
        )

    col_map = {c.lower(): c for c in gdf.columns}
    zona_col = (
        col_map.get("zona")
        or col_map.get("zone")
        or col_map.get("sigla")
        or col_map.get("codigo")
        or col_map.get("cod_zona")
    )
    if zona_col is None:
        raise ValueError(
            f"Coluna de zona nao encontrada. Colunas disponiveis: {list(gdf.columns)}"
        )

    gdf = gdf.rename(columns={zona_col: "zona"})

    label_col = col_map.get("label") or col_map.get("descricao") or col_map.get("nome")
    keep_cols = ["zona", "geometry"]
    if label_col and label_col != "zona":
        gdf = gdf.rename(columns={label_col: "label"})
        keep_cols = ["zona", "label", "geometry"]

    gdf = gdf[keep_cols].copy()
    gdf = gdf.to_crs(epsg=4326)

    gdf = gdf.dissolve(by="zona", as_index=False)

    eng = make_engine(settings)

    with eng.begin() as conn:
        conn.execute(text("TRUNCATE geo.zoning"))

    import json

    with eng.begin() as conn:
        for _, row in gdf.iterrows():
            obs = row.get("label") if "label" in gdf.columns else None
            conn.execute(
                text(
                    "INSERT INTO geo.zoning (zona, observacoes, geom) "
                    "VALUES (:zona, :obs, ST_SetSRID(ST_GeomFromGeoJSON(:geom), 4326))"
                ),
                {
                    "zona": row["zona"],
                    "obs": obs,
                    "geom": json.dumps(row.geometry.__geo_interface__),
                },
            )

    with eng.begin() as conn:
        # Add zona column to geo.features if it doesn't exist yet
        conn.execute(text(
            "ALTER TABLE geo.features ADD COLUMN IF NOT EXISTS zona VARCHAR(32)"
        ))

        result = conn.execute(text(
            """
            UPDATE geo.features f
            SET zona = z.zona
            FROM geo.zoning z
            JOIN geo.grid_h3 g ON ST_Intersects(ST_Centroid(g.geom), z.geom)
            WHERE g.h3_id = f.h3_id
            """
        ))
        cells_assigned = result.rowcount

        unmatched = conn.execute(
            text("SELECT COUNT(*) FROM geo.features WHERE zona IS NULL")
        ).scalar()

    eng.dispose()

    return ZoningImportResult(
        zones_imported=len(gdf),
        cells_assigned=cells_assigned,
        unmatched_cells=int(unmatched or 0),
        source_file=str(path),
    )


def generate_sample_zoning_geojson(output_path: str = "data/sample_zoning.geojson") -> str:
    """Generate a sample zoning GeoJSON covering the Pouso Alegre region for testing."""
    import json

    from .config import Settings

    s = Settings()
    lat, lon = s.city_lat, s.city_lon

    # Approximate bounding boxes around city centre
    zones = [
        {
            "zona": "ZMC",
            "label": "Zona Mista Central",
            "coords": [
                [lon - 0.01, lat - 0.008],
                [lon + 0.01, lat - 0.008],
                [lon + 0.01, lat + 0.008],
                [lon - 0.01, lat + 0.008],
                [lon - 0.01, lat - 0.008],
            ],
        },
        {
            "zona": "ZM",
            "label": "Zona Mista",
            "coords": [
                [lon - 0.025, lat - 0.02],
                [lon - 0.01, lat - 0.02],
                [lon - 0.01, lat + 0.02],
                [lon - 0.025, lat + 0.02],
                [lon - 0.025, lat - 0.02],
            ],
        },
        {
            "zona": "ZM1",
            "label": "Zona Mista 1",
            "coords": [
                [lon + 0.01, lat - 0.02],
                [lon + 0.025, lat - 0.02],
                [lon + 0.025, lat + 0.02],
                [lon + 0.01, lat + 0.02],
                [lon + 0.01, lat - 0.02],
            ],
        },
        {
            "zona": "ZEU",
            "label": "Zona de Expansao Urbana",
            "coords": [
                [lon - 0.05, lat - 0.04],
                [lon + 0.05, lat - 0.04],
                [lon + 0.05, lat - 0.02],
                [lon - 0.05, lat - 0.02],
                [lon - 0.05, lat - 0.04],
            ],
        },
        {
            "zona": "ZEIS",
            "label": "Zona Especial de Interesse Social",
            "coords": [
                [lon - 0.05, lat + 0.02],
                [lon + 0.05, lat + 0.02],
                [lon + 0.05, lat + 0.04],
                [lon - 0.05, lat + 0.04],
                [lon - 0.05, lat + 0.02],
            ],
        },
        {
            "zona": "ZPA",
            "label": "Zona de Preservacao Ambiental",
            "coords": [
                [lon - 0.07, lat - 0.06],
                [lon + 0.07, lat - 0.06],
                [lon + 0.07, lat - 0.04],
                [lon - 0.07, lat - 0.04],
                [lon - 0.07, lat - 0.06],
            ],
        },
    ]

    features = [
        {
            "type": "Feature",
            "properties": {"zona": z["zona"], "label": z["label"]},
            "geometry": {"type": "Polygon", "coordinates": [z["coords"]]},
        }
        for z in zones
    ]

    geojson = {"type": "FeatureCollection", "features": features}

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(geojson, fh, ensure_ascii=False, indent=2)

    return output_path
