import unittest

from recomendacao_imobiliaria.legal_annexes import inspect_legal_annexes


class LegalAnnexesTest(unittest.TestCase):
    def test_required_annexes_are_registered(self):
        statuses = inspect_legal_annexes()
        keys = {status.key for status in statuses}

        self.assertIn("occupation_parameters", keys)
        self.assertIn("non_residential_uses_mdu", keys)
        self.assertIn("installation_conditions", keys)


if __name__ == "__main__":
    unittest.main()
