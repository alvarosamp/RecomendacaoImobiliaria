from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import text

from .config import Settings, load_settings
from .db import db_engine


REQUIRED_INDEX_COLUMNS = {"h3_id", "date"}
INDEX_VALUE_COLUMNS = ["ndvi", "ndbi", "bai", "cloud_pct"]


@dataclass(frozen=True)
class IndexImportResult:
    rows_read: int
    rows_written: int
    h3_cells: int
    min_date: str | None
    max_date: str | None


@dataclass(frozen=True)
class FeatureUpdateResult:
    h3_cells: int
    reference_date: str | None


def import_indices_csv(csv_path: str, settings: Settings | None = None) -> IndexImportResult:
    settings = settings or load_settings()
    frame = _read_indices_csv(csv_path)

    rows_written = 0
    with db_engine(settings) as engine:
        with engine.begin() as conn:
            for row in frame.to_dict(orient="records"):
                conn.execute(
                    text(
                        """
                        INSERT INTO geo.indices (
                            h3_id,
                            date,
                            ndvi,
                            ndbi,
                            bai,
                            cloud_pct
                        )
                        VALUES (
                            :h3_id,
                            :date,
                            :ndvi,
                            :ndbi,
                            :bai,
                            :cloud_pct
                        )
                        ON CONFLICT (h3_id, date) DO UPDATE SET
                            ndvi = EXCLUDED.ndvi,
                            ndbi = EXCLUDED.ndbi,
                            bai = EXCLUDED.bai,
                            cloud_pct = EXCLUDED.cloud_pct
                        """
                    ),
                    _row_to_params(row),
                )
                rows_written += 1

    return IndexImportResult(
        rows_read=len(frame),
        rows_written=rows_written,
        h3_cells=int(frame["h3_id"].nunique()),
        min_date=_date_to_text(frame["date"].min()),
        max_date=_date_to_text(frame["date"].max()),
    )


def update_remote_sensing_features(
    settings: Settings | None = None,
    reference_date: str | None = None,
) -> FeatureUpdateResult:
    settings = settings or load_settings()
    with db_engine(settings) as engine:
        indices = pd.read_sql(
            "SELECT h3_id, date, ndvi, ndbi, bai, cloud_pct FROM geo.indices",
            engine,
            parse_dates=["date"],
        )
        if indices.empty:
            return FeatureUpdateResult(h3_cells=0, reference_date=None)

        features = compute_index_features(indices, reference_date=reference_date)
        with engine.begin() as conn:
            for row in features.to_dict(orient="records"):
                conn.execute(
                    text(
                        """
                        INSERT INTO geo.features (
                            h3_id,
                            ndvi_mean_90,
                            ndvi_slope_180,
                            ndbi_mean_90,
                            ndbi_slope_180,
                            updated_at
                        )
                        VALUES (
                            :h3_id,
                            :ndvi_mean_90,
                            :ndvi_slope_180,
                            :ndbi_mean_90,
                            :ndbi_slope_180,
                            now()
                        )
                        ON CONFLICT (h3_id) DO UPDATE SET
                            ndvi_mean_90 = EXCLUDED.ndvi_mean_90,
                            ndvi_slope_180 = EXCLUDED.ndvi_slope_180,
                            ndbi_mean_90 = EXCLUDED.ndbi_mean_90,
                            ndbi_slope_180 = EXCLUDED.ndbi_slope_180,
                            updated_at = now()
                        """
                    ),
                    _row_to_params(row),
                )

    ref = features.attrs.get("reference_date")
    return FeatureUpdateResult(
        h3_cells=len(features),
        reference_date=_date_to_text(ref) if ref is not None else None,
    )


def compute_index_features(
    indices: pd.DataFrame,
    reference_date: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    frame = indices.copy()
    missing = REQUIRED_INDEX_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"Colunas obrigatorias ausentes: {sorted(missing)}")

    frame["date"] = pd.to_datetime(frame["date"])
    for column in INDEX_VALUE_COLUMNS:
        if column not in frame.columns:
            frame[column] = np.nan
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    ref = pd.to_datetime(reference_date) if reference_date else frame["date"].max()
    window_90 = frame[frame["date"] >= ref - pd.Timedelta(days=90)]
    window_180 = frame[frame["date"] >= ref - pd.Timedelta(days=180)]

    rows = []
    for h3_id, group_180 in window_180.groupby("h3_id"):
        group_90 = window_90[window_90["h3_id"] == h3_id]
        rows.append(
            {
                "h3_id": h3_id,
                "ndvi_mean_90": _mean_or_none(group_90["ndvi"]),
                "ndvi_slope_180": _daily_slope(group_180, "ndvi"),
                "ndbi_mean_90": _mean_or_none(group_90["ndbi"]),
                "ndbi_slope_180": _daily_slope(group_180, "ndbi"),
            }
        )

    result = pd.DataFrame(rows)
    result.attrs["reference_date"] = ref
    return result


def write_sample_indices_csv(path: str = "data/sample_indices.csv") -> str:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    base_dates = pd.date_range("2025-01-01", periods=8, freq="30D")
    profiles = {
        "demo-norte-01": {"ndvi": 0.54, "ndvi_step": -0.018, "ndbi": 0.12, "ndbi_step": 0.021},
        "demo-centro-01": {"ndvi": 0.22, "ndvi_step": -0.002, "ndbi": 0.48, "ndbi_step": 0.004},
        "demo-sul-01": {"ndvi": 0.68, "ndvi_step": 0.004, "ndbi": 0.08, "ndbi_step": 0.001},
    }
    for h3_id, profile in profiles.items():
        for i, date in enumerate(base_dates):
            rows.append(
                {
                    "h3_id": h3_id,
                    "date": date.date().isoformat(),
                    "ndvi": round(profile["ndvi"] + (profile["ndvi_step"] * i), 4),
                    "ndbi": round(profile["ndbi"] + (profile["ndbi_step"] * i), 4),
                    "bai": None,
                    "cloud_pct": 8 + i,
                }
            )
    pd.DataFrame(rows).to_csv(output, index=False)
    return str(output)


def _read_indices_csv(csv_path: str) -> pd.DataFrame:
    frame = pd.read_csv(csv_path)
    missing = REQUIRED_INDEX_COLUMNS - set(frame.columns)
    if missing:
        raise ValueError(f"Colunas obrigatorias ausentes: {sorted(missing)}")

    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    for column in INDEX_VALUE_COLUMNS:
        if column not in frame.columns:
            frame[column] = np.nan
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    return frame[["h3_id", "date", *INDEX_VALUE_COLUMNS]]


def _daily_slope(frame: pd.DataFrame, column: str) -> float | None:
    valid = frame[["date", column]].dropna()
    if len(valid) < 2:
        return None

    x = (valid["date"] - valid["date"].min()).dt.days.to_numpy(dtype=float)
    y = valid[column].to_numpy(dtype=float)
    if np.all(x == x[0]):
        return None
    slope = np.polyfit(x, y, 1)[0]
    return float(slope)


def _mean_or_none(series: pd.Series) -> float | None:
    value = series.dropna().mean()
    if pd.isna(value):
        return None
    return float(value)


def _row_to_params(row: dict[str, object]) -> dict[str, object]:
    params = {}
    for key, value in row.items():
        if pd.isna(value):
            params[key] = None
        elif isinstance(value, pd.Timestamp):
            params[key] = value.date()
        else:
            params[key] = value
    return params


def _date_to_text(value) -> str | None:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    return str(value)
