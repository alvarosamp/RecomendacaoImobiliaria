import unittest


class SidraParsingTest(unittest.TestCase):
    """
    Tests for the SIDRA API response parsing in ibge_collector.
    No HTTP calls — pure parsing logic.
    """

    def test_setor_population_parsing_valid_response(self):
        from unittest.mock import patch, MagicMock

        fake_response = [
            {"D1C": "header", "V": "Total"},  # cabeçalho
            {"D1C": "315180005000001", "V": "456"},
            {"D1C": "315180005000002", "V": "789"},
            {"D1C": "315180005000003", "V": "não informado"},  # invalid value
        ]

        mock_resp = MagicMock()
        mock_resp.raise_for_status = lambda: None
        mock_resp.json.return_value = fake_response

        with patch("recomendacao_imobiliaria.ibge_collector.requests.get", return_value=mock_resp):
            from recomendacao_imobiliaria.ibge_collector import _fetch_setor_population
            result = _fetch_setor_population()

        # header row and invalid value must be ignored
        self.assertEqual(result.get("315180005000001"), 456)
        self.assertEqual(result.get("315180005000002"), 789)
        self.assertNotIn("315180005000003", result)

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
