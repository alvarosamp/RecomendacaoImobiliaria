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
        self.assertEqual(normalize_zone("Zona Mista Central"), "ZC")
        self.assertEqual(normalize_zone("ZMC"), "ZC")
        self.assertEqual(normalize_zone("ZEPAM 1"), "ZEPAM1")

    def test_all_official_kml_zones_have_structured_rules(self):
        from recomendacao_imobiliaria.plan_director import load_plan_rules
        from recomendacao_imobiliaria.zoning_import import inspect_zoning_file

        rules = load_plan_rules()["rules"]
        inspection = inspect_zoning_file("data/official/pdpa/zoneamento_pdpa.kml")
        official_zones = {item["zona"] for item in inspection.zones}

        self.assertEqual(len(official_zones), 22)
        self.assertEqual(official_zones - set(rules), set())

    def test_special_environmental_and_project_zones_fail_closed(self):
        for zone in ("ZEPAM1", "ZEPAM2", "ZEPAM3", "ZEPAM4", "ZEPU1", "ZEPU2", "ZEPU3"):
            with self.subTest(zone=zone):
                self.assertEqual(evaluate_plan_compatibility(zone, "residencial").status, "blocked")

    def test_macroarea_dependent_parameters_are_ranges(self):
        decision = evaluate_plan_compatibility("ZMV", "residencial")
        self.assertTrue(decision.parameters["requires_macroarea_check"])
        self.assertEqual(decision.parameters["ca_maximo_range"], [3.0, 6.0])


if __name__ == "__main__":
    unittest.main()
