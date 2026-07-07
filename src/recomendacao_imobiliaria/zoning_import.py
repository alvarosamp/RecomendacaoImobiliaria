"""Import official zoning data into PostGIS and assign zones to H3 cells."""
from __future__ import annotations

import dataclasses
import json
import re
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET


@dataclasses.dataclass
class ZoningImportResult:
    zones_imported: int
    cells_assigned: int
    unmatched_cells: int
    source_file: str


@dataclasses.dataclass
class ZoningInspectionResult:
    source_file: str
    driver_hint: str
    feature_count: int
    zone_count: int
    zones: list[dict[str, object]]
    recommended_zone_column: str | None
    has_geometry: bool


ZONE_COLUMN_CANDIDATES = [
    "zona",
    "zone",
    "sigla",
    "codigo",
    "cod_zona",
    "layer",
    "name",
    "nome",
]


def default_zoning_file() -> Path:
    candidates = [
        Path("data/official/pdpa/zoneamento_pdpa.kml"),
        Path("data/official/pdpa/zoneamento_pdpa.kmz"),
        Path("data/official/zoneamento_oficial.kml"),
        Path("data/official/zoneamento_oficial.kmz"),
        Path("data/official/zoneamento_oficial.geojson"),
        Path("data/official/zoneamento_oficial.gpkg"),
        Path("data/sample_zoning.geojson"),
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError("Nenhum arquivo de zoneamento encontrado em data/official ou data/sample_zoning.geojson.")


def inspect_zoning_file(filepath: str | Path) -> ZoningInspectionResult:
    path = _prepare_zoning_path(Path(filepath))
    if path.suffix.lower() == ".kml":
        return _inspect_kml(path)
    return _inspect_vector_file(path)


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

    path = _prepare_zoning_path(Path(filepath))
    if not path.exists():
        raise FileNotFoundError(
            f"Arquivo de zoneamento nao encontrado: {path}. "
            "Coloque o arquivo oficial em data/official/ ou gere um exemplo com gen-sample-zoning."
        )
    if path.suffix.lower() not in {".geojson", ".json", ".shp", ".gpkg", ".kml"}:
        raise ValueError(
            "Formato nao suportado para zoneamento. Use GeoJSON, Shapefile, GeoPackage, KML ou KMZ."
        )
    _enable_kml_driver()
    gdf = gpd.read_file(path)
    if gdf.empty:
        raise ValueError("Arquivo de zoneamento lido, mas sem geometrias.")
    if gdf.crs is None:
        raise ValueError(
            "Arquivo de zoneamento esta sem CRS/SRID. Defina o sistema de coordenadas no QGIS antes de importar."
        )

    col_map = {c.lower(): c for c in gdf.columns}
    zona_col = _find_zone_column(col_map)
    if zona_col is None:
        gdf["zona"] = gdf.apply(_infer_zone_from_row, axis=1)
        zona_col = "zona"

    gdf = gdf.rename(columns={zona_col: "zona"})
    gdf["zona"] = gdf["zona"].apply(_clean_zone_code)
    gdf = gdf[gdf["zona"].notna() & (gdf["zona"] != "")].copy()
    if gdf.empty:
        raise ValueError("Nenhuma zona valida foi encontrada no arquivo.")

    label_col = col_map.get("label") or col_map.get("descricao") or col_map.get("desc") or col_map.get("nome")
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


def _prepare_zoning_path(path: Path) -> Path:
    if path.suffix.lower() != ".kmz":
        return path
    if not path.exists():
        return path

    out_dir = Path("data/processed/kmz_extract") / path.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path) as archive:
        kml_names = [name for name in archive.namelist() if name.lower().endswith(".kml")]
        if not kml_names:
            raise ValueError(f"KMZ sem arquivo KML interno: {path}")
        selected = kml_names[0]
        target = out_dir / Path(selected).name
        if not target.exists():
            target.write_bytes(archive.read(selected))
    return target


def _enable_kml_driver() -> None:
    try:
        import fiona

        fiona.drvsupport.supported_drivers["KML"] = "rw"
        fiona.drvsupport.supported_drivers["LIBKML"] = "rw"
    except Exception:
        return


