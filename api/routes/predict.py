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


BASE_PRICE_M2 = {
    "apartamento": 5200,
    "casa": 4300,
    "comercial": 5600,
    "terreno": 1250,
}


def _fallback_price(req: PredictRequest) -> dict:
    base = BASE_PRICE_M2.get(req.property_type, 4300)
    area = max(req.area_m2, 1)
    rooms_factor = 1 + min(req.bedrooms, 5) * 0.035 + min(req.bathrooms, 5) * 0.028
    parking_factor = 1 + min(req.parking_spaces, 4) * 0.025
    location_factor = 1.0
    if -22.28 <= req.latitude <= -22.18 and -46.02 <= req.longitude <= -45.88:
        location_factor = 1.06
    if req.property_type == "terreno":
        rooms_factor = 1.0
        parking_factor = 1.0
    price = area * base * rooms_factor * parking_factor * location_factor
    return {
        "predicted_price": round(price, 2),
        "price_low": round(price * 0.82, 2),
        "price_high": round(price * 1.18, 2),
        "price_per_m2": round(price / area, 2),
        "model_status": "fallback_hedonic",
        "explain": [
            f"base regional estimada de R$ {base:,.0f}/m2".replace(",", "."),
            "ajuste por quartos, banheiros, vagas e localizacao",
            "treine o LightGBM para substituir esta estimativa por modelo supervisionado",
        ],
    }


@router.post("/predict")
def predict(req: PredictRequest):
    if not os.path.exists(MODEL_PATH):
        result = _fallback_price(req)
        result["warning"] = "Modelo LightGBM nao treinado. Usando estimativa hedônica de baixo custo."
        return result

    try:
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
        return {
            "predicted_price": round(price, 2),
            "price_low": round(price * 0.88, 2),
            "price_high": round(price * 1.12, 2),
            "price_per_m2": round(price / max(req.area_m2, 1), 2),
            "model_status": "lightgbm",
        }
    except Exception:
        # Modelo treinado presente no disco, mas dependencia (ex.: lightgbm) ou
        # arquivo indisponivel neste ambiente — degrada para a estimativa hedonica
        # em vez de derrubar a rota com 500.
        result = _fallback_price(req)
        result["warning"] = "Modelo LightGBM indisponivel neste ambiente. Usando estimativa hedônica de baixo custo."
        return result
