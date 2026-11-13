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
    # Tendencia tipica da cidade no mesmo periodo (mediana das celulas). Descontada
    # do slope da celula para nao confundir sazonalidade (seca/chuva) com urbanizacao.
    ndvi_slope_baseline: float = 0.0
    ndbi_slope_baseline: float = 0.0
    # False fora do perimetro com zoneamento: ali queda de NDVI/alta de NDBI costuma
    # ser colheita ou solo exposto, e a tendencia nao pode contar como urbanizacao.
    growth_trend_reliable: bool = True
    # Deteccao ano-contra-ano a 10 m (geo.urban_change_h3). Quando existe, substitui
    # os slopes: compara a mesma estacao e exige persistencia em duas cenas.
    change_fraction: float | None = None
    change_valid_fraction: float | None = None
    # Habitantes (Censo 2022) dentro do raio de contagem de estabelecimentos e a media da
    # cidade de estabelecimentos por habitante (supermarket/pharmacy/school). Quando
    # ausentes, a carencia usa as metas fixas por celula de ``demand_targets``.
    population_catchment: float | None = None
    service_rates: dict[str, float] | None = None
    poi_supermarket_cnt: int | None = None
    poi_pharmacy_cnt: int | None = None
    poi_school_cnt: int | None = None
    dist_min_supermarket_m: float | None = None
    dist_min_pharmacy_m: float | None = None
    dist_min_school_m: float | None = None
    # Faixa de minutos a pe (5/10/15, Mapbox Isochrone) ate o estabelecimento mais
    # proximo em linha reta; None = sem POI da categoria ou fora de 15 min.
    # Informativo: nao entra em nenhuma formula de score_area nem na calibracao.
    travel_min_supermarket: int | None = None
    travel_min_pharmacy: int | None = None
    travel_min_school: int | None = None
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
    # True apenas quando a zona veio de uma camada oficial registrada (nao do exemplo).
    zoning_official: bool = False


@dataclass(frozen=True)
class ScoreResult:
    h3_id: str
    score_residencial: float
    score_comercial: float
    explain: dict[str, object] = field(default_factory=dict)


def urban_growth_signal(features: AreaFeatures, config: ScoringConfig | None = None) -> float:
    """Sinal 0-1 de urbanizacao recente.

    Os slopes chegam em unidades de indice por dia. Cada um e comparado com a
    tendencia da cidade e normalizado pela variacao em 180 dias configurada como
    sinal maximo; sem isso a queda sazonal de NDVI apareceria como crescimento.
    """
    built_only = 0.20 * clamp((features.ndbi_mean_90 or 0.0) * 2.0, 0.0, 1.0)
    if not features.growth_trend_reliable:
        return built_only
    if has_change_detection(features, config):
        full = max(config.growth_change_fraction_full if config else 0.15, 1e-6)
        return 0.80 * clamp(features.change_fraction / full) + built_only
    change_180d = config.growth_index_change_180d if config else 0.10
    scale = max(change_180d, 1e-6) / 180.0
    ndbi_growth = 0.0
    if features.ndbi_slope_180 is not None:
        ndbi_growth = clamp((features.ndbi_slope_180 - features.ndbi_slope_baseline) / scale)
    ndvi_loss = 0.0
    if features.ndvi_slope_180 is not None:
        ndvi_loss = clamp(-(features.ndvi_slope_180 - features.ndvi_slope_baseline) / scale)
    built_level = clamp((features.ndbi_mean_90 or 0.0) * 2.0, 0.0, 1.0)
    return (0.45 * ndbi_growth) + (0.35 * ndvi_loss) + (0.20 * built_level)


def has_change_detection(features: AreaFeatures, config: ScoringConfig | None = None) -> bool:
    """True quando a celula tem deteccao ano-contra-ano com area observada suficiente."""
    minimum = config.growth_change_min_valid_fraction if config else 0.5
    return (
        features.change_fraction is not None
        and features.change_valid_fraction is not None
        and features.change_valid_fraction >= minimum
    )


def has_population_demand(features: AreaFeatures) -> bool:
    return features.population_catchment is not None and bool(features.service_rates)


