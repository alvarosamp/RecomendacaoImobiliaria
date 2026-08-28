import unittest

from recomendacao_imobiliaria.risk_susceptibility import assess_susceptibility


class RiskSusceptibilityTest(unittest.TestCase):
    def test_full_evidence_can_raise_high_alert(self):
        result = assess_susceptibility(
            slope_pct=24, drainage_distance_m=20, water_observation_rate=0.9,
            ndvi_slope_180=-0.003, ndbi_slope_180=0.003,
        )
        self.assertEqual(result.alert_level, "alto")
        self.assertGreaterEqual(result.confidence, 0.9)

    def test_satellite_only_is_observation_not_confirmed_risk(self):
        result = assess_susceptibility(ndvi_slope_180=-0.003, ndbi_slope_180=0.003)
        self.assertEqual(result.alert_level, "em_observacao")
        self.assertLess(result.confidence, 0.45)

    def test_no_evidence_is_disclosed(self):
        result = assess_susceptibility()
        self.assertEqual(result.alert_level, "dados_insuficientes")
