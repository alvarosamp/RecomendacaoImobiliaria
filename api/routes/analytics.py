from __future__ import annotations

import math
from functools import lru_cache

from fastapi import APIRouter

router = APIRouter()

GAP_CONFIG = [
    {
        "type": "farmacia",
        "label": "Farmácia / Drogaria",
        "description": (
            "Serviço de saúde essencial para acesso a medicamentos, especialmente "
            "em áreas com população idosa ou familiar consolidada."
        ),
        "col_cnt":  "poi_pharmacy_cnt",
        "col_dist": "dist_min_pharmacy_m",
        "threshold_m": 1800,
        "zoning": "ZMU, ZC, ZMC",
    },
    {
        "type": "mercado",
        "label": "Mercado / Supermercado",
        "description": (
            "Ausência força moradores a deslocamentos longos, aumentando custo de vida "
            "e indicando oportunidade de alto fluxo para comércio de abastecimento."
        ),
        "col_cnt":  "poi_supermarket_cnt",
        "col_dist": "dist_min_supermarket_m",
        "threshold_m": 2500,
        "zoning": "ZC, ZMC, ZMU",
    },
    {
        "type": "escola",
        "label": "Escola / Creche",
        "description": (
            "Déficit educacional é indicador de bairro em expansão residencial "
            "que ainda não recebeu infraestrutura pública compatível."
        ),
        "col_cnt":  "poi_school_cnt",
        "col_dist": "dist_min_school_m",
        "threshold_m": 2200,
        "zoning": "Zonas residenciais e mistas",
    },
    {
        "type": "hospital",
        "label": "Hospital / UPA",
        "description": (
            "Atendimento de urgência e internação. "
            "Áreas distantes de hospitais têm maior vulnerabilidade em saúde e maior "
            "valorização quando recebem este equipamento."
        ),
        "col_cnt":  "poi_hospital_cnt",
        "col_dist": "dist_min_hospital_m",
        "threshold_m": 5000,
        "zoning": "ZMU, ZC, ZE",
    },
    {
        "type": "area_verde",
        "label": "Parque / Área verde",
        "description": (
            "Presença de parques e áreas verdes eleva qualidade de vida, "
            "valoriza imóveis residenciais próximos e é indicador de bairros maduros."
        ),
        "col_cnt":  "poi_leisure_cnt",
        "col_dist": "dist_min_park_m",
        "threshold_m": 1500,
        "zoning": "ZR1, ZR2, ZMU",
    },
]

TYPOLOGY_FEATURES = [
    "ndbi_mean_90", "ndvi_mean_90", "ndvi_slope_180",
    "poi_supermarket_cnt", "poi_pharmacy_cnt", "poi_school_cnt",
    "poi_hospital_cnt", "poi_leisure_cnt",
    "dist_min_supermarket_m", "dist_min_pharmacy_m", "dist_min_hospital_m",
]

TYPOLOGY_NAMES = [
    "Urbano denso",
    "Residencial consolidado",
    "Em expansão",
    "Rural / periférico",
]


def _load_features():
    """Load geo.features + geo.scores + zona joined."""
    from sqlalchemy import text
    from recomendacao_imobiliaria.config import load_settings
    from recomendacao_imobiliaria.db import make_engine
    import pandas as pd

    settings = load_settings()
    engine = make_engine(settings)
    try:
        df = pd.read_sql(
            text("""
                SELECT
                    f.h3_id,
                    f.ndbi_mean_90, f.ndvi_mean_90, f.ndvi_slope_180, f.ndbi_slope_180,
                    f.poi_supermarket_cnt, f.poi_pharmacy_cnt, f.poi_school_cnt,
                    f.poi_hospital_cnt, f.poi_restaurant_cnt, f.poi_bank_cnt,
                    f.poi_leisure_cnt,
                    f.dist_min_supermarket_m, f.dist_min_pharmacy_m, f.dist_min_school_m,
                    f.dist_min_hospital_m, f.dist_min_park_m, f.dist_min_bus_stop_m,
                    f.pop_estimated,
                    z.zona,
                    s.score_residencial, s.score_comercial,
                    s.explain_json
                FROM geo.features f
                LEFT JOIN geo.v_h3_zona z USING (h3_id)
                LEFT JOIN geo.scores s USING (h3_id)
            """),
            engine,
        )
    finally:
        engine.dispose()
    return df


