import unittest

from recomendacao_imobiliaria.plan_director import evaluate_plan_compatibility, normalize_zone


class PlanDirectorTest(unittest.TestCase):
    def test_environmental_zone_blocks_commercial_use(self):
        decision = evaluate_plan_compatibility("ZPA", "comercial")

        self.assertEqual(decision.status, "blocked")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.multiplier, 0.0)

    def test_expansion_zone_is_conditioned(self):
        decision = evaluate_plan_compatibility("Zona de Expansao Urbana", "residencial")

        self.assertEqual(decision.status, "conditioned")
        self.assertTrue(decision.allowed)

    def test_normalize_zone_alias(self):
        self.assertEqual(normalize_zone("Zona Mista Central"), "ZMC")


if __name__ == "__main__":
    unittest.main()
