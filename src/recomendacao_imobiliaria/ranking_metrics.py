"""Metricas reproduziveis para avaliar rankings de recomendacao offline."""
from __future__ import annotations

from dataclasses import dataclass
from math import log2
from typing import Iterable


@dataclass(frozen=True)
class RankingMetrics:
    precision_at_k: float
    recall_at_k: float
    ndcg_at_k: float
    hit_rate_at_k: float
    catalog_coverage: float


def evaluate_rankings(
    recommendations: Iterable[Iterable[str]],
    relevant_items: Iterable[Iterable[str]],
    *,
    k: int,
    catalog: Iterable[str] | None = None,
) -> RankingMetrics:
    """Calcula metricas top-K para listas alinhadas de usuarios/cenarios.

    ``recommendations`` e ``relevant_items`` precisam ter o mesmo numero de
    listas. Itens repetidos em uma recomendacao contam somente uma vez.
    """
    if k <= 0:
        raise ValueError("k deve ser maior que zero")

    recommendation_lists = [list(items)[:k] for items in recommendations]
    relevant_lists = [set(items) for items in relevant_items]
    if len(recommendation_lists) != len(relevant_lists):
        raise ValueError("recommendations e relevant_items devem ter o mesmo tamanho")
    if not recommendation_lists:
        return RankingMetrics(0.0, 0.0, 0.0, 0.0, 0.0)

    precisions: list[float] = []
    recalls: list[float] = []
    ndcgs: list[float] = []
    hits: list[float] = []
    recommended_catalog: set[str] = set()

    for ranking, relevant in zip(recommendation_lists, relevant_lists):
        unique_ranking = list(dict.fromkeys(ranking))
        recommended_catalog.update(unique_ranking)
        matched = [item for item in unique_ranking if item in relevant]
        precisions.append(len(matched) / k)
        recalls.append(len(matched) / len(relevant) if relevant else 0.0)
        hits.append(1.0 if matched else 0.0)

        dcg = sum(1.0 / log2(position + 2) for position, item in enumerate(unique_ranking) if item in relevant)
        ideal_count = min(len(relevant), k)
        idcg = sum(1.0 / log2(position + 2) for position in range(ideal_count))
        ndcgs.append(dcg / idcg if idcg else 0.0)

    known_catalog = set(catalog) if catalog is not None else recommended_catalog
    coverage = len(recommended_catalog & known_catalog) / len(known_catalog) if known_catalog else 0.0
    return RankingMetrics(
        precision_at_k=sum(precisions) / len(precisions),
        recall_at_k=sum(recalls) / len(recalls),
        ndcg_at_k=sum(ndcgs) / len(ndcgs),
        hit_rate_at_k=sum(hits) / len(hits),
        catalog_coverage=coverage,
    )
