import unittest

from recomendacao_imobiliaria.legal_audit import build_legal_audit


class LegalAuditTest(unittest.TestCase):
    def test_environmental_zone_is_blocked_with_citation(self):
        audit = build_legal_audit("ZPA", "comercial")

        self.assertEqual(audit.status, "blocked")
        self.assertIn("Art. 30", audit.articles)
        self.assertTrue(audit.sources)

    def test_blocking_spatial_overlay_overrides_zone(self):
        audit = build_legal_audit(
            "ZM",
            "residencial",
            overlays=[{"tipo": "area_de_risco", "status": "blocked"}],
            spatial_overlays_verified=True,
        )

        self.assertEqual(audit.status, "blocked")
        self.assertTrue(audit.spatial_overlays_verified)

    def test_missing_overlay_layer_is_disclosed(self):
        audit = build_legal_audit("ZM", "comercial")
        self.assertFalse(audit.spatial_overlays_verified)
