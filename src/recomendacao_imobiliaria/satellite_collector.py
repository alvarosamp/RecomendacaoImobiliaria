"""Collect real Sentinel-2 NDVI/NDBI for H3 cells via Microsoft Planetary Computer (free, no key)."""
from __future__ import annotations

import dataclasses
import datetime
import logging
import time
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


def _cells_bbox(h3_ids: list[str], buffer: float = 0.001) -> list[float]:
    import h3 as h3lib

    all_lons: list[float] = []
    all_lats: list[float] = []
    for h3_id in h3_ids:
        for lat, lon in h3lib.cell_to_boundary(h3_id):
            all_lats.append(lat)
            all_lons.append(lon)

    return [
        min(all_lons) - buffer,
        min(all_lats) - buffer,
        max(all_lons) + buffer,
        max(all_lats) + buffer,
    ]


def _h3_to_bbox(h3_id: str, buffer: float = 0.001) -> list[float]:
    return _cells_bbox([h3_id], buffer=buffer)


def _search_items_with_retry(
    catalog,
    label: str,
    bbox: list[float],
    start_date: str,
    end_date: str,
    max_cloud_pct: float,
    limit: int = 200,
    max_retries: int = 3,
):
    for attempt in range(1, max_retries + 1):
        try:
            search = catalog.search(
                collections=["sentinel-2-l2a"],
                bbox=bbox,
                datetime=f"{start_date}/{end_date}",
                query={"eo:cloud_cover": {"lt": max_cloud_pct}},
                limit=limit,
                max_items=limit,
            )
            return list(search.items())

        except Exception as exc:
            msg = str(exc).lower()
            if "maximum allowed time" in msg or "timed out" in msg or "timeout" in msg:
                log.warning("Timeout na busca STAC (%s). Tentativa %d/%d.", label, attempt, max_retries)
                if attempt < max_retries:
                    time.sleep(5 * attempt)
                    continue
                raise RuntimeError(
                    f"Timeout na busca STAC para {label} apos {max_retries} tentativas."
                ) from exc
            raise


def _best_scene_per_tile(items: list) -> dict[str, object]:
    """Return the lowest-cloud-cover scene for each MGRS tile."""
    best: dict[str, object] = {}
    for item in items:
        tile_id = item.properties.get("s2:mgrs_tile") or item.id[:6]
        cloud = item.properties.get("eo:cloud_cover", 100.0)
        current = best.get(tile_id)
        if current is None or cloud < current.properties.get("eo:cloud_cover", 100.0):
            best[tile_id] = item
    return best


