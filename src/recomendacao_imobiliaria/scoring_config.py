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
    )
