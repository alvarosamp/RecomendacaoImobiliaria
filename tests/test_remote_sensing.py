import unittest

try:
    import pandas as pd

    from recomendacao_imobiliaria.remote_sensing import compute_index_features
except ModuleNotFoundError:
    pd = None
    compute_index_features = None


@unittest.skipIf(pd is None, "pandas/numpy nao instalados")
class RemoteSensingTest(unittest.TestCase):
    def test_compute_index_features_detects_growth_signal(self):
        frame = pd.DataFrame(
            [
                {"h3_id": "a", "date": "2025-01-01", "ndvi": 0.50, "ndbi": 0.10},
                {"h3_id": "a", "date": "2025-03-01", "ndvi": 0.42, "ndbi": 0.18},
                {"h3_id": "a", "date": "2025-06-01", "ndvi": 0.35, "ndbi": 0.28},
            ]
        )

        result = compute_index_features(frame, reference_date="2025-06-01")
        row = result.iloc[0]

        self.assertLess(row["ndvi_slope_180"], 0)
        self.assertGreater(row["ndbi_slope_180"], 0)
        self.assertAlmostEqual(row["ndvi_mean_90"], 0.35)


if __name__ == "__main__":
    unittest.main()
