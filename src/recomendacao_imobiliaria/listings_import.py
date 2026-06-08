"""Normalize and import real property listings from Brazilian portals into ML format."""
from __future__ import annotations

import dataclasses
import re
from pathlib import Path

import pandas as pd


# Column aliases found in common BR portal exports (OLX, ZAP, VivaReal, Imovelweb)
_ALIASES: dict[str, list[str]] = {
    "price": ["preco", "valor", "price", "venda", "preco_venda", "valor_venda", "preco_total"],
    "area_m2": ["area", "area_m2", "area_util", "area_total", "metragem", "metros", "tamanho"],
    "bedrooms": ["quartos", "dormitorios", "suites", "bedrooms", "dorms", "quarto"],
    "bathrooms": ["banheiros", "wc", "bathrooms", "banheiro"],
    "parking_spaces": ["vagas", "garagem", "parking", "vaga", "estacionamento"],
    "property_type": ["tipo", "tipo_imovel", "property_type", "categoria", "subtipo"],
    "neighborhood": ["bairro", "neighborhood", "regiao", "bairro_oficial"],
    "city": ["cidade", "city", "municipio"],
    "state": ["estado", "state", "uf"],
    "address": ["endereco", "logradouro", "address", "rua"],
    "lat": ["lat", "latitude", "latitudine"],
    "lon": ["lon", "lng", "longitude", "longitudine"],
    "zona": ["zona", "zone", "zoneamento", "cod_zona"],
    "score_residencial": ["score_residencial", "score_res"],
    "score_comercial": ["score_comercial", "score_com"],
    "ndvi_mean_90": ["ndvi", "ndvi_mean", "ndvi_mean_90", "ndvi_90"],
    "ndbi_mean_90": ["ndbi", "ndbi_mean", "ndbi_mean_90", "ndbi_90"],
}


@dataclasses.dataclass
class ListingsImportResult:
    rows_read: int
    rows_valid: int
    output_path: str
    missing_columns: list[str]


def normalize_listings(input_csv: str, output_csv: str | None = None) -> ListingsImportResult:
    """Read a CSV from any Brazilian portal, normalize column names, clean values,
    and write to a standard format compatible with train_price_model().
    """
    df = pd.read_csv(input_csv, low_memory=False)
    rows_read = len(df)

    # Build reverse map from alias → canonical name
    reverse: dict[str, str] = {}
    for canonical, aliases in _ALIASES.items():
        for alias in aliases:
            reverse[alias.lower()] = canonical

    rename_map = {
        col: reverse[col.lower()]
        for col in df.columns
        if col.lower() in reverse
    }
    df = df.rename(columns=rename_map)

    missing = [c for c in ["price", "area_m2"] if c not in df.columns]

    # ---- price cleaning ----
    if "price" in df.columns:
        df["price"] = (
            df["price"]
            .astype(str)
            .str.replace(r"[R$\s\.]", "", regex=True)
            .str.replace(",", ".")
        )
        df["price"] = pd.to_numeric(df["price"], errors="coerce")

    # ---- area cleaning ----
    if "area_m2" in df.columns:
        df["area_m2"] = (
            df["area_m2"]
            .astype(str)
            .str.extract(r"(\d+[\.,]?\d*)")[0]
            .str.replace(",", ".")
        )
        df["area_m2"] = pd.to_numeric(df["area_m2"], errors="coerce")

    # ---- bedrooms / bathrooms / parking ----
    for col in ["bedrooms", "bathrooms", "parking_spaces"]:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.extract(r"(\d+)")[0],
                errors="coerce",
            )

    # ---- property_type normalization ----
    if "property_type" in df.columns:
        type_map = {
            "apartamento": "apartamento",
            "apto": "apartamento",
            "ap": "apartamento",
            "casa": "casa",
            "casa condominio": "casa_condominio",
            "terreno": "terreno",
            "lote": "terreno",
            "loteamento": "terreno",
            "comercial": "comercial",
            "sala": "comercial",
            "loja": "comercial",
            "galpao": "galpao",
            "sitio": "rural",
            "fazenda": "rural",
            "chacara": "rural",
        }
        df["property_type"] = (
            df["property_type"]
            .astype(str)
            .str.strip()
            .str.lower()
            .map(lambda v: next((mapped for key, mapped in type_map.items() if key in v), v))
        )

    # ---- lat/lon type ----
    for coord in ["lat", "lon"]:
        if coord in df.columns:
            df[coord] = pd.to_numeric(df[coord], errors="coerce")

    # ---- drop rows without price or area ----
    df_valid = df.copy()
    if "price" in df_valid.columns:
        df_valid = df_valid[df_valid["price"].notna() & (df_valid["price"] > 0)]
    if "area_m2" in df_valid.columns:
        df_valid = df_valid[df_valid["area_m2"].notna() & (df_valid["area_m2"] > 0)]

    # ---- price sanity (remove outliers beyond 3σ) ----
    if "price" in df_valid.columns and len(df_valid) > 10:
        mu, sigma = df_valid["price"].mean(), df_valid["price"].std()
        df_valid = df_valid[df_valid["price"].between(mu - 3 * sigma, mu + 3 * sigma)]

    if output_csv is None:
        stem = Path(input_csv).stem
        output_csv = str(Path(input_csv).parent / f"{stem}_normalized.csv")

    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    df_valid.to_csv(output_csv, index=False)

    return ListingsImportResult(
        rows_read=rows_read,
        rows_valid=len(df_valid),
        output_path=output_csv,
        missing_columns=missing,
    )


