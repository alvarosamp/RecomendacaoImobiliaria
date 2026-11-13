import unittest

from recomendacao_imobiliaria.mapbox_access import IsochroneBand, classify_band
from recomendacao_imobiliaria.scoring import AreaFeatures, score_area, travel_time_summary


def square(center_lon, center_lat, half_side):
    lo_x, hi_x = center_lon - half_side, center_lon + half_side
    lo_y, hi_y = center_lat - half_side, center_lat + half_side
    return {
        "type": "Polygon",
        "coordinates": [[[lo_x, lo_y], [hi_x, lo_y], [hi_x, hi_y], [lo_x, hi_y], [lo_x, lo_y]]],
    }


class ClassifyBandTest(unittest.TestCase):
    def setUp(self):
        # Bandas concentricas: 5 min = quadrado pequeno, 10 e 15 min maiores.
        self.bands = [
            IsochroneBand(minutes=5, geometry=square(0, 0, 0.01)),
            IsochroneBand(minutes=10, geometry=square(0, 0, 0.02)),
            IsochroneBand(minutes=15, geometry=square(0, 0, 0.03)),
        ]

    def test_point_inside_innermost_band_gets_smallest_minutes(self):
        self.assertEqual(classify_band(0.0, 0.0, self.bands), 5)

    def test_point_only_in_outer_band_gets_its_minutes(self):
        self.assertEqual(classify_band(0.025, 0.0, self.bands), 15)

    def test_point_outside_all_bands_is_none(self):
        self.assertIsNone(classify_band(1.0, 1.0, self.bands))

    def test_band_order_in_input_does_not_matter(self):
        shuffled = [self.bands[2], self.bands[0], self.bands[1]]
        self.assertEqual(classify_band(0.0, 0.0, shuffled), 5)


class TravelTimeSummaryTest(unittest.TestCase):
    def test_summary_reports_bands_and_never_claims_use_in_score(self):
        summary = travel_time_summary(
            AreaFeatures(h3_id="x", travel_min_supermarket=10, travel_min_pharmacy=None, travel_min_school=5)
        )
        self.assertEqual(summary["bands_minutes"], {"supermarket": 10, "pharmacy": None, "school": 5})
        self.assertTrue(summary["available"])
        self.assertFalse(summary["used_in_score"])

    def test_summary_unavailable_when_no_band_present(self):
        summary = travel_time_summary(AreaFeatures(h3_id="x"))
        self.assertFalse(summary["available"])


class CalibratedScoreUnaffectedTest(unittest.TestCase):
    """Garante que a camada do Mapbox e puramente informativa.

    Mesmas entradas usadas no score calibrado, com e sem os campos
    `travel_min_*` preenchidos: os dois scores devem ser identicos. Se um dia
    isso quebrar, alguem misturou a camada nova na formula calibrada.
    """

    def _features(self, **travel):
        return AreaFeatures(
            h3_id="cell",
            zona="ZMC",
            ndvi_mean_90=0.3,
            poi_supermarket_cnt=1,
            poi_pharmacy_cnt=1,
            poi_school_cnt=1,
            dist_min_supermarket_m=800,
            dist_min_pharmacy_m=500,
            dist_min_school_m=1000,
            **travel,
        )

    def test_score_identical_with_or_without_travel_bands(self):
        without = score_area(self._features())
        with_bands = score_area(self._features(travel_min_supermarket=5, travel_min_pharmacy=10, travel_min_school=None))

        self.assertEqual(without.score_residencial, with_bands.score_residencial)
        self.assertEqual(without.score_comercial, with_bands.score_comercial)
        for key in without.explain:
            if key == "travel_time_access":
                continue
            self.assertEqual(without.explain[key], with_bands.explain[key], key)


if __name__ == "__main__":
    unittest.main()
