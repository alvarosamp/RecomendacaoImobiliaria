import unittest
from recomendacao_imobiliaria.official_sources import (
    official_sources_as_dicts,
    validate_official_data,
)


class OfficialSourcesTest(unittest.TestCase):
    def test_sources_include_prefeitura_and_legislation(self):
        sources = official_sources_as_dicts()
        names = " ".join(source["name"] for source in sources)

        self.assertIn("Prefeitura", names)
        self.assertIn("Camara", names)

    def test_validate_official_data_reports_missing_files(self):
        result = validate_official_data("data/official_empty_test")

        self.assertIn("data", result.base_dir)
        self.assertIn("zoneamento_oficial.geojson", result.missing_recommended)


if __name__ == "__main__":
    unittest.main()