def generate_realistic_listings(
    output_csv: str = "data/pouso_alegre_listings.csv",
    n: int = 500,
    seed: int = 42,
) -> str:
    """Generate a realistic synthetic dataset of property listings for Pouso Alegre.

    Distributions are calibrated to the local market (2024 reference values).
    """
    import numpy as np

    rng = np.random.default_rng(seed)

    neighborhoods = [
        ("Centro", "ZMC", -22.230, -45.948, 1.0),
        ("Bela Vista", "ZM", -22.220, -45.960, 0.85),
        ("Jardim Panorama", "ZM1", -22.215, -45.942, 0.80),
        ("São Geraldo", "ZM2", -22.240, -45.952, 0.75),
        ("Santa Luzia", "ZMV", -22.235, -45.940, 0.90),
        ("Jardim São Paulo", "ZEIS", -22.250, -45.965, 0.55),
        ("Vila Formosa", "ZEIS", -22.245, -45.955, 0.58),
        ("Bairro Industrial", "ZEU", -22.205, -45.945, 0.60),
        ("Novo Horizonte", "ZEU", -22.210, -45.970, 0.62),
        ("Parque das Acácias", "ZM", -22.225, -45.972, 0.78),
    ]

    prop_types = ["apartamento", "casa", "casa_condominio", "terreno", "comercial"]
    prop_weights = [0.35, 0.40, 0.10, 0.10, 0.05]

    rows = []
    for _ in range(n):
        nb_idx = rng.integers(len(neighborhoods))
        nb, zona, lat_c, lon_c, price_factor = neighborhoods[nb_idx]

        ptype = rng.choice(prop_types, p=prop_weights)

        if ptype == "terreno":
            area = float(rng.integers(200, 1200))
            beds, baths, parking = 0, 0, 0
            base_price_m2 = float(rng.uniform(300, 700) * price_factor)
        elif ptype == "apartamento":
            area = float(rng.integers(40, 160))
            beds = int(rng.integers(1, 4))
            baths = max(1, beds - 1 + int(rng.integers(0, 2)))
            parking = int(rng.integers(0, 3))
            base_price_m2 = float(rng.uniform(3500, 7000) * price_factor)
        elif ptype == "casa_condominio":
            area = float(rng.integers(80, 300))
            beds = int(rng.integers(2, 5))
            baths = beds
            parking = int(rng.integers(1, 4))
            base_price_m2 = float(rng.uniform(3000, 6000) * price_factor)
        elif ptype == "comercial":
            area = float(rng.integers(30, 500))
            beds, baths, parking = 0, 1, int(rng.integers(0, 5))
            base_price_m2 = float(rng.uniform(2000, 5000) * price_factor)
        else:  # casa
            area = float(rng.integers(60, 280))
            beds = int(rng.integers(2, 5))
            baths = max(1, beds - 1)
            parking = int(rng.integers(0, 3))
            base_price_m2 = float(rng.uniform(2500, 5500) * price_factor)

        noise = float(rng.normal(1.0, 0.12))
        price = round(area * base_price_m2 * noise, -3)

        lat = float(rng.normal(lat_c, 0.005))
        lon = float(rng.normal(lon_c, 0.005))

        ndvi = float(rng.uniform(0.15, 0.55))
        ndbi = float(rng.uniform(-0.25, 0.10))
        score_res = float(rng.uniform(0.3, 0.95) * price_factor)
        score_com = float(rng.uniform(0.2, 0.85) * price_factor)

        rows.append(
            {
                "price": price,
                "area_m2": area,
                "bedrooms": beds,
                "bathrooms": baths,
                "parking_spaces": parking,
                "property_type": ptype,
                "neighborhood": nb,
                "zona": zona,
                "city": "Pouso Alegre",
                "state": "MG",
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "score_residencial": round(score_res, 4),
                "score_comercial": round(score_com, 4),
                "ndvi_mean_90": round(ndvi, 4),
                "ndbi_mean_90": round(ndbi, 4),
            }
        )

    df = pd.DataFrame(rows)
    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False)
    return output_csv
