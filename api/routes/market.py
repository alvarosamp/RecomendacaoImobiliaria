"""Comparação transparente de preço com anúncios locais disponíveis."""
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/market/compare")
def compare_market_price(
    neighborhood: str = Query(..., min_length=2),
    asking_price: float = Query(..., gt=0),
    area_m2: float = Query(..., gt=0),
):
    path = Path(__file__).resolve().parents[2] / "data" / "pouso_alegre_listings.csv"
    data = pd.read_csv(path, usecols=["price", "area_m2", "neighborhood"])
    data["price_m2"] = data.price / data.area_m2.replace(0, pd.NA)
    sample = data[data.neighborhood.str.casefold() == neighborhood.casefold()].dropna(subset=["price_m2"])
    if sample.empty:
        sample = data.dropna(subset=["price_m2"])
        scope = "municipio"
    else:
        scope = "bairro"
    reference = float(sample.price_m2.median())
    asking_m2 = asking_price / area_m2
    deviation = (asking_m2 / reference - 1) * 100
    status = "abaixo_do_mercado" if deviation <= -8 else "acima_do_mercado" if deviation >= 8 else "compativel"
    return {"scope": scope, "comparables": len(sample), "reference_price_m2": round(reference, 2), "asking_price_m2": round(asking_m2, 2), "deviation_pct": round(deviation, 1), "status": status,
            "recommendation": "Negociar antes de avancar." if status == "acima_do_mercado" else "Preco compativel com a amostra." if status == "compativel" else "Validar condicao e documentacao; preco abaixo da referencia."}
