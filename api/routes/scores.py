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


@router.get("/scores")
def get_scores():
    from recomendacao_imobiliaria.reporting import load_score_table

    df = load_score_table()
    if "explain_json" in df.columns:
        df = df.drop(columns=["explain_json"])
    return [_sanitise(r) for r in df.to_dict(orient="records")]
