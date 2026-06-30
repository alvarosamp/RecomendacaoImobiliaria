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

    def test_explain_includes_confidence_and_factors(self):
        result = score_area(
            AreaFeatures(
                h3_id="explain",
                zona="ZMC",
                ndvi_mean_90=0.4,
                ndbi_mean_90=0.3,
                ndbi_slope_180=0.05,
                ndvi_slope_180=-0.02,
                poi_supermarket_cnt=0,
                poi_pharmacy_cnt=0,
                poi_school_cnt=0,
                dist_min_supermarket_m=500,
                dist_min_pharmacy_m=600,
                dist_min_school_m=700,
            )
        )

        self.assertIn("confidence", result.explain)
        self.assertIn("positive_factors", result.explain)
        self.assertIn("contributions", result.explain)
        self.assertGreater(result.explain["confidence"], 0)


if __name__ == "__main__":
    unittest.main()
