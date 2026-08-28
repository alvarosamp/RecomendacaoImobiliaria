import unittest
import numpy as np

from recomendacao_imobiliaria.sentinel1_collector import water_fraction
from recomendacao_imobiliaria.terrain_collector import slope_pct_from_elevation_range


class TerrainCollectorsTest(unittest.TestCase):
    def test_slope_estimate(self):
        self.assertEqual(slope_pct_from_elevation_range(70, 700), 10.0)

    def test_water_fraction_uses_both_polarizations(self):
        vv = np.array([[0.02, 0.12]])
        vh = np.array([[0.01, 0.01]])
        self.assertEqual(water_fraction(vv, vh), 0.5)
