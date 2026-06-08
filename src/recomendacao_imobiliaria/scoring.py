from __future__ import annotations

from dataclasses import dataclass, field


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def inverse_distance_score(distance_m: float | None, target_m: float) -> float:
    if distance_m is None:
        return 0.0
    return clamp(1.0 - (distance_m / target_m))


def unmet_demand_score(count: int | None, target_count: int) -> float:
    current = count or 0
    if target_count <= 0:
        return 0.0
    return clamp((target_count - current) / target_count)


@dataclass(frozen=True)
class AreaFeatures:
    h3_id: str
    zona: str | None = None
    ndvi_mean_90: float | None = None
    ndvi_slope_180: float | None = None
    ndbi_mean_90: float | None = None
    ndbi_slope_180: float | None = None
    poi_supermarket_cnt: int | None = None
    poi_pharmacy_cnt: int | None = None
    poi_school_cnt: int | None = None
    dist_min_supermarket_m: float | None = None
    dist_min_pharmacy_m: float | None = None
    dist_min_school_m: float | None = None
    residential_allowed: bool = True
    commercial_allowed: bool = True
    residential_plan_status: str = "allowed"
    commercial_plan_status: str = "allowed"
    residential_plan_multiplier: float = 1.0
    commercial_plan_multiplier: float = 1.0
    legal_notes: str | None = None


@dataclass(frozen=True)
class ScoreResult:
    h3_id: str
    score_residencial: float
    score_comercial: float
    explain: dict[str, object] = field(default_factory=dict)


def urban_growth_signal(features: AreaFeatures) -> float:
    ndbi_growth = clamp((features.ndbi_slope_180 or 0.0) * 10.0, 0.0, 1.0)
    ndvi_loss = clamp(-(features.ndvi_slope_180 or 0.0) * 10.0, 0.0, 1.0)
    built_level = clamp((features.ndbi_mean_90 or 0.0) * 2.0, 0.0, 1.0)
    return (0.45 * ndbi_growth) + (0.35 * ndvi_loss) + (0.20 * built_level)


def score_area(features: AreaFeatures) -> ScoreResult:
    growth = urban_growth_signal(features)
    environmental_quality = clamp(((features.ndvi_mean_90 or 0.0) + 1.0) / 2.0)

    supermarket_gap = unmet_demand_score(features.poi_supermarket_cnt, target_count=2)
    pharmacy_gap = unmet_demand_score(features.poi_pharmacy_cnt, target_count=2)
    school_gap = unmet_demand_score(features.poi_school_cnt, target_count=1)
    commercial_gap = (0.45 * supermarket_gap) + (0.35 * pharmacy_gap) + (0.20 * school_gap)

    supermarket_access = inverse_distance_score(features.dist_min_supermarket_m, 2500.0)
    pharmacy_access = inverse_distance_score(features.dist_min_pharmacy_m, 1800.0)
    school_access = inverse_distance_score(features.dist_min_school_m, 2200.0)
    mixed_access = (supermarket_access + pharmacy_access + school_access) / 3.0

    raw_commercial = (0.45 * commercial_gap) + (0.35 * growth) + (0.20 * mixed_access)
    raw_residential = (0.40 * environmental_quality) + (0.35 * mixed_access) + (0.25 * growth)

    score_commercial = (
        0.0
        if not features.commercial_allowed
        else round(raw_commercial * features.commercial_plan_multiplier * 100, 2)
    )
    score_residential = (
        0.0
        if not features.residential_allowed
        else round(raw_residential * features.residential_plan_multiplier * 100, 2)
    )

    explain = {
        "growth_signal": round(growth, 4),
        "environmental_quality": round(environmental_quality, 4),
        "commercial_gap": round(commercial_gap, 4),
        "mixed_access": round(mixed_access, 4),
        "zoning": {
            "zona": features.zona,
            "residential_allowed": features.residential_allowed,
            "commercial_allowed": features.commercial_allowed,
            "residential_plan_status": features.residential_plan_status,
            "commercial_plan_status": features.commercial_plan_status,
            "legal_notes": features.legal_notes,
        },
        "main_recommendations": recommend_uses(
            supermarket_gap=supermarket_gap,
            pharmacy_gap=pharmacy_gap,
            school_gap=school_gap,
            commercial_allowed=features.commercial_allowed,
        ),
    }

    return ScoreResult(
        h3_id=features.h3_id,
        score_residencial=score_residential,
        score_comercial=score_commercial,
        explain=explain,
    )


def recommend_uses(
    supermarket_gap: float,
    pharmacy_gap: float,
    school_gap: float,
    commercial_allowed: bool,
) -> list[dict[str, str]]:
    if not commercial_allowed:
        return [{"use": "nenhum", "why": "O zoneamento informado veta ou nao permite uso comercial."}]

    candidates = [
        ("mercado", supermarket_gap, "baixa oferta de mercados/supermercados na celula ou entorno"),
        ("farmacia", pharmacy_gap, "baixa oferta de farmacias e servicos de conveniencia"),
        ("escola/creche", school_gap, "baixa oferta educacional proxima ao tecido residencial"),
    ]
    ranked = sorted(candidates, key=lambda item: item[1], reverse=True)
    return [
        {"use": use, "why": why}
        for use, gap, why in ranked
        if gap >= 0.35
    ][:3]
