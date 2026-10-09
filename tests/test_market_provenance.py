import pandas as pd

from api.routes import market, predict
from recomendacao_imobiliaria.ml import _guess_data_kind


def test_compare_without_real_listings_has_no_reference(monkeypatch):
    monkeypatch.setattr(market, "_real_listings", lambda: pd.DataFrame(columns=["neighborhood", "price_per_m2"]))
    result = market.compare_market_price("Centro", 500_000, 100)
    assert result["status"] == "sem_dados"
    assert result["reference_price_m2"] is None


def test_compare_uses_neighborhood_only_with_enough_listings(monkeypatch):
    rows = [("Centro", 6000.0)] * 5 + [("Jardim Yara", 3000.0)] * 2
    monkeypatch.setattr(market, "_real_listings", lambda: pd.DataFrame(rows, columns=["neighborhood", "price_per_m2"]))
    centro = market.compare_market_price("centro", 600_000, 100)
    yara = market.compare_market_price("Jardim Yara", 300_000, 100)
    assert (centro["scope"], centro["reference_price_m2"], centro["status"]) == ("bairro", 6000.0, "compativel")
    assert yara["scope"] == "municipio" and yara["comparables"] == 7


def test_models_without_real_provenance_are_flagged():
    assert predict._training_warning({}) == predict.DEMO_MODEL_WARNING
    assert predict._training_warning({"training_source": {"kind": "demo"}}) == predict.DEMO_MODEL_WARNING
    assert predict._training_warning({"training_source": {"kind": "real"}}) is None


def test_synthetic_listings_csv_is_marked_demo():
    assert _guess_data_kind("data/pouso_alegre_listings.csv") == "demo"
    assert _guess_data_kind("data/processed/market_listings_train.csv") == "csv"
