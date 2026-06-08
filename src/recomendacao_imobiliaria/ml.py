from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


DEFAULT_TARGET = "price"
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
    "ndbi_mean_90",
    "dist_min_supermarket_m",
    "dist_min_pharmacy_m",
    "dist_min_school_m",
]
DEFAULT_CATEGORICAL_FEATURES = ["property_type", "neighborhood", "zona"]


@dataclass(frozen=True)
class TrainResult:
    model_path: str
    rows: int
    mae: float
    r2: float


def train_price_model(
    csv_path: str,
    model_path: str = "models/price_model.joblib",
    target: str = DEFAULT_TARGET,
) -> TrainResult:
    data = pd.read_csv(csv_path)
    missing = [column for column in [target] if column not in data.columns]
    if missing:
        raise ValueError(f"Colunas obrigatorias ausentes: {missing}")

    numeric_features = [column for column in DEFAULT_NUMERIC_FEATURES if column in data.columns]
    categorical_features = [column for column in DEFAULT_CATEGORICAL_FEATURES if column in data.columns]
    if not numeric_features and not categorical_features:
        raise ValueError("Nenhuma feature conhecida encontrada no CSV.")

    frame = data.dropna(subset=[target]).copy()
    x = frame[numeric_features + categorical_features]
    y = frame[target]

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.2,
        random_state=42,
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", SimpleImputer(strategy="median"), numeric_features),
            (
                "cat",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                categorical_features,
            ),
        ],
        remainder="drop",
    )

    model = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            (
                "regressor",
                RandomForestRegressor(
                    n_estimators=250,
                    random_state=42,
                    min_samples_leaf=2,
                    n_jobs=-1,
                ),
            ),
        ]
    )

    model.fit(x_train, y_train)
    predictions = model.predict(x_test)

    output = Path(model_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": model,
            "numeric_features": numeric_features,
            "categorical_features": categorical_features,
            "target": target,
        },
        output,
    )

    return TrainResult(
        model_path=str(output),
        rows=len(frame),
        mae=float(mean_absolute_error(y_test, predictions)),
        r2=float(r2_score(y_test, predictions)),
    )
