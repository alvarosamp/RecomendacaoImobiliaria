"""Fetch real property listings from public Brazilian APIs (Mercado Livre Imoveis + IBGE)."""
from __future__ import annotations

import dataclasses
import logging
import time
from pathlib import Path

import pandas as pd
import requests

log = logging.getLogger(__name__)

# Mercado Livre public API — no key required
_ML_BASE = "https://api.mercadolibre.com"
_ML_SITE = "MLB"
# MLB1459 = Imoveis (requer OAuth para acesso direto)
# Busca aberta por texto funciona sem autenticacao
_ML_REAL_ESTATE_CATEGORY = None

# IBGE Agregados API — no key required
_IBGE_BASE = "https://servicodados.ibge.gov.br/api/v1"

# Pouso Alegre IBGE code
_PA_IBGE_CODE = "3152501"


@dataclasses.dataclass
class ApiCollectResult:
    source: str
    rows_fetched: int
    output_path: str
    errors: list[str] = dataclasses.field(default_factory=list)


# ---------------------------------------------------------------------------
# Mercado Livre Imoveis
# ---------------------------------------------------------------------------

def _ml_search(query: str, offset: int = 0, limit: int = 50, access_token: str | None = None) -> dict:
    """Search Mercado Livre listings.

    The search endpoint requires an OAuth access_token.
    Register a free app at https://developers.mercadolibre.com.br to get one.
    Pass the token via the --token argument or the ML_ACCESS_TOKEN env var.
    """
    url = f"{_ML_BASE}/sites/{_ML_SITE}/search"
    params: dict = {"q": query, "offset": offset, "limit": limit, "category": "MLB1459"}
    headers = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    resp = requests.get(url, params=params, headers=headers, timeout=20)
    if resp.status_code == 403:
        raise PermissionError(
            "Mercado Livre retornou 403. A API de busca requer autenticacao OAuth.\n"
            "1. Cadastre um app gratuito em https://developers.mercadolibre.com.br\n"
            "2. Obtenha um access_token\n"
            "3. Passe com --token SEU_TOKEN ou defina a variavel ML_ACCESS_TOKEN"
        )
    resp.raise_for_status()
    return resp.json()


def _ml_item_detail(item_id: str) -> dict:
    url = f"{_ML_BASE}/items/{item_id}"
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return resp.json()


def _ml_extract_row(item: dict) -> dict | None:
    """Extract standardized fields from a Mercado Livre listing."""
    attrs = {a["id"]: a.get("value_name") or a.get("values", [{}])[0].get("name") for a in item.get("attributes", [])}

    price = item.get("price")
    if not price:
        return None

    title = item.get("title", "")
    location = item.get("location", {})
    address = location.get("address_line", "")
    neighborhood = location.get("neighborhood", {}).get("name", "")
    city = location.get("city", {}).get("name", "")
    state = location.get("state", {}).get("name", "")
    lat = location.get("latitude")
    lon = location.get("longitude")

    # Attribute keys used by ML Real Estate
    area_str = attrs.get("TOTAL_AREA") or attrs.get("COVERED_AREA") or attrs.get("LOT_SIZE")
    try:
        area = float(str(area_str).replace(",", ".")) if area_str else None
    except ValueError:
        area = None

    bedrooms_str = attrs.get("BEDROOMS")
    try:
        bedrooms = int(bedrooms_str) if bedrooms_str else None
    except ValueError:
        bedrooms = None

    bathrooms_str = attrs.get("FULL_BATHROOMS") or attrs.get("BATHROOMS")
    try:
        bathrooms = int(bathrooms_str) if bathrooms_str else None
    except ValueError:
        bathrooms = None

    parking_str = attrs.get("PARKING_LOTS")
    try:
        parking = int(parking_str) if parking_str else None
    except ValueError:
        parking = None

    prop_type_raw = attrs.get("PROPERTY_TYPE", "")
    prop_type_map = {
        "Apartamento": "apartamento",
        "Casa": "casa",
        "Casa em Condomínio": "casa_condominio",
        "Terreno": "terreno",
        "Comercial": "comercial",
        "Galpão": "galpao",
    }
    prop_type = prop_type_map.get(str(prop_type_raw), str(prop_type_raw).lower())

    return {
        "ml_id": item.get("id"),
        "title": title,
        "price": price,
        "area_m2": area,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "parking_spaces": parking,
        "property_type": prop_type,
        "neighborhood": neighborhood,
        "city": city,
        "state": state,
        "address": address,
        "lat": lat,
        "lon": lon,
        "url": item.get("permalink"),
    }


def fetch_ml_listings(
    city_query: str = "Pouso Alegre MG",
    max_results: int = 200,
    output_csv: str = "data/ml_listings.csv",
    sleep_between_pages: float = 0.5,
    access_token: str | None = None,
) -> ApiCollectResult:
    """Fetch real estate listings from Mercado Livre API for a given city.

    Free, no authentication required. Rate limit: ~60 req/min anonymous.
    """
    rows: list[dict] = []
    errors: list[str] = []
    offset = 0
    limit = 50

    import os
    token = access_token or os.environ.get("ML_ACCESS_TOKEN")

    while offset < max_results:
        try:
            data = _ml_search(city_query, offset=offset, limit=min(limit, max_results - offset), access_token=token)
        except requests.HTTPError as exc:
            errors.append(f"offset={offset}: {exc}")
            break

        items = data.get("results", [])
        if not items:
            break

        for item in items:
            row = _ml_extract_row(item)
            if row:
                rows.append(row)

        offset += len(items)
        if offset >= data.get("paging", {}).get("total", 0):
            break

        time.sleep(sleep_between_pages)

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.drop_duplicates(subset=["ml_id"])
        # Filter to city if lat/lon available
        if "city" in df.columns:
            city_lower = city_query.lower().split()[0]
            mask = df["city"].str.lower().str.contains(city_lower, na=False)
            if mask.sum() > 0:
                df = df[mask]

    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False)

    return ApiCollectResult(
        source="mercadolivre",
        rows_fetched=len(df),
        output_path=output_csv,
        errors=errors,
    )


