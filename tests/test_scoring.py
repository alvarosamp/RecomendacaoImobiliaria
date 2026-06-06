import unittest

from recomendacao_imobiliaria.scoring import AreaFeatures, score_area


class ScoringTest(unittest.TestCase):
    def test_zoning_blocks_scores_when_use_is_not_allowed(self):
        result = score_area(
            AreaFeatures(
                h3_id="blocked",
                residential_allowed=False,
                commercial_allowed=False,
                poi_supermarket_cnt=0,
                poi_pharmacy_cnt=0,
                poi_school_cnt=0,
            )
        )

        self.assertEqual(result.score_residencial, 0.0)
        self.assertEqual(result.score_comercial, 0.0)
        self.assertEqual(result.explain["main_recommendations"][0]["use"], "nenhum")

    def test_commercial_gap_generates_recommendation(self):
        result = score_area(
            AreaFeatures(
                h3_id="gap",
                poi_supermarket_cnt=0,
                poi_pharmacy_cnt=2,
                poi_school_cnt=1,
                commercial_allowed=True,
            )
        )

        uses = [item["use"] for item in result.explain["main_recommendations"]]
        self.assertIn("mercado", uses)


if __name__ == "__main__":
    unittest.main()