def _compute_typology(df):
    """KMeans on spatial features → typology label per cell."""
    import numpy as np
    try:
        from sklearn.preprocessing import StandardScaler
        from sklearn.cluster import KMeans
    except ImportError:
        return {}

    cols = [c for c in TYPOLOGY_FEATURES if c in df.columns]
    valid = df.dropna(subset=cols[:2]).copy()
    if len(valid) < 4:
        return {}

    X = valid[cols].fillna(0).values.astype(float)
    X_scaled = StandardScaler().fit_transform(X)

    km = KMeans(n_clusters=4, random_state=42, n_init=10)
    labels = km.fit_predict(X_scaled)

    # Sort clusters by ndbi (index 0) → highest NDBI = most urban
    ndbi_idx = cols.index("ndbi_mean_90") if "ndbi_mean_90" in cols else 0
    cluster_means = [X[labels == c, ndbi_idx].mean() for c in range(4)]
    order = sorted(range(4), key=lambda c: cluster_means[c], reverse=True)
    name_map = {old: TYPOLOGY_NAMES[rank] for rank, old in enumerate(order)}

    return {row["h3_id"]: name_map[labels[i]] for i, (_, row) in enumerate(valid.iterrows())}


def _growth_label(slope: float | None) -> str:
    if slope is None:
        return "dados insuficientes"
    if slope > 0.002:
        return "urbanização acelerada"
    if slope > 0.0005:
        return "crescimento moderado"
    if slope < -0.001:
        return "perda de área construída"
    return "estável"


def _build_reasons(row, cfg: dict, typology: str) -> list[str]:
    reasons = []
    dist = row.get(cfg["col_dist"])
    if dist and not math.isnan(dist):
        reasons.append(f"{cfg['label']} mais próxima a {dist/1000:.1f} km")
    reasons.append(f"Tipologia: {typology}")
    slope = row.get("ndbi_slope_180")
    reasons.append(f"Sinal de crescimento: {_growth_label(slope)}")
    zona = row.get("zona") or "não identificada"
    reasons.append(f"Zoneamento: {zona} — usos permitidos: {cfg['zoning']}")
    pop = row.get("pop_estimated")
    if pop and not math.isnan(float(pop or 0)):
        reasons.append(f"Estimativa de {int(pop):,} moradores na célula (IBGE Censo 2022)")
    score_res = row.get("score_residencial")
    if score_res and not math.isnan(score_res):
        reasons.append(f"Score residencial: {score_res:.0f}/100 (potencial de moradores)")
    return reasons


@router.get("/analytics/commerce-gaps")
def commerce_gaps():
    try:
        import math as _math
        df = _load_features()
        typology_map = _compute_typology(df)

        result = []
        for cfg in GAP_CONFIG:
            col_d = cfg["col_dist"]
            col_c = cfg["col_cnt"]
            if col_d not in df.columns:
                continue

            mask = (
                (df[col_d].fillna(9999) > cfg["threshold_m"]) |
                (df[col_c].fillna(0) == 0)
            )
            gap_df = df[mask].copy()

            # Rank by distance (furthest from service = highest impact)
            gap_df = gap_df.sort_values(col_d, ascending=False).head(20)

            locations = []
            for _, row in gap_df.iterrows():
                h3 = row["h3_id"]
                typ = typology_map.get(h3, "–")
                dist = row.get(col_d)
                dist_clean = None if (dist is None or _math.isnan(dist)) else round(float(dist))
                locations.append({
                    "h3_id": h3,
                    "dist_m": dist_clean,
                    "score_residencial": None if _math.isnan(row.get("score_residencial") or float("nan")) else round(float(row.get("score_residencial") or 0), 1),
                    "typology": typ,
                    "zona": row.get("zona") or "–",
                    "growth_signal": round(float(row.get("ndbi_slope_180") or 0), 4),
                    "reasons": _build_reasons(row, cfg, typ),
                })

            result.append({
                "type": cfg["type"],
                "label": cfg["label"],
                "description": cfg["description"],
                "cells_affected": int(mask.sum()),
                "top_locations": locations[:5],
            })

        return result

    except Exception as exc:
        return {"error": str(exc)}


@router.get("/analytics/typology")
def cell_typology():
    try:
        df = _load_features()
        typology_map = _compute_typology(df)
        return typology_map
    except Exception as exc:
        return {"error": str(exc)}
