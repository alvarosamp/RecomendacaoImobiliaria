import unittest

try:
    import pandas as pd

    from recomendacao_imobiliaria.decision import enrich_opportunities
except ModuleNotFoundError:
    pd = None
    enrich_opportunities = None


@unittest.skipIf(pd is None, "pandas nao instalado")
class DecisionTest(unittest.TestCase):
    def test_enrich_opportunities_adds_priority_and_summary(self):
        frame = pd.DataFrame(
            [
                {
                    "h3_id": "a",
                    "score_residencial": 80,
                    "score_comercial": 55,
                    "ndvi_slope_180": -0.002,
                    "ndbi_slope_180": 0.002,
                    "explain_json": {"main_recommendations": [{"use": "mercado", "why": "carencia"}]},
                }
            ]
        )

        result = enrich_opportunities(frame)

        self.assertEqual(result.loc[0, "priority"], "alta")
        self.assertEqual(result.loc[0, "primary_use"], "residencial")
        self.assertIn("mercado", result.loc[0, "summary"])


if __name__ == "__main__":
    unittest.main()
