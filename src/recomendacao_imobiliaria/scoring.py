from __future__ import annotations

from dataclasses import dataclass, field

from .scoring_config import ScoringConfig, load_scoring_config


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
    legal_articles: tuple[str, ...] = ()
    legal_parameters: dict[str, object] = field(default_factory=dict)
    legal_sources: tuple[dict[str, str], ...] = ()


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


def score_area(features: AreaFeatures, config: ScoringConfig | None = None) -> ScoreResult:
    config = config or load_scoring_config()
    growth = urban_growth_signal(features)
    environmental_quality = clamp(((features.ndvi_mean_90 or 0.0) + 1.0) / 2.0)

    supermarket_gap = unmet_demand_score(features.poi_supermarket_cnt, config.demand_targets["supermarket"])
    pharmacy_gap = unmet_demand_score(features.poi_pharmacy_cnt, config.demand_targets["pharmacy"])
    school_gap = unmet_demand_score(features.poi_school_cnt, config.demand_targets["school"])
    commercial_gap = (0.45 * supermarket_gap) + (0.35 * pharmacy_gap) + (0.20 * school_gap)

    supermarket_access = inverse_distance_score(features.dist_min_supermarket_m, config.access_targets_m["supermarket"])
    pharmacy_access = inverse_distance_score(features.dist_min_pharmacy_m, config.access_targets_m["pharmacy"])
    school_access = inverse_distance_score(features.dist_min_school_m, config.access_targets_m["school"])
    mixed_access = (supermarket_access + pharmacy_access + school_access) / 3.0

    raw_commercial = (
        (config.commercial_weights["commercial_gap"] * commercial_gap)
        + (config.commercial_weights["growth"] * growth)
        + (config.commercial_weights["mixed_access"] * mixed_access)
    )
    raw_residential = (
        (config.residential_weights["environmental_quality"] * environmental_quality)
        + (config.residential_weights["mixed_access"] * mixed_access)
        + (config.residential_weights["growth"] * growth)
    )

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
        "confidence": round(_confidence(features, config), 4),
        "contributions": {
            "commercial": {
                "commercial_gap": round(config.commercial_weights["commercial_gap"] * commercial_gap, 4),
                "growth": round(config.commercial_weights["growth"] * growth, 4),
                "mixed_access": round(config.commercial_weights["mixed_access"] * mixed_access, 4),
                "plan_multiplier": features.commercial_plan_multiplier,
            },
            "residential": {
                "environmental_quality": round(
                    config.residential_weights["environmental_quality"] * environmental_quality,
                    4,
                ),
                "mixed_access": round(config.residential_weights["mixed_access"] * mixed_access, 4),
                "growth": round(config.residential_weights["growth"] * growth, 4),
                "plan_multiplier": features.residential_plan_multiplier,
            },
        },
        "positive_factors": _positive_factors(
            growth=growth,
            environmental_quality=environmental_quality,
            commercial_gap=commercial_gap,
            mixed_access=mixed_access,
        ),
        "negative_factors": _negative_factors(
            features=features,
            growth=growth,
            commercial_gap=commercial_gap,
            mixed_access=mixed_access,
        ),
        "zoning": {
            "zona": features.zona,
            "residential_allowed": features.residential_allowed,
            "commercial_allowed": features.commercial_allowed,
            "residential_plan_status": features.residential_plan_status,
            "commercial_plan_status": features.commercial_plan_status,
            "legal_notes": features.legal_notes,
            "legal_articles": list(features.legal_articles),
            "legal_parameters": features.legal_parameters,
            "legal_sources": list(features.legal_sources),
        },
        "main_recommendations": recommend_uses(
            supermarket_gap=supermarket_gap,
            pharmacy_gap=pharmacy_gap,
            school_gap=school_gap,
            commercial_allowed=features.commercial_allowed,
            threshold=config.recommendation_threshold,
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
    threshold: float = 0.35,
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
        if gap >= threshold
    ][:3]


def _confidence(features: AreaFeatures, config: ScoringConfig) -> float:
    value = config.confidence_weights["base"]
    if features.ndvi_mean_90 is not None or features.ndbi_mean_90 is not None:
        value += config.confidence_weights["has_remote_sensing"]
    if any(
        item is not None
        for item in [
            features.dist_min_supermarket_m,
            features.dist_min_pharmacy_m,
            features.dist_min_school_m,
        ]
    ):
        value += config.confidence_weights["has_accessibility"]
    if features.zona:
        value += config.confidence_weights["has_zoning"]
    if features.residential_plan_status != "blocked" and features.commercial_plan_status != "blocked":
        value += config.confidence_weights["allowed_by_plan"]
    return clamp(value)


def _positive_factors(
    growth: float,
    environmental_quality: float,
    commercial_gap: float,
    mixed_access: float,
) -> list[str]:
    factors = []
    if growth >= 0.35:
        factors.append("sinal de crescimento urbano")
    if environmental_quality >= 0.65:
        factors.append("boa qualidade ambiental relativa")
    if commercial_gap >= 0.45:
        factors.append("carencia relevante de servicos")
    if mixed_access >= 0.45:
        factors.append("boa acessibilidade a equipamentos")
    return factors


def _negative_factors(
    features: AreaFeatures,
    growth: float,
    commercial_gap: float,
    mixed_access: float,
) -> list[str]:
    factors = []
    if growth < 0.15:
        factors.append("baixo sinal de crescimento recente")
    if commercial_gap < 0.2:
        factors.append("baixa carencia comercial detectada")
    if mixed_access < 0.2:
        factors.append("acessibilidade limitada aos servicos medidos")
    if features.residential_plan_status == "conditioned" or features.commercial_plan_status == "conditioned":
        factors.append("uso condicionado pelo Plano Diretor")
    if not features.residential_allowed or not features.commercial_allowed:
        factors.append("uso bloqueado ou vetado pela regra legal/zoneamento")
    return factors