# ---------------------------------------------------------------------------
# IBGE demographic / housing data
# ---------------------------------------------------------------------------

def fetch_ibge_housing_indicators(
    ibge_code: str = _PA_IBGE_CODE,
    output_csv: str = "data/ibge_housing.csv",
) -> ApiCollectResult:
    """Fetch housing and population indicators from IBGE APIs (free, no key).

    Sources used:
      - API v3 Agregados (SIDRA): population estimates, income proxy
      - API v1 Localidades: municipality metadata
    """
    errors: list[str] = []
    rows: list[dict] = []

    # --- Info basica do municipio (sempre funciona) ---
    try:
        url = f"https://servicodados.ibge.gov.br/api/v1/localidades/municipios/{ibge_code}"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        muni = resp.json()
        uf = (
            muni.get("microrregiao", {})
            .get("mesorregiao", {})
            .get("UF", {})
            .get("sigla", "")
        )
        rows.append({"indicador": "nome_municipio", "codigo_ibge": ibge_code, "valor": muni.get("nome", "")})
        rows.append({"indicador": "uf", "codigo_ibge": ibge_code, "valor": uf})
        rows.append({"indicador": "mesorregiao", "codigo_ibge": ibge_code,
                     "valor": muni.get("microrregiao", {}).get("mesorregiao", {}).get("nome", "")})
    except Exception as exc:
        errors.append(f"localidades: {exc}")

    # --- Estimativa populacional (API v3, tabela 6579 — estimativas populacao) ---
    # Variavel 9324 = populacao estimada
    sidra_queries = [
        ("6579", "9324", "last", "populacao_estimada"),
    ]
    for tabela, variavel, periodo, nome in sidra_queries:
        url = (
            f"https://servicodados.ibge.gov.br/api/v3/agregados/{tabela}"
            f"/periodos/{periodo}/variaveis/{variavel}"
            f"?localidades=N6[{ibge_code}]"
        )
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            valor = (
                data[0]["resultados"][0]["series"][0]["serie"]
                if data and data[0].get("resultados")
                else None
            )
            if isinstance(valor, dict):
                valor = list(valor.values())[-1]  # valor do ultimo periodo
            rows.append({"indicador": nome, "codigo_ibge": ibge_code, "valor": valor})
        except Exception as exc:
            errors.append(f"sidra/{tabela}/{variavel}: {exc}")
            log.debug("IBGE SIDRA %s: %s", tabela, exc)

    # --- PIB per capita (tabela 5938, variavel 37) ---
    try:
        url = (
            "https://servicodados.ibge.gov.br/api/v3/agregados/5938"
            "/periodos/last/variaveis/37"
            f"?localidades=N6[{ibge_code}]"
        )
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if data and data[0].get("resultados"):
            serie = data[0]["resultados"][0]["series"][0]["serie"]
            valor_pib = list(serie.values())[-1] if isinstance(serie, dict) else None
            rows.append({"indicador": "pib_per_capita_reais", "codigo_ibge": ibge_code, "valor": valor_pib})
    except Exception as exc:
        errors.append(f"pib_per_capita: {exc}")

    df = pd.DataFrame(rows)
    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False)

    return ApiCollectResult(
        source="ibge",
        rows_fetched=len(df),
        output_path=output_csv,
        errors=errors,
    )


# ---------------------------------------------------------------------------
# ViaCEP — address/neighborhood enrichment
# ---------------------------------------------------------------------------

def enrich_with_viacep(df: pd.DataFrame, cep_col: str = "cep") -> pd.DataFrame:
    """Add neighborhood/city/state columns from CEP using ViaCEP API (free, no key)."""
    if cep_col not in df.columns:
        return df

    cache: dict[str, dict] = {}

    def _lookup(cep: str) -> dict:
        cep_clean = str(cep).replace("-", "").strip()
        if cep_clean not in cache:
            try:
                resp = requests.get(f"https://viacep.com.br/ws/{cep_clean}/json/", timeout=5)
                resp.raise_for_status()
                cache[cep_clean] = resp.json()
            except Exception:
                cache[cep_clean] = {}
        return cache[cep_clean]

    viacep_data = df[cep_col].apply(_lookup)
    df = df.copy()
    df["neighborhood"] = df.get("neighborhood", pd.Series(dtype=str))
    df["city"] = df.get("city", pd.Series(dtype=str))
    df["state"] = df.get("state", pd.Series(dtype=str))

    for idx, row_data in viacep_data.items():
        if row_data and not row_data.get("erro"):
            if pd.isna(df.at[idx, "neighborhood"]):
                df.at[idx, "neighborhood"] = row_data.get("bairro", "")
            if pd.isna(df.at[idx, "city"]):
                df.at[idx, "city"] = row_data.get("localidade", "")
            if pd.isna(df.at[idx, "state"]):
                df.at[idx, "state"] = row_data.get("uf", "")

    return df
