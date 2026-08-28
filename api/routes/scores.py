from __future__ import annotations

import math

from fastapi import APIRouter

router = APIRouter()


def _clean(val):
    if val is None:
        return None
    try:
        if math.isnan(val):
            return None
    except (TypeError, ValueError):
        pass
    return val


def _sanitise(row: dict) -> dict:
    return {k: _clean(v) for k, v in row.items()}


def _parse_explain(raw) -> dict:
    import json
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return {}
    if not isinstance(raw, dict):
        return {}
    return {
        "growth_signal":    raw.get("growth_signal"),
        "commercial_gap":   raw.get("commercial_gap"),
        "mixed_access":     raw.get("mixed_access"),
        "confidence":       raw.get("confidence"),
        "positive_factors": raw.get("positive_factors", []),
        "negative_factors": raw.get("negative_factors", []),
        "contributions":    raw.get("contributions", {}),
        "recommendations":  raw.get("main_recommendations", []),
        "zona":             (raw.get("zoning") or {}).get("zona"),
        "legal_notes":      (raw.get("zoning") or {}).get("legal_notes"),
        "legal_articles":   (raw.get("zoning") or {}).get("legal_articles", []),
        "legal_parameters": (raw.get("zoning") or {}).get("legal_parameters", {}),
        "legal_sources":    (raw.get("zoning") or {}).get("legal_sources", []),
    }


def _km(value) -> str:
    if value is None:
        return "sem dado"
    try:
        return f"{float(value) / 1000:.1f} km"
    except (TypeError, ValueError):
        return "sem dado"


def _growth_text(value) -> str:
    try:
        n = float(value or 0)
    except (TypeError, ValueError):
        return "crescimento sem leitura suficiente"
    if n > 0.003:
        return "crescimento urbano acelerado"
    if n > 0.001:
        return "crescimento urbano moderado"
    if n < -0.001:
        return "retração ou perda de area construida"
    return "area relativamente estavel"


def _build_explainability(record: dict) -> list[dict[str, str]]:
    gaps = []
    if (record.get("poi_school_cnt") or 0) <= 1:
        gaps.append(f"escolas/creches proximas: {record.get('poi_school_cnt') or 0}; menor distancia {_km(record.get('dist_min_school_m'))}")
    if (record.get("poi_supermarket_cnt") or 0) <= 1:
        gaps.append(f"mercados proximos: {record.get('poi_supermarket_cnt') or 0}; menor distancia {_km(record.get('dist_min_supermarket_m'))}")
    if (record.get("poi_pharmacy_cnt") or 0) <= 1:
        gaps.append(f"farmacias proximas: {record.get('poi_pharmacy_cnt') or 0}; menor distancia {_km(record.get('dist_min_pharmacy_m'))}")

    return [
        {
            "label": "Equipamentos e servicos",
            "value": "; ".join(gaps) if gaps else "boa cobertura dos servicos medidos no entorno",
        },
        {
            "label": "Comercio faltante",
            "value": ", ".join(item.get("use", "") for item in record.get("recommendations", [])[:3]) or "sem lacuna comercial forte",
        },
        {
            "label": "Zoneamento",
            "value": record.get("legal_notes") or record.get("zona") or "zoneamento nao identificado",
        },
        {
            "label": "Crescimento urbano",
            "value": _growth_text(record.get("ndbi_slope_180") or record.get("growth_signal")),
        },
        {
            "label": "Risco",
            "value": f"risco {record.get('risk_level') or 'nao classificado'}; confianca {record.get('confidence') or '-'}",
        },
    ]


@router.get("/scores")
def get_scores():
    from recomendacao_imobiliaria.reporting import load_score_table

    df = load_score_table()
    rows = []
    for r in df.to_dict(orient="records"):
        explain_raw = r.pop("explain_json", None)
        record = _sanitise(r)
        record.update(_parse_explain(explain_raw))
        record["explainability"] = _build_explainability(record)
        rows.append(record)
    return rows
