from __future__ import annotations

import os

import numpy as np
import pandas as pd
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

MODEL_PATH = os.getenv("MODEL_PATH", "models/price_model.joblib")


class PredictRequest(BaseModel):
    area_m2: float
    bedrooms: int = 0
    bathrooms: int = 0
    parking_spaces: int = 0
    property_type: str = "apartamento"
    latitude: float = 0.0
    longitude: float = 0.0


@router.post("/predict")
def predict(req: PredictRequest):
    if not os.path.exists(MODEL_PATH):
        return {"predicted_price": None, "error": "Modelo nao treinado ainda. Rode train-price primeiro."}

    import joblib

    bundle = joblib.load(MODEL_PATH)
    model = bundle["model"]
    numeric_features: list[str] = bundle["numeric_features"]
    categorical_features: list[str] = bundle["categorical_features"]
    encoder = bundle.get("encoder")

    row = {
        "area_m2": req.area_m2,
        "bedrooms": req.bedrooms,
        "bathrooms": req.bathrooms,
        "parking_spaces": req.parking_spaces,
        "property_type": req.property_type,
        "latitude": req.latitude,
        "longitude": req.longitude,
    }

    df = pd.DataFrame([row])

    try:
        from recomendacao_imobiliaria.ml import enrich_with_postgis
        df = enrich_with_postgis(df)
    except Exception:
        pass

    for col in numeric_features + categorical_features:
        if col not in df.columns:
            df[col] = np.nan

    if encoder is not None and categorical_features:
        df[categorical_features] = encoder.transform(df[categorical_features].astype(str))

    X = df[numeric_features + categorical_features].values.astype(float)
    price = float(model.predict(X)[0])
    return {"predicted_price": round(price, 2)}
