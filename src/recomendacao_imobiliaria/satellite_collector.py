"""Collect real Sentinel-2 NDVI/NDBI for H3 cells via Microsoft Planetary Computer (free, no key)."""
from __future__ import annotations

import dataclasses
import datetime
import logging
from pathlib import Path

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

_REQUIRED_PACKAGES = ("pystac_client", "planetary_computer", "stackstac", "rioxarray")


@dataclasses.dataclass
class SatelliteCollectResult:
    h3_cells: int
    scenes_processed: int
    rows_written: int
    output_path: str
    errors: list[str] = dataclasses.field(default_factory=list)


def _check_deps() -> None:
    missing = []
    for pkg in _REQUIRED_PACKAGES:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg.replace("_", "-"))
    if missing:
        raise ImportError(
            "Instale as dependencias de sensoriamento remoto real:\n"
            f"  pip install {' '.join(missing)}"
        )


def collect_sentinel2_indices(
    h3_ids: list[str],
    start_date: str,
    end_date: str,
    output_csv: str = "data/sentinel2_indices.csv",
    max_cloud_pct: float = 30.0,
) -> SatelliteCollectResult:
    """Fetch Sentinel-2 L2A NDVI/NDBI for a list of H3 cells.

    Uses Microsoft Planetary Computer STAC (free, anonymous).
    Bands used:  B04 (Red), B08 (NIR), B11 (SWIR1).
    NDVI = (NIR - Red) / (NIR + Red)
    NDBI = (SWIR1 - NIR) / (SWIR1 + NIR)
    """
    _check_deps()

    import h3 as h3lib
    import planetary_computer
    import pystac_client
    import stackstac

    rows: list[dict] = []
    errors: list[str] = []
    scenes_processed = 0

    catalog = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace,
    )

    for h3_id in h3_ids:
        try:
            boundary = h3lib.cell_to_boundary(h3_id)
            lats = [p[0] for p in boundary]
            lons = [p[1] for p in boundary]
            bbox = [min(lons) - 0.001, min(lats) - 0.001, max(lons) + 0.001, max(lats) + 0.001]

            search = catalog.search(
                collections=["sentinel-2-l2a"],
                bbox=bbox,
                datetime=f"{start_date}/{end_date}",
                query={"eo:cloud_cover": {"lt": max_cloud_pct}},
                sortby="+datetime",
            )

            items = list(search.items())
            if not items:
                log.debug("Sem cenas para %s no periodo.", h3_id)
                continue

            for item in items:
                try:
                    da = stackstac.stack(
                        [item],
                        assets=["B04", "B08", "B11"],
                        bounds_latlon=bbox,
                        resolution=20,
                        dtype="float32",
                    ).squeeze("time")

                    b04 = da.sel(band="B04").values
                    b08 = da.sel(band="B08").values
                    b11 = da.sel(band="B11").values

                    # Scale factor for L2A (DN → reflectance)
                    b04 = b04 / 10000.0
                    b08 = b08 / 10000.0
                    b11 = b11 / 10000.0

                    ndvi = np.nanmedian((b08 - b04) / (b08 + b04 + 1e-9))
                    ndbi = np.nanmedian((b11 - b08) / (b11 + b08 + 1e-9))
                    cloud_pct = float(item.properties.get("eo:cloud_cover", 0.0))
                    date_str = (
                        item.datetime.strftime("%Y-%m-%d")
                        if item.datetime
                        else start_date
                    )

                    rows.append(
                        {
                            "h3_id": h3_id,
                            "date": date_str,
                            "ndvi": round(float(ndvi), 4),
                            "ndbi": round(float(ndbi), 4),
                            "bai": None,
                            "cloud_pct": round(cloud_pct, 1),
                        }
                    )
                    scenes_processed += 1

                except Exception as exc:
                    errors.append(f"{h3_id}/{item.id}: {exc}")
                    log.warning("Erro ao processar cena %s: %s", item.id, exc)

        except Exception as exc:
            errors.append(f"{h3_id}: {exc}")
            log.warning("Erro ao buscar cenas para %s: %s", h3_id, exc)

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(["h3_id", "date"])
    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False)

    return SatelliteCollectResult(
        h3_cells=len(h3_ids),
        scenes_processed=scenes_processed,
        rows_written=len(df),
        output_path=output_csv,
        errors=errors[:20],
    )


def collect_for_grid(
    start_date: str | None = None,
    end_date: str | None = None,
    output_csv: str = "data/sentinel2_indices.csv",
    max_cloud_pct: float = 30.0,
    settings=None,
) -> SatelliteCollectResult:
    """Fetch H3 IDs from PostGIS and collect Sentinel-2 indices for the full grid."""
    from .config import Settings
    from .db import engine

    if settings is None:
        settings = Settings()
    if end_date is None:
        end_date = datetime.date.today().isoformat()
    if start_date is None:
        start_date = (datetime.date.today() - datetime.timedelta(days=180)).isoformat()

    eng = engine(settings)
    with eng.connect() as conn:
        result = conn.execute("SELECT h3_id FROM geo.grid_h3")
        h3_ids = [row[0] for row in result]

    log.info("Coletando Sentinel-2 para %d celulas H3 (%s a %s).", len(h3_ids), start_date, end_date)
    return collect_sentinel2_indices(h3_ids, start_date, end_date, output_csv, max_cloud_pct)
