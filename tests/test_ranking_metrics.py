import unittest

from recomendacao_imobiliaria.ranking_metrics import evaluate_rankings


class RankingMetricsTest(unittest.TestCase):
    def test_evaluates_top_k_and_catalog_coverage(self):
        result = evaluate_rankings(
            recommendations=[["a", "b", "c"], ["c", "d", "a"]],
            relevant_items=[["a", "z"], ["d"]],
            k=2,
            catalog=["a", "b", "c", "d", "z"],
        )

        self.assertEqual(result.precision_at_k, 0.5)
        self.assertEqual(result.recall_at_k, 0.75)
        self.assertEqual(result.hit_rate_at_k, 1.0)
        self.assertAlmostEqual(result.catalog_coverage, 0.8)
        self.assertGreater(result.ndcg_at_k, 0)

    def test_rejects_invalid_k_or_unaligned_lists(self):
        with self.assertRaises(ValueError):
            evaluate_rankings([], [], k=0)
        with self.assertRaises(ValueError):
            evaluate_rankings([["a"]], [], k=1)