def collect_sentinel2_indices(
    h3_ids: list[str],
    start_date: str,
    end_date: str,
    output_csv: str = "data/sentinel2_indices.csv",
    max_cloud_pct: float = 30.0,
    limit: int = 200,
) -> SatelliteCollectResult:
    """Fetch Sentinel-2 L2A NDVI/NDBI for a list of H3 cells.

    Uses Microsoft Planetary Computer STAC. Performs ONE search over the full
    bounding box, groups results by MGRS tile, then downloads each tile once and
    extracts all H3 cells from it in memory — instead of one request per cell.

    Bands: B04 Red, B08 NIR, B11 SWIR1.
    NDVI = (NIR - Red) / (NIR + Red)
    NDBI = (SWIR1 - NIR) / (SWIR1 + NIR)
    """
    _check_deps()

    import h3 as h3lib
    import planetary_computer
    import pystac_client
    import stackstac

    catalog = pystac_client.Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace,
    )

    best_rows: dict[str, dict] = {}  # h3_id -> best (lowest cloud_pct) row
    errors: list[str] = []
    scenes_processed = 0

    # --- Step 1: single search over the full bbox ---
    overall_bbox = _cells_bbox(h3_ids, buffer=0.01)
    print(
        f"Buscando cenas Sentinel-2 para {len(h3_ids)} celulas H3 "
        f"(bbox: {[round(x, 3) for x in overall_bbox]})..."
    )

    items = _search_items_with_retry(
        catalog=catalog,
        label="grid_completo",
        bbox=overall_bbox,
        start_date=start_date,
        end_date=end_date,
        max_cloud_pct=max_cloud_pct,
        limit=limit,
        max_retries=3,
    )

    if not items:
        print("Sem cenas Sentinel-2 no periodo com cobertura de nuvens aceitavel.")
        Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame().to_csv(output_csv, index=False)
        return SatelliteCollectResult(
            h3_cells=len(h3_ids),
            scenes_processed=0,
            rows_written=0,
            output_path=output_csv,
        )

    # --- Step 2: best scene per MGRS tile ---
    best_by_tile = _best_scene_per_tile(items)
    print(f"Encontradas {len(items)} cenas em {len(best_by_tile)} tiles MGRS. Processando...")

    # Precompute centroids for fast containment checks
    h3_centroids: dict[str, tuple[float, float]] = {}
    for h3_id in h3_ids:
        lat, lon = h3lib.cell_to_latlng(h3_id)
        h3_centroids[h3_id] = (lat, lon)

    covered_h3_ids: set[str] = set()

    # --- Step 3: one download per tile, extract all H3 cells in one pass ---
    for tile_idx, (tile_id, item) in enumerate(best_by_tile.items(), 1):
        item_bbox = item.bbox or _cells_bbox(
            [h3_id for h3_id in h3_ids], buffer=0.0
        )

        # H3 cells whose centroid falls within this tile
        tile_h3_ids = [
            h3_id
            for h3_id, (lat, lon) in h3_centroids.items()
            if item_bbox[0] <= lon <= item_bbox[2] and item_bbox[1] <= lat <= item_bbox[3]
        ]

        if not tile_h3_ids:
            continue

        cloud_pct = float(item.properties.get("eo:cloud_cover", 0.0))
        date_str = item.datetime.strftime("%Y-%m-%d") if item.datetime else None

        group_bbox = _cells_bbox(tile_h3_ids, buffer=0.002)

        print(
            f"[{tile_idx}/{len(best_by_tile)}] Tile {tile_id} "
            f"({date_str}, nuvem {cloud_pct:.0f}%): "
            f"{len(tile_h3_ids)} celulas H3..."
        )

        try:
            da = stackstac.stack(
                [item],
                assets=["B04", "B08", "B11"],
                bounds_latlon=group_bbox,
                epsg=4326,
                resolution=0.0002,  # ~22 m in degrees at 23°S
                dtype="float64",
                rescale=False,
            ).squeeze("time")

            b04 = da.sel(band="B04").values / 10000.0
            b08 = da.sel(band="B08").values / 10000.0
            b11 = da.sel(band="B11").values / 10000.0

            ndvi_raster = (b08 - b04) / (b08 + b04 + 1e-9)
            ndbi_raster = (b11 - b08) / (b11 + b08 + 1e-9)

            lons = da.coords["x"].values  # shape (nx,)
            lats = da.coords["y"].values  # shape (ny,), may be descending

            scenes_processed += 1

            for h3_id in tile_h3_ids:
                cell_bbox = _h3_to_bbox(h3_id, buffer=0.0)

                lat_idx = np.where((lats >= cell_bbox[1]) & (lats <= cell_bbox[3]))[0]
                lon_idx = np.where((lons >= cell_bbox[0]) & (lons <= cell_bbox[2]))[0]

                if lat_idx.size == 0 or lon_idx.size == 0:
                    errors.append(f"{h3_id}: sem pixels na celula rasterizada.")
                    continue

                ndvi_sub = ndvi_raster[np.ix_(lat_idx, lon_idx)]
                ndbi_sub = ndbi_raster[np.ix_(lat_idx, lon_idx)]

                ndvi_val = float(np.nanmedian(ndvi_sub))
                ndbi_val = float(np.nanmedian(ndbi_sub))

                if np.isnan(ndvi_val) or np.isnan(ndbi_val):
                    errors.append(f"{h3_id}: NDVI ou NDBI invalido.")
                    continue

                existing = best_rows.get(h3_id)
                if existing is None or cloud_pct < existing["cloud_pct"]:
                    best_rows[h3_id] = {
                        "h3_id": h3_id,
                        "date": date_str,
                        "ndvi": round(ndvi_val, 4),
                        "ndbi": round(ndbi_val, 4),
                        "bai": None,
                        "cloud_pct": round(cloud_pct, 1),
                    }
                    covered_h3_ids.add(h3_id)

            print(f"  -> {len(tile_h3_ids)} celulas extraidas.")

        except Exception as exc:
            msg = f"Tile {tile_id}: {exc}"
            errors.append(msg)
            log.warning("Erro ao processar tile %s: %s", tile_id, exc)

    uncovered = len(h3_ids) - len(covered_h3_ids)
    if uncovered:
        log.info("%d celulas H3 sem cobertura de tiles.", uncovered)

    df = pd.DataFrame(list(best_rows.values()))
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
    from sqlalchemy import text

    from .config import load_settings
    from .db import make_engine

    if settings is None:
        settings = load_settings()

    if end_date is None:
        end_date = datetime.date.today().isoformat()

    if start_date is None:
        start_date = (datetime.date.today() - datetime.timedelta(days=180)).isoformat()

    eng = make_engine(settings)

    try:
        with eng.connect() as conn:
            result = conn.execute(text("SELECT h3_id FROM geo.grid_h3"))
            h3_ids = [row[0] for row in result]
    finally:
        eng.dispose()

    log.info(
        "Coletando Sentinel-2 para %d celulas H3 (%s a %s).",
        len(h3_ids),
        start_date,
        end_date,
    )

    return collect_sentinel2_indices(
        h3_ids=h3_ids,
        start_date=start_date,
        end_date=end_date,
        output_csv=output_csv,
        max_cloud_pct=max_cloud_pct,
    )


def collect_time_series_for_grid(
    months: int = 12,
    output_csv: str = "data/sentinel2_indices.csv",
    max_cloud_pct: float = 30.0,
    settings=None,
) -> SatelliteCollectResult:
    """Mantém uma série mensal: uma melhor cena por mês e por célula H3.

    A coleta por janelas evita que a melhor cena mais recente apague a história
    necessária para calcular tendência de NDVI/NDBI.
    """
    if months < 1:
        raise ValueError("months deve ser maior que zero")
    today = datetime.date.today()
    frames: list[pd.DataFrame] = []
    errors: list[str] = []
    h3_cells = scenes = rows = 0
    for offset in range(months - 1, -1, -1):
        end = (pd.Timestamp(today).replace(day=1) - pd.DateOffset(months=offset - 1) - pd.Timedelta(days=1)).date()
        start = end.replace(day=1)
        temporary = Path(output_csv).with_name(f".{Path(output_csv).stem}-{start:%Y%m}.csv")
        result = collect_for_grid(start.isoformat(), end.isoformat(), str(temporary), max_cloud_pct, settings)
        h3_cells = max(h3_cells, result.h3_cells)
        scenes += result.scenes_processed
        rows += result.rows_written
        errors.extend(result.errors)
        if temporary.exists() and temporary.stat().st_size:
            frames.append(pd.read_csv(temporary))
        temporary.unlink(missing_ok=True)
    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if not combined.empty:
        combined = combined.drop_duplicates(subset=["h3_id", "date"], keep="last").sort_values(["h3_id", "date"])
    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(output_csv, index=False)
    return SatelliteCollectResult(h3_cells, scenes, len(combined), output_csv, errors[:20])
