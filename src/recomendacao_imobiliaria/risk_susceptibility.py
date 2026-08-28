"""Alerta de suscetibilidade territorial com evidencias satelitais e de relevo.

O resultado e um sinal de triagem, nunca um laudo ou uma classificacao legal de risco.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

import pandas as pd
from sqlalchemy import text

from .config import Settings, load_settings
from .db import db_engine


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


@dataclass(frozen=True)
class RiskSignal:
    susceptibility_score: float
    alert_level: str
    confidence: float
    components: dict[str, float]
    evidence: dict[str, object]


def assess_susceptibility(
    *,
    ndvi_slope_180: float | None = None,
    ndbi_slope_180: float | None = None,
    slope_pct: float | None = None,
    drainage_distance_m: float | None = None,
    water_observation_rate: float | None = None,
) -> RiskSignal:
    """Combina sinais disponíveis, reduzindo a confiança quando faltam camadas.

    ``water_observation_rate`` deve ser a fração 0–1 de observações com água
    em uma série Sentinel-1/SAR. Relevo e drenagem devem vir de fontes oficiais
    ou DEM devidamente registrado.
    """
    components: dict[str, float] = {}
    weights: dict[str, float] = {}
    evidence: dict[str, object] = {"type": "suscetibilidade_analitica"}

    if slope_pct is not None:
        components["declividade"] = _clamp(float(slope_pct) / 25.0)
        weights["declividade"] = 0.30
        evidence["slope_pct"] = float(slope_pct)
    if drainage_distance_m is not None:
        components["proximidade_drenagem"] = _clamp(1 - (float(drainage_distance_m) / 300.0))
        weights["proximidade_drenagem"] = 0.25
        evidence["drainage_distance_m"] = float(drainage_distance_m)
    if water_observation_rate is not None:
        components["recorrencia_agua_sar"] = _clamp(float(water_observation_rate))
        weights["recorrencia_agua_sar"] = 0.30
        evidence["water_observation_rate"] = float(water_observation_rate)

    if ndvi_slope_180 is not None or ndbi_slope_180 is not None:
        vegetation_loss = _clamp(-float(ndvi_slope_180 or 0) / 0.004)
        built_growth = _clamp(float(ndbi_slope_180 or 0) / 0.004)
        components["pressao_urbanizacao_satelite"] = round((vegetation_loss + built_growth) / 2, 4)
        weights["pressao_urbanizacao_satelite"] = 0.15
        evidence["ndvi_slope_180"] = ndvi_slope_180
        evidence["ndbi_slope_180"] = ndbi_slope_180

    if not weights:
        return RiskSignal(0.0, "dados_insuficientes", 0.0, {}, evidence)

    total_weight = sum(weights.values())
    score = sum(components[key] * weights[key] for key in weights) / total_weight
    confidence = total_weight
    if confidence < 0.45:
        level = "em_observacao"
    elif score >= 0.70:
        level = "alto"
    elif score >= 0.40:
        level = "medio"
    else:
        level = "baixo"
    return RiskSignal(round(score, 4), level, round(confidence, 2), components, evidence)


def calculate_risk_signals(settings: Settings | None = None) -> int:
    settings = settings or load_settings()
    with db_engine(settings) as engine:
        frame = pd.read_sql(
            text("""
                SELECT f.h3_id, f.ndvi_slope_180, f.ndbi_slope_180,
                       i.slope_pct, i.drainage_distance_m, i.water_observation_rate
                FROM geo.features f
                LEFT JOIN geo.risk_inputs i USING (h3_id)
            """),
            engine,
        )
        with engine.begin() as conn:
            for row in frame.to_dict(orient="records"):
                values = {key: (None if pd.isna(value) else value) for key, value in row.items()}
                signal = assess_susceptibility(
                    ndvi_slope_180=values["ndvi_slope_180"],
                    ndbi_slope_180=values["ndbi_slope_180"],
                    slope_pct=values["slope_pct"],
                    drainage_distance_m=values["drainage_distance_m"],
                    water_observation_rate=values["water_observation_rate"],
                )
                conn.execute(text("""
                    INSERT INTO geo.risk_signals
                    (h3_id, susceptibility_score, alert_level, confidence, components, evidence, calculated_at)
                    VALUES (:h3_id, :score, :alert_level, :confidence, CAST(:components AS jsonb),
                            CAST(:evidence AS jsonb), now())
                    ON CONFLICT (h3_id) DO UPDATE SET
                      susceptibility_score = EXCLUDED.susceptibility_score,
                      alert_level = EXCLUDED.alert_level,
                      confidence = EXCLUDED.confidence,
                      components = EXCLUDED.components,
                      evidence = EXCLUDED.evidence,
                      calculated_at = now()
                """), {
                    "h3_id": values["h3_id"], "score": signal.susceptibility_score,
                    "alert_level": signal.alert_level, "confidence": signal.confidence,
                    "components": json.dumps(signal.components), "evidence": json.dumps(signal.evidence),
                })
    return len(frame)


def import_risk_inputs_csv(csv_path: str, settings: Settings | None = None, source_name: str = "external") -> int:
    """Importa relevo, drenagem e água SAR por H3 sem misturar esses dados ao score legal."""
    frame = pd.read_csv(csv_path)
    if "h3_id" not in frame.columns:
        raise ValueError("CSV de risco deve conter h3_id")
    allowed = ["slope_pct", "drainage_distance_m", "water_observation_rate", "reference_date"]
    for column in allowed:
        if column not in frame.columns:
            frame[column] = None
    settings = settings or load_settings()
    with db_engine(settings) as engine, engine.begin() as conn:
        for row in frame[["h3_id", *allowed]].to_dict(orient="records"):
            values = {key: (None if pd.isna(value) else value) for key, value in row.items()}
            conn.execute(text("""
                INSERT INTO geo.risk_inputs
                (h3_id, slope_pct, drainage_distance_m, water_observation_rate, source_name, reference_date, updated_at)
                VALUES (:h3_id, :slope_pct, :drainage_distance_m, :water_observation_rate,
                        :source_name, :reference_date, now())
                ON CONFLICT (h3_id) DO UPDATE SET
                  slope_pct = EXCLUDED.slope_pct, drainage_distance_m = EXCLUDED.drainage_distance_m,
                  water_observation_rate = EXCLUDED.water_observation_rate, source_name = EXCLUDED.source_name,
                  reference_date = EXCLUDED.reference_date, updated_at = now()
            """), {**values, "source_name": source_name})
    return len(frame)
