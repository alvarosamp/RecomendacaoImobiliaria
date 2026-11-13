import unittest


class SidraParsingTest(unittest.TestCase):
    """
    Tests for the SIDRA API response parsing in ibge_collector.
    No HTTP calls — pure parsing logic.
    """

    def test_municipality_population_fallback(self):
        from unittest.mock import patch
        from recomendacao_imobiliaria.ibge_collector import _get_municipality_population

        # Simulate API failure → should return hardcoded Pouso Alegre value
        with patch("recomendacao_imobiliaria.ibge_collector.requests.get", side_effect=Exception("timeout")):
            pop = _get_municipality_population()
        self.assertGreater(pop, 100_000)

    def test_population_fallback_parse_api(self):
        from unittest.mock import patch, MagicMock

        fake_response = [
            {
                "series": [
                    {"serie": {"2022": "163.567", "2023": "165.000"}}
                ]
            }
        ]

        mock_resp = MagicMock()
        mock_resp.raise_for_status = lambda: None
        mock_resp.json.return_value = fake_response

        with patch("recomendacao_imobiliaria.ibge_collector.requests.get", return_value=mock_resp):
            from recomendacao_imobiliaria.ibge_collector import _get_municipality_population
            pop = _get_municipality_population()

        self.assertEqual(pop, 165_000)

    def test_population_parses_indicator_api_format(self):
        from unittest.mock import patch, MagicMock

        # Formato real de /pesquisas/indicadores/29171/resultados/{codigo}
        fake_response = [{"id": 29171, "res": [{"localidade": "315250", "res": {"2025": "162133", "2026": "163439", "2023": "-"}}]}]
        mock_resp = MagicMock()
        mock_resp.raise_for_status = lambda: None
        mock_resp.json.return_value = fake_response

        with patch("recomendacao_imobiliaria.ibge_collector.requests.get", return_value=mock_resp):
            from recomendacao_imobiliaria.ibge_collector import _get_municipality_population
            pop = _get_municipality_population()

        self.assertEqual(pop, 163_439)

    def test_city_code_is_pouso_alegre(self):
        from recomendacao_imobiliaria import ibge_collector

        self.assertEqual(ibge_collector.IBGE_CITY_CODE, 3152501)
        self.assertEqual(ibge_collector._POUSO_ALEGRE_POP_2022, 152_217)


class CnesTypeMapTest(unittest.TestCase):
    def test_farmacia_maps_to_pharmacy(self):
        from recomendacao_imobiliaria.cnes_collector import _CNES_TIPO_MAP
        self.assertEqual(_CNES_TIPO_MAP["FARMACIA"], "pharmacy")

    def test_uba_maps_to_clinic(self):
        from recomendacao_imobiliaria.cnes_collector import _CNES_TIPO_MAP
        self.assertEqual(_CNES_TIPO_MAP["UBS"], "clinic")

    def test_hospital_maps_to_hospital(self):
        from recomendacao_imobiliaria.cnes_collector import _CNES_TIPO_MAP
        self.assertEqual(_CNES_TIPO_MAP["HOSPITAL"], "hospital")


if __name__ == "__main__":
    unittest.main()
