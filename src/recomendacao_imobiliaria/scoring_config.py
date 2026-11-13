from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


DEFAULT_SCORING_CONFIG = Path("config/scoring_weights.json")


@dataclass(frozen=True)
class ScoringConfig:
    commercial_weights: dict[str, float]
    residential_weights: dict[str, float]
    demand_targets: dict[str, int]
    access_targets_m: dict[str, float]
    recommendation_threshold: float
    confidence_weights: dict[str, float]
    # Variacao do indice (NDBI/NDVI) em 180 dias, alem da tendencia da cidade,
    # que equivale ao sinal maximo de crescimento.
    growth_index_change_180d: float = 0.10
    # Fracao da celula com mudanca detectada ano-contra-ano (Sentinel-2, 10 m, nivel
    # "provavel") que equivale ao sinal maximo de crescimento. Alta porque o nivel
    # provavel marca cerca de 2 a 3 vezes mais area do que a referencia confirma.
    growth_change_fraction_full: float = 0.15
    # Minimo de area observada sem nuvem para a deteccao valer na celula.
    growth_change_min_valid_fraction: float = 0.5
    # Raio (m) da contagem de estabelecimentos no entorno da celula.
    poi_count_radius_m: float = 1000.0
    # Estabelecimentos faltando (esperado pela populacao do entorno menos os mapeados)
    # que equivalem a carencia maxima (1,0).
    unmet_full_establishments: float = 1.0


def load_scoring_config(path: str | Path = DEFAULT_SCORING_CONFIG) -> ScoringConfig:
    with Path(path).open("r", encoding="utf-8") as file:
        raw = json.load(file)

    return ScoringConfig(
        commercial_weights={key: float(value) for key, value in raw["commercial"].items()},
        residential_weights={key: float(value) for key, value in raw["residential"].items()},
        demand_targets={key: int(value) for key, value in raw["demand_targets"].items()},
        access_targets_m={key: float(value) for key, value in raw["access_targets_m"].items()},
        recommendation_threshold=float(raw.get("recommendation_threshold", 0.35)),
        confidence_weights={key: float(value) for key, value in raw["confidence"].items()},
        growth_index_change_180d=float(raw.get("growth_index_change_180d", 0.10)),
        growth_change_fraction_full=float(raw.get("growth_change_fraction_full", 0.15)),
        growth_change_min_valid_fraction=float(raw.get("growth_change_min_valid_fraction", 0.5)),
        poi_count_radius_m=float(raw.get("poi_count_radius_m", 1000.0)),
        unmet_full_establishments=float(raw.get("unmet_full_establishments", 1.0)),
    )
