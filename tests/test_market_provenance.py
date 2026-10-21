import pandas as pd

from api.routes import market, predict
from recomendacao_imobiliaria.ml import _guess_data_kind


def test_compare_without_real_listings_has_no_reference(monkeypatch):
    monkeypatch.setattr(market, "_real_listings", lambda: pd.DataFrame(columns=["neighborhood", "price_per_m2"]))
    result = market.compare_market_price("Centro", 500_000, 100)
    assert result["status"] == "sem_dados"
    assert result["reference_price_m2"] is None


def test_compare_filters_and_requires_explicit_city_expansion(monkeypatch):
    rows = [("Centro", 6000.0)] * 5 + [("Jardim Yara", 3000.0)] * 2
    frame = pd.DataFrame(rows, columns=["neighborhood", "price_per_m2"])
    frame['city']='Pouso Alegre';frame['property_type']='casa';frame['transaction']='venda';frame['area_m2']=100
    frame['collected_at']=pd.Timestamp.now(tz='UTC')
    unrelated=frame.iloc[:1].copy();unrelated['property_type']='apartamento';unrelated['price_per_m2']=99999
    monkeypatch.setattr(market, "_real_listings", lambda: pd.concat([frame,unrelated],ignore_index=True))
    centro=market.compare_market_price("centro",600_000,100,property_type='casa')
    assert centro['scope']=='bairro' and centro['reference_price_m2']==6000
    assert market.compare_market_price("Jardim Yara",300_000,100,property_type='casa')['status']=='sem_dados'
    expanded=market.compare_market_price("Jardim Yara",300_000,100,property_type='casa',allow_city_expansion=True)
    assert expanded['scope']=='municipio' and expanded['comparables']==7 and expanded['expanded'] is True
    assert market.compare_market_price("centro",600_000,100,city='Outra',property_type='casa')['status']=='sem_dados'


def test_models_without_real_provenance_are_flagged():
    assert predict._training_warning({}) == predict.DEMO_MODEL_WARNING
    assert predict._training_warning({"training_source": {"kind": "demo"}}) == predict.DEMO_MODEL_WARNING
    assert predict._training_warning({"training_source": {"kind": "real"}}) is None


def test_synthetic_listings_csv_is_marked_demo():
    assert _guess_data_kind("data/pouso_alegre_listings.csv") == "demo"
    assert _guess_data_kind("data/processed/market_listings_train.csv") == "csv"
