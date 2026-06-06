from __future__ import annotations

import json

from .demo_data import sample_areas
from .scoring import score_area


def score_demo() -> None:
    results = [score_area(area) for area in sample_areas()]
    payload = [
        {
            "h3_id": result.h3_id,
            "score_residencial": result.score_residencial,
            "score_comercial": result.score_comercial,
            "explain": result.explain,
        }
        for result in results
    ]
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    score_demo()
