"""Descriptive comparison with explicit scope; never broadens the sample silently."""
from typing import Literal
import pandas as pd
from fastapi import APIRouter, Query
from sqlalchemy import text

router=APIRouter()
MIN_NEIGHBORHOOD_SAMPLE=5

def _real_listings():
    from recomendacao_imobiliaria.config import load_settings
    from recomendacao_imobiliaria.db import make_engine
    engine=make_engine(load_settings())
    try:
        return pd.read_sql(text("""SELECT neighborhood, price_per_m2, area_m2, property_type, city, collected_at,
            COALESCE(raw->>'transaction',raw->>'transaction_type') AS transaction
            FROM market.listings WHERE price_per_m2>0"""),engine)
    finally:engine.dispose()

@router.get('/market/compare')
def compare_market_price(neighborhood:str=Query(...,min_length=2),asking_price:float=Query(...,ge=.01,le=1e12),area_m2:float=Query(...,ge=.01,le=1e8),
    city:str='Pouso Alegre',property_type:Literal['casa','apartamento','terreno','comercial']|None=None,
    transaction:Literal['venda','aluguel']='venda',allow_city_expansion:bool=False):
    asking_m2=asking_price/area_m2
    empty=dict(scope=None,comparables=0,reference_price_m2=None,asking_price_m2=round(asking_m2,2),deviation_pct=None,status='sem_dados',
        recommendation='Não há comparáveis adequados com município, tipo, finalidade, área e data identificados. Revise as referências ou registre uma pesquisa própria.',
        expanded=False,filters=dict(city=city,property_type=property_type,transaction=transaction,area_tolerance_pct=30,maximum_age_days=365))
    try:data=_real_listings()
    except Exception:return empty
    required={'city','property_type','transaction','area_m2','collected_at','price_per_m2','neighborhood'}
    if data.empty or not required.issubset(data.columns) or property_type is None:return empty
    area=pd.to_numeric(data.area_m2,errors='coerce');price=pd.to_numeric(data.price_per_m2,errors='coerce')
    collected=pd.to_datetime(data.collected_at,errors='coerce',utc=True)
    now=pd.Timestamp.now(tz='UTC')
    valid=data.city.fillna('').str.casefold().eq(city.casefold())&data.property_type.fillna('').str.casefold().eq(property_type)&data.transaction.fillna('').str.casefold().eq(transaction)
    valid&=area.between(area_m2*.7,area_m2*1.3)&price.gt(0)&price.lt(float('inf'))&collected.between(now-pd.Timedelta(days=365),now)
    eligible=data[valid].copy();eligible['price_per_m2']=price[valid]
    sample=eligible[eligible.neighborhood.fillna('').str.casefold()==neighborhood.casefold()];scope='bairro'
    if len(sample)<MIN_NEIGHBORHOOD_SAMPLE:
        if not allow_city_expansion:return empty
        sample,scope=eligible,'municipio'
    if sample.empty:return empty
    reference=float(sample.price_per_m2.median());deviation=(asking_m2/reference-1)*100
    return dict(scope=scope,comparables=len(sample),reference_price_m2=round(reference,2),asking_price_m2=round(asking_m2,2),
        deviation_pct=round(deviation,1),status='referencia_descritiva',expanded=scope=='municipio',filters=empty['filters'],
        recommendation='Comparação descritiva dos anúncios filtrados, sem comprovar preço de transação ou avaliação profissional.'+(' A amostra foi ampliada ao município com sua autorização.' if scope=='municipio' else ''))
