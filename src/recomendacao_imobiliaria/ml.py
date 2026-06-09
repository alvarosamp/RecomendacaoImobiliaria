from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import KFold, train_test_split
from sklearn.preprocessing import OrdinalEncoder

log = logging.getLogger(__name__)

try:
    import mlflow
    import mlflow.lightgbm as _mlflow_lgbm
    _MLFLOW = True
except ImportError:
    _MLFLOW = False

DEFAULT_TARGET = "price"

# lat/lon aceitos em qualquer variante de nome
_LAT_ALIASES = ["latitude", "lat"]
_LON_ALIASES = ["longitude", "lon"]

DEFAULT_NUMERIC_FEATURES = [
    "area_m2",
    "bedrooms",
    "bathrooms",
    "parking_spaces",
    "latitude",
    "longitude",
    "score_residencial",
    "score_comercial",
    "ndvi_mean_90",
    "ndvi_slope_180",
    "ndbi_mean_90",
    "ndbi_slope_180",
    "dist_min_supermarket_m",
    "dist_min_pharmacy_m",
    "dist_min_school_m",
    "poi_supermarket_cnt",
    "poi_pharmacy_cnt",
    "poi_school_cnt",
]
DEFAULT_CATEGORICAL_FEATURES = ["property_type", "neighborhood", "zona"]


@dataclass(frozen=True)
class TrainResult:
    model_path: str
    rows: int
    mae: float
    r2: float
    cv_mae_mean: float
    cv_mae_std: float


@dataclass(frozen=True)
class PredictionResult:
    output_path: str
    rows: int
    prediction_column: str


# ---------------------------------------------------------------------------
# PostGIS enrichment
# ---------------------------------------------------------------------------

def enrich_with_postgis(df: pd.DataFrame, settings=None) -> pd.DataFrame:
    """Join listing rows to geo.features + geo.scores via H3 cell.

    Requires a `h3_id` column, or falls back to geocoding lat/lon to H3.
    Columns already present in df are NOT overwritten.
    """
    try:
        import h3 as h3lib
        from sqlalchemy import text

        from .config import load_settings
        from .db import make_engine

        settings = settings or load_settings()
    except ImportError as exc:
        log.warning("Enriquecimento PostGIS ignorado: %s", exc)
        return df

    frame = df.copy()

    # Derive h3_id from lat/lon if not present
    if "h3_id" not in frame.columns:
        lat_col = next((c for c in _LAT_ALIASES if c in frame.columns), None)
        lon_col = next((c for c in _LON_ALIASES if c in frame.columns), None)
        if lat_col and lon_col:
            frame["h3_id"] = frame.apply(
                lambda r: h3lib.latlng_to_cell(r[lat_col], r[lon_col], 8)
                if pd.notna(r[lat_col]) and pd.notna(r[lon_col])
                else None,
                axis=1,
            )

    if "h3_id" not in frame.columns or frame["h3_id"].isna().all():
        log.warning("Sem h3_id para enriquecimento PostGIS.")
        return frame

    eng = make_engine(settings)
    try:
        geo = pd.read_sql(
            """
            SELECT
                f.h3_id,
                f.ndvi_mean_90, f.ndvi_slope_180,
                f.ndbi_mean_90, f.ndbi_slope_180,
                f.dist_min_supermarket_m, f.dist_min_pharmacy_m, f.dist_min_school_m,
                f.poi_supermarket_cnt, f.poi_pharmacy_cnt, f.poi_school_cnt,
                f.zona,
                s.score_residencial, s.score_comercial
            FROM geo.features f
            LEFT JOIN geo.scores s USING (h3_id)
            """,
            eng,
        )
    finally:
        eng.dispose()

    if geo.empty:
        return frame

    # Overwrite only columns that are null or missing in the original frame
    merged = frame.merge(geo, on="h3_id", how="left", suffixes=("", "_geo"))
    for col in geo.columns:
        if col == "h3_id":
            continue
        geo_col = f"{col}_geo"
        if geo_col in merged.columns:
            # Use PostGIS value where original is null
            if col in merged.columns:
                merged[col] = merged[col].where(merged[col].notna(), merged[geo_col])
            else:
                merged[col] = merged[geo_col]
            merged.drop(columns=[geo_col], inplace=True)

    return merged


