"""Calibra faixas de prioridade a partir da distribuição observada de scores."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from .config import load_settings
from .data_registry import record_data_source
from .db import make_engine


def calibrate_priorities(config_path: str = "config/scoring_weights.json", *, apply: bool = False, settings=None) -> dict[str, object]:
    active_settings = settings or load_settings()
    engine = make_engine(active_settings)
    try:
        with engine.connect() as conn:
            frame = pd.read_sql(text("""
                SELECT GREATEST(score_residencial, score_comercial) AS score
                FROM geo.scores WHERE score_residencial IS NOT NULL OR score_comercial IS NOT NULL
            """), conn)
    finally:
        engine.dispose()
    if len(frame) < 20:
        raise ValueError("São necessários ao menos 20 scores para recalibrar prioridades.")
    scores = frame["score"].astype(float)
    spread = float(scores.quantile(0.90) - scores.quantile(0.10))
    if spread < 1.0:
        payload = {
            "sample_size": len(scores), "score_spread_p90_p10": round(spread, 2),
            "status": "waiting_for_discriminative_data",
            "reason": "A dispersão dos scores é insuficiente; mantenho os pesos e faixas atuais para não criar prioridades artificiais.",
            "applied": False,
        }
        record_data_source("scoring_calibration", "quantile_calibration", source_uri=config_path, row_count=len(scores), status="waiting_data", details=payload, settings=active_settings)
        return payload
    # Em cidades pequenas é comum haver uma massa no score-base (mesmos POIs
    # e índices ainda pouco discriminativos). O percentil 90 evita que essa
    # massa inteira seja promovida a "alta" apenas por empate numérico.
    thresholds = {"high": round(float(scores.quantile(0.90)), 2), "medium": round(float(scores.quantile(0.70)), 2)}
    if thresholds["high"] <= thresholds["medium"]:
        thresholds["high"] = round(thresholds["medium"] + 0.01, 2)
    payload = {"sample_size": len(scores), "score_spread_p90_p10": round(spread, 2), "priority_thresholds": thresholds, "method": "quantis_90_70", "calibrated_at": date.today().isoformat()}
    if apply:
        path = Path(config_path)
        raw = json.loads(path.read_text(encoding="utf-8"))
        raw["priority_thresholds"] = thresholds
        raw["calibration"] = {key: value for key, value in payload.items() if key != "priority_thresholds"}
        path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    record_data_source("scoring_calibration", "quantile_calibration", source_uri=config_path, row_count=len(scores), details={**payload, "applied": apply}, settings=active_settings)
    return {**payload, "applied": apply}
