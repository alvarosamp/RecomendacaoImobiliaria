import math
import unittest

try:
    import pandas as pd
    import numpy as np
except ModuleNotFoundError:
    pd = None
    np = None


@unittest.skipIf(pd is None, "pandas nao instalado")
class TypologyTest(unittest.TestCase):
    def _make_df(self):
        rows = []
        for i in range(20):
            rows.append({
                "h3_id": f"cell_{i:03d}",
                "ndbi_mean_90": 0.05 + i * 0.03,
                "ndvi_mean_90": 0.60 - i * 0.02,
                "ndvi_slope_180": -0.001 * i,
                "poi_supermarket_cnt": i % 4,
                "poi_pharmacy_cnt": (i + 1) % 3,
                "poi_school_cnt": i % 2,
                "poi_hospital_cnt": i % 5,
                "poi_leisure_cnt": 3 - i % 4,
                "dist_min_supermarket_m": 500 + i * 100,
                "dist_min_pharmacy_m": 300 + i * 150,
                "dist_min_hospital_m": 1000 + i * 200,
            })
        return pd.DataFrame(rows)

    def test_compute_typology_returns_one_label_per_cell(self):
        from api.routes.analytics import _compute_typology
        df = self._make_df()
        result = _compute_typology(df)
        self.assertEqual(len(result), len(df))

    def test_typology_labels_are_known_values(self):
        from api.routes.analytics import _compute_typology, TYPOLOGY_NAMES
        df = self._make_df()
        result = _compute_typology(df)
        for cell, label in result.items():
            self.assertIn(label, TYPOLOGY_NAMES)

    def test_empty_df_returns_empty_dict(self):
        from api.routes.analytics import _compute_typology
        empty = pd.DataFrame(columns=["h3_id", "ndbi_mean_90", "ndvi_mean_90"])
        self.assertEqual(_compute_typology(empty), {})


class GrowthLabelTest(unittest.TestCase):
    def test_rapid_growth(self):
        from api.routes.analytics import _growth_label
        self.assertIn("acelerada", _growth_label(0.003))

    def test_moderate_growth(self):
        from api.routes.analytics import _growth_label
        self.assertIn("moderado", _growth_label(0.001))

    def test_stable(self):
        from api.routes.analytics import _growth_label
        self.assertIn("estável", _growth_label(0.0))

    def test_decline(self):
        from api.routes.analytics import _growth_label
        self.assertIn("perda", _growth_label(-0.002))

    def test_none_returns_string(self):
        from api.routes.analytics import _growth_label
        label = _growth_label(None)
        self.assertIsInstance(label, str)


@unittest.skipIf(pd is None, "pandas nao instalado")
class BuildReasonsTest(unittest.TestCase):
    def _cfg(self):
        return {
            "label": "Farmácia / Drogaria",
            "col_dist": "dist_min_pharmacy_m",
            "col_cnt": "poi_pharmacy_cnt",
            "zoning": "ZMU, ZC",
        }

    def test_population_appears_in_reasons_when_present(self):
        from api.routes.analytics import _build_reasons
        row = {
            "dist_min_pharmacy_m": 2500.0,
            "ndbi_slope_180": 0.002,
            "zona": "ZMU",
            "pop_estimated": 1250,
            "score_residencial": 75.0,
        }
        reasons = _build_reasons(row, self._cfg(), "Residencial consolidado")
        self.assertTrue(any("1.250" in r or "1,250" in r for r in reasons))

    def test_distance_appears_in_reasons(self):
        from api.routes.analytics import _build_reasons
        row = {
            "dist_min_pharmacy_m": 3200.0,
            "ndbi_slope_180": 0.001,
            "zona": "ZC",
            "pop_estimated": None,
            "score_residencial": None,
        }
        reasons = _build_reasons(row, self._cfg(), "Em expansão")
        self.assertTrue(any("km" in r for r in reasons))


if __name__ == "__main__":
    unittest.main()
