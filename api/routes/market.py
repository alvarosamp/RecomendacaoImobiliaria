"""Comparação transparente de preço com anúncios reais importados (market.listings)."""
import pandas as pd
from fastapi import APIRouter, Query
from sqlalchemy import text

router = APIRouter()

MIN_NEIGHBORHOOD_SAMPLE = 5


def _real_listings() -> pd.DataFrame:
    from recomendacao_imobiliaria.config import load_settings
    from recomendacao_imobiliaria.db import make_engine

    engine = make_engine(load_settings())
    try:
        return pd.read_sql(text("""
            SELECT neighborhood, price_per_m2
              FROM market.listings
             WHERE price_per_m2 > 0
        """), engine)
    finally:
        engine.dispose()


@router.get("/market/compare")
def compare_market_price(
    neighborhood: str = Query(..., min_length=2),
    asking_price: float = Query(..., gt=0),
    area_m2: float = Query(..., gt=0),
):
    asking_m2 = asking_price / area_m2
    try:
        data = _real_listings()
    except Exception:
        data = pd.DataFrame(columns=["neighborhood", "price_per_m2"])
    if data.empty:
        # Antes a referência vinha de um CSV sintético; sem anúncios reais não há referência.
        return {"scope": None, "comparables": 0, "reference_price_m2": None, "asking_price_m2": round(asking_m2, 2),
                "deviation_pct": None, "status": "sem_dados",
                "recommendation": "Nenhum anúncio real importado ainda. Rode sync-listings ou import-listings para ter referência de mercado."}
    sample = data[data.neighborhood.fillna("").str.casefold() == neighborhood.casefold()]
    scope = "bairro"
    if len(sample) < MIN_NEIGHBORHOOD_SAMPLE:
        sample, scope = data, "municipio"
    reference = float(sample.price_per_m2.median())
    deviation = (asking_m2 / reference - 1) * 100
    status = "abaixo_do_mercado" if deviation <= -8 else "acima_do_mercado" if deviation >= 8 else "compativel"
    return {"scope": scope, "comparables": len(sample), "reference_price_m2": round(reference, 2), "asking_price_m2": round(asking_m2, 2), "deviation_pct": round(deviation, 1), "status": status,
            "recommendation": "Negociar antes de avancar." if status == "acima_do_mercado" else "Preco compativel com a amostra." if status == "compativel" else "Validar condicao e documentacao; preco abaixo da referencia."}