def demand_gaps(features: AreaFeatures, config: ScoringConfig) -> tuple[dict[str, float], dict[str, object]]:
    """Carencia (0-1) de mercado, farmacia e escola, e a memoria de calculo.

    Com populacao: esperado = habitantes do entorno x estabelecimentos por habitante da
    cidade; carencia = estabelecimentos que faltam (esperado - mapeados), saturando em
    ``unmet_full_establishments``. Uma celula sem gente nao tem demanda, nem ausencia de
    estabelecimentos a explica. Sem populacao: metas fixas por celula (comportamento antigo).
    """
    counts = {
        "supermarket": features.poi_supermarket_cnt,
        "pharmacy": features.poi_pharmacy_cnt,
        "school": features.poi_school_cnt,
    }
    if not has_population_demand(features):
        gaps = {key: unmet_demand_score(counts[key], config.demand_targets[key]) for key in counts}
        return gaps, {"basis": "metas_fixas_por_celula"}
    full = max(config.unmet_full_establishments, 1e-6)
    expected = {key: features.population_catchment * features.service_rates.get(key, 0.0) for key in counts}
    unmet = {key: max(expected[key] - (counts[key] or 0), 0.0) for key in counts}
    gaps = {key: clamp(unmet[key] / full) for key in counts}
    return gaps, {
        "basis": "populacao_do_entorno",
        "population_catchment": round(features.population_catchment),
        "expected_establishments": {key: round(value, 2) for key, value in expected.items()},
        "unmet_establishments": {key: round(value, 2) for key, value in unmet.items()},
    }


def travel_time_summary(features: AreaFeatures) -> dict[str, object]:
    """Resumo informativo do tempo real de deslocamento (Mapbox Isochrone).

    Nao influencia `score_area`: o score calibrado continua usando
    `dist_min_*_m` (linha reta) em `inverse_distance_score`. Serve para
    comparar, por celula, a diferenca entre a reta e o percurso real a pe.
    """
    minutes = {
        "supermarket": features.travel_min_supermarket,
        "pharmacy": features.travel_min_pharmacy,
        "school": features.travel_min_school,
    }
    return {
        "source": "mapbox_isochrone_walking",
        "used_in_score": False,
        "bands_minutes": minutes,
        "available": any(value is not None for value in minutes.values()),
    }


def score_area(features: AreaFeatures, config: ScoringConfig | None = None) -> ScoreResult:
    config = config or load_scoring_config()
    growth = urban_growth_signal(features, config)
    environmental_quality = clamp(((features.ndvi_mean_90 or 0.0) + 1.0) / 2.0)

    gaps, demand = demand_gaps(features, config)
    supermarket_gap, pharmacy_gap, school_gap = gaps["supermarket"], gaps["pharmacy"], gaps["school"]
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
        "growth_source": (
            "fora_do_perimetro_zoneado" if not features.growth_trend_reliable
            else "deteccao_anual_10m" if has_change_detection(features, config)
            else "tendencia_indices"
        ),
        "change_fraction": features.change_fraction,
        "environmental_quality": round(environmental_quality, 4),
        "commercial_gap": round(commercial_gap, 4),
        "demand": demand,
        "mixed_access": round(mixed_access, 4),
        "travel_time_access": travel_time_summary(features),
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
            "validation_status": (
                "pending_zoning" if not features.zona
                else "validated_official" if features.zoning_official
                else "unverified_zoning"
            ),
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
    """Confianca proporcional a quanto de cada camada realmente sustenta o score."""
    weights = config.confidence_weights
    value = weights["base"]

    # Satelite: nivel (medias) e tendencia (slopes) contam metade cada.
    has_level = features.ndvi_mean_90 is not None or features.ndbi_mean_90 is not None
    has_trend = features.growth_trend_reliable and (
        has_change_detection(features, config)
        or features.ndvi_slope_180 is not None
        or features.ndbi_slope_180 is not None
    )
    value += weights["has_remote_sensing"] * (0.5 * has_level + 0.5 * has_trend)

    distances = [
        features.dist_min_supermarket_m,
        features.dist_min_pharmacy_m,
        features.dist_min_school_m,
    ]
    value += weights["has_accessibility"] * sum(item is not None for item in distances) / len(distances)

    if has_population_demand(features):
        value += weights.get("has_population", 0.0)

    # Zona de camada nao oficial (exemplo) vale metade e nao recebe o bonus do plano.
    if features.zona:
        value += weights["has_zoning"] * (1.0 if features.zoning_official else 0.5)
    if (
        features.zona
        and features.zoning_official
        and features.residential_plan_status != "blocked"
        and features.commercial_plan_status != "blocked"
    ):
        value += weights["allowed_by_plan"]
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
