import unittest


class NormalizePOITest(unittest.TestCase):
    """Tests for _normalize_poi — no DB dependency."""

    def _make_row(self, **kwargs):
        class Row(dict):
            def get(self, key, default=None):
                return super().get(key, default)
        return Row(kwargs)

    def _norm(self, **kwargs):
        from recomendacao_imobiliaria.geospatial import _normalize_poi
        return _normalize_poi(self._make_row(**kwargs))

    # existing categories
    def test_supermarket_shop(self):
        self.assertEqual(self._norm(shop="supermarket"), ("shop", "supermarket"))

    def test_pharmacy_amenity(self):
        self.assertEqual(self._norm(amenity="pharmacy"), ("amenity", "pharmacy"))

    def test_pharmacy_shop_normalised_to_amenity(self):
        cat, sub = self._norm(shop="pharmacy")
        self.assertEqual(sub, "pharmacy")

    def test_school_amenity(self):
        self.assertEqual(self._norm(amenity="school"), ("amenity", "school"))

    # new leisure categories
    def test_park_leisure(self):
        self.assertEqual(self._norm(leisure="park"), ("leisure", "park"))

    def test_fitness_centre_leisure(self):
        self.assertEqual(self._norm(leisure="fitness_centre"), ("leisure", "fitness_centre"))

    def test_pitch_leisure(self):
        self.assertEqual(self._norm(leisure="pitch"), ("leisure", "pitch"))

    # new transport categories
    def test_bus_stop_highway(self):
        self.assertEqual(self._norm(highway="bus_stop"), ("transport", "bus_stop"))

    def test_platform_public_transport(self):
        self.assertEqual(self._norm(public_transport="platform"), ("transport", "bus_stop"))

    # healthcare OSM tag
    def test_healthcare_pharmacy(self):
        cat, sub = self._norm(healthcare="pharmacy")
        self.assertEqual(sub, "pharmacy")

    def test_healthcare_hospital(self):
        cat, sub = self._norm(healthcare="hospital")
        self.assertEqual(sub, "hospital")

    def test_healthcare_doctor_maps_to_clinic(self):
        cat, sub = self._norm(healthcare="doctor")
        self.assertEqual(sub, "clinic")

    # extended amenity
    def test_atm_amenity(self):
        self.assertEqual(self._norm(amenity="atm"), ("amenity", "atm"))

    def test_restaurant_amenity(self):
        self.assertEqual(self._norm(amenity="restaurant"), ("amenity", "restaurant"))

    # unknown value
    def test_unknown_returns_none(self):
        self.assertEqual(self._norm(amenity="unknown_type"), (None, None))


if __name__ == "__main__":
    unittest.main()