def _find_zone_column(col_map: dict[str, str]) -> str | None:
    for candidate in ZONE_COLUMN_CANDIDATES:
        if candidate in col_map:
            return col_map[candidate]
    return None


def _clean_zone_code(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.lower().endswith(".kml"):
        text = text[:-4]
    match = re.search(r"\b(Z[A-Z]{1,5}\s*-?\s*\d*[A-Z]?)\b", text.upper())
    if match:
        text = match.group(1)
    text = re.sub(r"[^A-Z0-9]", "", text.upper())
    if text == "ZONA" or not text.startswith("Z"):
        return None
    return text or None


def _infer_zone_from_row(row) -> str | None:
    texts = []
    for column in ["Layer", "layer", "Name", "name", "nome", "Description", "description", "DESC", "desc"]:
        if column in row and row[column] is not None:
            texts.append(str(row[column]))
            zone = _clean_zone_code(row[column])
            if zone:
                return zone
    return _infer_zone_from_description(" ".join(texts))


def _infer_zone_from_description(text: str | None) -> str | None:
    if not text:
        return None
    value = text.upper()
    if "VERTICALIZA" in value:
        return "ZMV"
    if "ZONAS CENTRAIS" in value or "ZONA CENTRAL" in value:
        return "ZC"
    if "EXPANSAO URBANA" in value or "EXPANSÃO URBANA" in value:
        return "ZEU"
    if "EXCLUSIVAMENTE RESIDENCIA" in value:
        return "ZER"
    return None


def _inspect_kml(path: Path) -> ZoningInspectionResult:
    ns = {"kml": "http://www.opengis.net/kml/2.2"}
    tree = ET.parse(path)
    root = tree.getroot()
    placemarks = root.findall(".//kml:Placemark", ns)
    zones: Counter[str] = Counter()
    has_geometry = False
    desc_by_zone: dict[str, str] = {}

    for placemark in placemarks:
        if placemark.find(".//kml:Polygon", ns) is not None or placemark.find(".//kml:MultiGeometry", ns) is not None:
            has_geometry = True
        values: dict[str, str] = {}
        name = placemark.find("kml:name", ns)
        if name is not None and name.text:
            values["name"] = name.text
        for item in placemark.findall(".//kml:SimpleData", ns):
            key = item.attrib.get("name", "")
            if key and item.text:
                values[key] = item.text
        zone = _clean_zone_code(values.get("Layer") or values.get("name")) or _infer_zone_from_description(values.get("DESC"))
        if not zone:
            continue
        zones[zone] += 1
        if values.get("DESC") and zone not in desc_by_zone:
            desc_by_zone[zone] = values["DESC"]

    zone_rows = [
        {"zona": zone, "features": count, "descricao": desc_by_zone.get(zone, "")}
        for zone, count in sorted(zones.items())
    ]
    return ZoningInspectionResult(
        source_file=str(path),
        driver_hint="KML",
        feature_count=len(placemarks),
        zone_count=len(zone_rows),
        zones=zone_rows,
        recommended_zone_column="Layer",
        has_geometry=has_geometry,
    )


def _inspect_vector_file(path: Path) -> ZoningInspectionResult:
    import geopandas as gpd

    _enable_kml_driver()
    gdf = gpd.read_file(path)
    col_map = {c.lower(): c for c in gdf.columns}
    zone_col = _find_zone_column(col_map)
    if zone_col:
        series = gdf[zone_col].apply(_clean_zone_code)
    else:
        series = gdf.apply(_infer_zone_from_row, axis=1)
    counts = series.dropna().value_counts().sort_index()
    zones = [{"zona": zone, "features": int(count), "descricao": ""} for zone, count in counts.items()]
    return ZoningInspectionResult(
        source_file=str(path),
        driver_hint=path.suffix.lower().lstrip("."),
        feature_count=len(gdf),
        zone_count=len(zones),
        zones=zones,
        recommended_zone_column=zone_col,
        has_geometry=bool(gdf.geometry.notna().any()),
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
