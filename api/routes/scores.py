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
        "recommendations":  raw.get("main_recommendations", []),
        "zona":             (raw.get("zoning") or {}).get("zona"),
        "legal_notes":      (raw.get("zoning") or {}).get("legal_notes"),
    }


@router.get("/scores")
def get_scores():
    from recomendacao_imobiliaria.reporting import load_score_table

    df = load_score_table()
    rows = []
    for r in df.to_dict(orient="records"):
        explain_raw = r.pop("explain_json", None)
        record = _sanitise(r)
        record.update(_parse_explain(explain_raw))
        rows.append(record)
    return rows
