"""Coleta automatica de declividade por H3 usando Copernicus DEM GLO-30."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def slope_pct_from_elevation_range(elevation_range_m: float, cell_width_m: float) -> float:
    """Aproximacao conservadora da declividade por celula, em porcentagem."""
    if cell_width_m <= 0:
        return 0.0
    return round(max(0.0, elevation_range_m) / cell_width_m * 100, 3)


def collect_dem_slope_for_grid(output_csv: str = "data/risk_dem_inputs.csv", settings=None) -> str:
    """Extrai amplitude altimetrica do DEM e produz ``slope_pct`` por H3.

    A estimativa e apropriada para triagem territorial; projeto executivo deve
    usar levantamento topografico.
    """
    import h3
    import planetary_computer
    import pystac_client
    import stackstac
    from sqlalchemy import text

    from .config import load_settings
    from .db import db_engine

    settings = settings or load_settings()
    with db_engine(settings) as engine:
        h3_ids = [row[0] for row in engine.connect().execute(text("SELECT h3_id FROM geo.grid_h3"))]
    bounds = [coord for h3_id in h3_ids for point in h3.cell_to_boundary(h3_id) for coord in (point[1], point[0])]
    lons, lats = bounds[::2], bounds[1::2]
    bbox = [min(lons), min(lats), max(lons), max(lats)]
    catalog = pystac_client.Client.open("https://planetarycomputer.microsoft.com/api/stac/v1", modifier=planetary_computer.sign_inplace)
    items = list(catalog.search(collections=["cop-dem-glo-30"], bbox=bbox).items())
    if not items:
        raise RuntimeError("Copernicus DEM nao retornou tiles para o limite municipal.")
    data = stackstac.stack(items, assets=["data"], bounds_latlon=bbox, epsg=4326, resolution=0.0003).squeeze()
    raster = data.values
    # Tiles do DEM podem formar uma pilha (tempo/tile, y, x); consolida sobre
    # a primeira dimensao preservando o mosaico espacial.
    if raster.ndim == 3:
        raster = np.nanmedian(raster, axis=0)
    lons_raster, lats_raster = data.coords["x"].values, data.coords["y"].values
    rows = []
    for h3_id in h3_ids:
        cell = h3.cell_to_boundary(h3_id)
        cell_lats, cell_lons = zip(*cell)
        lat_idx = np.where((lats_raster >= min(cell_lats)) & (lats_raster <= max(cell_lats)))[0]
        lon_idx = np.where((lons_raster >= min(cell_lons)) & (lons_raster <= max(cell_lons)))[0]
        if not len(lat_idx) or not len(lon_idx):
            continue
        local = raster[np.ix_(lat_idx, lon_idx)]
        # Cada H3 de resolucao 8 mede aproximadamente 700 m; mantemos a estimativa explicita.
        rows.append({"h3_id": h3_id, "slope_pct": slope_pct_from_elevation_range(float(np.nanmax(local) - np.nanmin(local)), 700)})
    output = Path(output_csv)
    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output, index=False)
    return str(output)
