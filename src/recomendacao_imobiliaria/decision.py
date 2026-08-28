from __future__ import annotations

import json
from pathlib import Path
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class OpportunityProfile:
    h3_id: str
    priority: str
    primary_use: str
    risk_level: str
    summary: str


def enrich_opportunities(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame.copy()

    result = frame.copy()
    profiles = [_profile_row(row) for row in result.to_dict(orient="records")]
    profile_frame = pd.DataFrame([profile.__dict__ for profile in profiles])
    return result.merge(profile_frame, on="h3_id", how="left")


def _profile_row(row: dict[str, object]) -> OpportunityProfile:
    h3_id = str(row.get("h3_id"))
    residential = _as_float(row.get("score_residencial"))
    commercial = _as_float(row.get("score_comercial"))
    growth = _growth_signal(row)
    risk = _risk_level(row)
    primary_use = "residencial" if residential >= commercial else "comercial"
    best_score = max(residential, commercial)
    priority = _priority(best_score, risk)
    summary = _summary(row, primary_use, best_score, growth, risk)
    legal_status = _legal_status(row)
    if legal_status == "bloqueado":
        primary_use = "analise legal"
    return OpportunityProfile(
        h3_id=h3_id,
        priority=priority,
        primary_use=primary_use,
        risk_level=risk,
        summary=summary,
    )


def _priority(score: float, risk: str) -> str:
    if risk == "alto":
        return "investigar"
    thresholds = _priority_thresholds()
    if score >= thresholds["high"]:
        return "alta"
    if score >= thresholds["medium"]:
        return "media"
    return "baixa"


def _priority_thresholds() -> dict[str, float]:
    try:
        raw = json.loads((Path("config") / "scoring_weights.json").read_text(encoding="utf-8"))
        values = raw.get("priority_thresholds", {})
        return {"high": float(values.get("high", 70)), "medium": float(values.get("medium", 50))}
    except (OSError, ValueError, json.JSONDecodeError):
        return {"high": 70.0, "medium": 50.0}


def _risk_level(row: dict[str, object]) -> str:
    explain = _parse_explain(row.get("explain_json"))
    zoning = explain.get("zoning", {}) if isinstance(explain, dict) else {}
    if zoning and (not zoning.get("residential_allowed", True) or not zoning.get("commercial_allowed", True)):
        return "alto"
    if zoning and (
        zoning.get("residential_plan_status") == "conditioned"
        or zoning.get("commercial_plan_status") == "conditioned"
    ):
        return "medio"

    # Triagem conservadora de cobertura: não substitui licença ou CAR, mas evita
    # promover corpos d'água/áreas alagadas como oportunidade imobiliária.
    cover = str(row.get("land_cover_class") or "").lower()
    if cover in {"corpo dagua", "campo alagado"}:
        return "alto"
    if cover == "formacao florestal":
        return "medio"

    # A carta técnica oficial prevalece sobre a inferência analítica/satelital.
    official_risk = str(row.get("official_risk_level") or "").lower()
    if official_risk in {"alto", "medio"}:
        return official_risk

    satellite_alert = str(row.get("satellite_risk_alert") or "")
    satellite_confidence = _as_float(row.get("satellite_risk_confidence"))
    if satellite_confidence >= 0.45 and satellite_alert == "alto":
        return "alto"
    if satellite_confidence >= 0.45 and satellite_alert == "medio":
        return "medio"

    ndvi_slope = _as_float(row.get("ndvi_slope_180"))
    ndbi_slope = _as_float(row.get("ndbi_slope_180"))
    if ndvi_slope < -0.0015 and ndbi_slope > 0.0015:
        return "medio"
    return "baixo"


def _growth_signal(row: dict[str, object]) -> str:
    if bool(row.get("observed_urban_expansion")):
        return "expansao urbana observada no MapBiomas (2019–2024)"
    cover = str(row.get("land_cover_class") or "").lower()
    if cover in {"formacao florestal", "campo alagado", "corpo dagua"}:
        return "cobertura ambiental sensivel"
    ndvi_slope = _as_float(row.get("ndvi_slope_180"))
    ndbi_slope = _as_float(row.get("ndbi_slope_180"))
    if ndvi_slope < 0 and ndbi_slope > 0:
        return "expansao urbana provavel"
    if ndbi_slope > 0:
        return "adensamento leve"
    if ndvi_slope > 0:
        return "estabilidade ambiental"
    return "sem sinal forte"


def _summary(
    row: dict[str, object],
    primary_use: str,
    best_score: float,
    growth: str,
    risk: str,
) -> str:
    explain = _parse_explain(row.get("explain_json"))
    recommendations = explain.get("main_recommendations", []) if isinstance(explain, dict) else []
    if recommendations:
        uses = ", ".join(str(item.get("use")) for item in recommendations if item.get("use"))
        reason = f"Uso sugerido: {uses}."
    else:
        reason = "Sem carencia comercial prioritaria."
    zoning = explain.get("zoning", {}) if isinstance(explain, dict) else {}
    legal = zoning.get("legal_notes")
    legal_text = f" Plano Diretor: {legal}" if legal else ""
    land_cover = str(row.get("land_cover_transition") or "")
    land_text = f" Cobertura do solo: {land_cover}." if land_cover else ""
    return (
        f"Prioridade para {primary_use} com score {best_score:.1f}. "
        f"Sinal: {growth}. Risco: {risk}. {reason}{legal_text}{land_text}"
    )


def _legal_status(row: dict[str, object]) -> str:
    explain = _parse_explain(row.get("explain_json"))
    zoning = explain.get("zoning", {}) if isinstance(explain, dict) else {}
    statuses = {
        str(zoning.get("residential_plan_status", "allowed")),
        str(zoning.get("commercial_plan_status", "allowed")),
    }
    if "blocked" in statuses:
        return "bloqueado"
    if "conditioned" in statuses:
        return "condicionado"
    return "permitido"


def _parse_explain(value) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {}
    return {}


def _as_float(value) -> float:
    if value is None or pd.isna(value):
        return 0.0
    return float(value)