# ---------------------------------------------------------------------------
# Feature preparation
# ---------------------------------------------------------------------------

def _normalise_latlon(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure latitude/longitude columns exist, accepting lat/lon aliases."""
    frame = df.copy()
    if "latitude" not in frame.columns:
        for alias in _LAT_ALIASES:
            if alias in frame.columns:
                frame["latitude"] = frame[alias]
                break
    if "longitude" not in frame.columns:
        for alias in _LON_ALIASES:
            if alias in frame.columns:
                frame["longitude"] = frame[alias]
                break
    return frame


def _build_features(
    df: pd.DataFrame,
    numeric_features: list[str],
    categorical_features: list[str],
) -> tuple[np.ndarray, list[str], OrdinalEncoder | None]:
    """Return (X_array, final_feature_names, fitted_encoder_or_None)."""
    import lightgbm as lgb  # noqa: F401 — just to ensure it's available

    frame = df[numeric_features + categorical_features].copy()

    # Encode categoricals with OrdinalEncoder (LightGBM handles -1 natively)
    encoder = None
    if categorical_features:
        encoder = OrdinalEncoder(
            handle_unknown="use_encoded_value",
            unknown_value=-1,
            encoded_missing_value=-1,
        )
        frame[categorical_features] = encoder.fit_transform(
            frame[categorical_features].astype(str)
        )

    return frame.values.astype(float), numeric_features + categorical_features, encoder


# ---------------------------------------------------------------------------
# Optuna tuning
# ---------------------------------------------------------------------------

def _kfold_mae(
    model,
    X: np.ndarray,
    y: np.ndarray,
    cat_idx: list[int],
    feature_names: list[str] | None = None,
    n_splits: int = 5,
) -> tuple[float, float]:
    import lightgbm as lgb

    kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)
    maes = []
    for train_idx, val_idx in kf.split(X):
        m = lgb.LGBMRegressor(**model.get_params())
        fit_kw = {"categorical_feature": cat_idx} if cat_idx else {}
        if feature_names:
            X_tr = pd.DataFrame(X[train_idx], columns=feature_names)
            X_val = pd.DataFrame(X[val_idx], columns=feature_names)
        else:
            X_tr, X_val = X[train_idx], X[val_idx]
        m.fit(X_tr, y[train_idx], **fit_kw)
        preds = m.predict(X_val)
        maes.append(mean_absolute_error(y[val_idx], preds))
    return float(np.mean(maes)), float(np.std(maes))


def _tune_lgbm(
    X: np.ndarray,
    y: np.ndarray,
    cat_idx: list[int],
    n_trials: int = 50,
) -> dict:
    import lightgbm as lgb
    import optuna

    optuna.logging.set_verbosity(optuna.logging.WARNING)

    def objective(trial):
        params = {
            "objective": "regression",
            "metric": "mae",
            "verbosity": -1,
            "n_estimators": trial.suggest_int("n_estimators", 200, 1000),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 31, 255),
            "min_child_samples": trial.suggest_int("min_child_samples", 5, 50),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
            "n_jobs": -1,
        }
        model = lgb.LGBMRegressor(**params)
        mae, _ = _kfold_mae(model, X, y, cat_idx)
        return mae

    study = optuna.create_study(direction="minimize")
    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)
    return study.best_params


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def train_price_model(
    csv_path: str,
    model_path: str = "models/price_model.joblib",
    target: str = DEFAULT_TARGET,
    enrich: bool = True,
    n_trials: int = 50,
) -> TrainResult:
    """Train a LightGBM price model with Optuna tuning and k-fold CV.

    If *enrich* is True and PostGIS is reachable, geospatial features
    (NDVI, distances, scores, zona) are joined from the database before training.
    """
    import lightgbm as lgb

    data = pd.read_csv(csv_path)
    data = _normalise_latlon(data)

    if enrich:
        print("Enriquecendo dados com features geoespaciais do PostGIS...")
        data = enrich_with_postgis(data)

    if target not in data.columns:
        raise ValueError(f"Coluna alvo '{target}' nao encontrada no CSV.")

    numeric_features = [c for c in DEFAULT_NUMERIC_FEATURES if c in data.columns]
    categorical_features = [c for c in DEFAULT_CATEGORICAL_FEATURES if c in data.columns]

    if not numeric_features and not categorical_features:
        raise ValueError("Nenhuma feature conhecida encontrada no CSV.")

    frame = data.dropna(subset=[target]).copy()
    print(f"Treinando com {len(frame)} linhas, {len(numeric_features)} features numericas, "
          f"{len(categorical_features)} categoricas.")

    X, feature_names, encoder = _build_features(frame, numeric_features, categorical_features)
    y = frame[target].values

    cat_idx = list(range(len(numeric_features), len(feature_names)))

    # Tune hyperparameters
    print(f"Tuning com Optuna ({n_trials} trials)...")
    best_params = _tune_lgbm(X, y, cat_idx, n_trials=n_trials)
    best_params.update({"objective": "regression", "metric": "mae", "verbosity": -1, "n_jobs": -1})
    print(f"Melhores parametros: {best_params}")

    # Final k-fold CV with best params
    final_model = lgb.LGBMRegressor(**best_params)
    cv_mae_mean, cv_mae_std = _kfold_mae(final_model, X, y, cat_idx, feature_names)
    print(f"CV MAE: R$ {cv_mae_mean:,.0f} ± R$ {cv_mae_std:,.0f}")

    # Train on full data for the saved model
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    fit_kwargs = {"categorical_feature": cat_idx} if cat_idx else {}
    final_model.fit(X_train, y_train, **fit_kwargs)
    preds = final_model.predict(X_test)

    mae_holdout = float(mean_absolute_error(y_test, preds))
    r2_holdout  = float(r2_score(y_test, preds))

    output = Path(model_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": final_model,
            "numeric_features": numeric_features,
            "categorical_features": categorical_features,
            "feature_names": feature_names,
            "encoder": encoder,
            "cat_idx": cat_idx,
            "target": target,
        },
        output,
    )

    # ── MLflow tracking (opcional) ──────────────────────────────────────────
    if _MLFLOW:
        try:
            mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))
            mlflow.set_experiment("preco-imovel")
            with mlflow.start_run(run_name="lgbm-optuna"):
                mlflow.log_params({**best_params, "n_rows": len(frame), "n_features": len(feature_names)})
                mlflow.log_metric("cv_mae_mean",  cv_mae_mean)
                mlflow.log_metric("cv_mae_std",   cv_mae_std)
                mlflow.log_metric("mae_holdout",  mae_holdout)
                mlflow.log_metric("r2_holdout",   r2_holdout)
                _mlflow_lgbm.log_model(
                    final_model, "model",
                    registered_model_name="preco-imovel",
                )
        except Exception as mlf_err:
            log.warning("MLflow tracking falhou (nao bloqueante): %s", mlf_err)

    return TrainResult(
        model_path=str(output),
        rows=len(frame),
        mae=mae_holdout,
        r2=r2_holdout,
        cv_mae_mean=cv_mae_mean,
        cv_mae_std=cv_mae_std,
    )


def predict_prices(
    csv_path: str,
    model_path: str = "models/price_model.joblib",
    output_path: str = "data/processed/predicted_prices.csv",
    enrich: bool = True,
) -> PredictionResult:
    bundle = joblib.load(model_path)
    model = bundle["model"]
    numeric_features = bundle["numeric_features"]
    categorical_features = bundle["categorical_features"]
    encoder: OrdinalEncoder | None = bundle.get("encoder")
    cat_idx: list[int] = bundle.get("cat_idx", [])

    data = pd.read_csv(csv_path)
    data = _normalise_latlon(data)

    if enrich:
        data = enrich_with_postgis(data)

    for col in numeric_features + categorical_features:
        if col not in data.columns:
            data[col] = pd.NA

    frame = data[numeric_features + categorical_features].copy()
    if encoder is not None and categorical_features:
        frame[categorical_features] = encoder.transform(
            frame[categorical_features].astype(str)
        )

    X = frame.values.astype(float)
    predict_kwargs = {"categorical_feature": cat_idx} if cat_idx else {}
    # LightGBM predict does not accept fit kwargs — use raw predict
    preds = model.predict(X)

    output = data.copy()
    output["predicted_price"] = preds.round(2)
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(out_file, index=False)

    return PredictionResult(
        output_path=str(out_file),
        rows=len(output),
        prediction_column="predicted_price",
    )
