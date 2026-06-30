import unittest

from recomendacao_imobiliaria.scoring_config import load_scoring_config


class ScoringConfigTest(unittest.TestCase):
    def test_load_scoring_config(self):
        config = load_scoring_config()

        self.assertIn("growth", config.commercial_weights)
        self.assertEqual(config.demand_targets["school"], 1)
        self.assertGreater(config.recommendation_threshold, 0)


if __name__ == "__main__":
    unittest.main()
