import unittest

from recomendacao_imobiliaria.zoning_import import inspect_zoning_file


class ZoningImportTest(unittest.TestCase):
    def test_inspect_kml_reads_layer_zones(self):
        result = inspect_zoning_file("tests/fixtures/sample_zoning.kml")
        zones = {item["zona"] for item in result.zones}

        self.assertEqual(result.feature_count, 2)
        self.assertTrue(result.has_geometry)
        self.assertIn("ZEU", zones)
        self.assertIn("ZEPAM1", zones)


if __name__ == "__main__":
    unittest.main()
