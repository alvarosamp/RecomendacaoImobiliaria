import unittest

try:
    import geopandas as gpd
    from shapely.geometry import box, mapping
except ModuleNotFoundError:  # ambiente sem geopandas
    gpd = None

from recomendacao_imobiliaria.place_names import street_label

# Ponto de referencia em Pouso Alegre; 0,001 grau ~ 100 m.
LON, LAT = -45.94, -22.23
STEP = 0.001


def cell(h3_id, west, south, east, north):
    return h3_id, box(LON + west * STEP, LAT + south * STEP, LON + east * STEP, LAT + north * STEP)


def street(name, highway, x1, y1, x2, y2):
    return {"name": name, "highway": highway, "coords": [(LON + x1 * STEP, LAT + y1 * STEP), (LON + x2 * STEP, LAT + y2 * STEP)]}


@unittest.skipIf(gpd is None, "geopandas nao instalado")
class PlaceNamesTest(unittest.TestCase):
    def cells(self, items):
        frame = gpd.GeoDataFrame({"h3_id": [i[0] for i in items]}, geometry=[i[1] for i in items], crs=4326)
        return frame, frame.to_crs(31983)

    def test_main_street_wins_over_a_longer_residential_one(self):
        from recomendacao_imobiliaria.place_names import rank_streets_in_cells

        _, metric = self.cells([cell("a", 0, 0, 10, 10)])
        ranked = rank_streets_in_cells([
            street("Rua das Flores", "residential", 0, 2, 10, 2),          # 10 trechos
            street("Avenida Central", "primary", 0, 5, 8, 5),             # mais curta, mas arterial
        ], metric)

        self.assertEqual([item["name"] for item in ranked["a"]], ["Avenida Central", "Rua das Flores"])
        self.assertEqual(ranked["a"][0]["highway"], "primary")

    def test_street_split_in_several_ways_is_summed_and_cut_by_cell(self):
        from recomendacao_imobiliaria.place_names import rank_streets_in_cells

        _, metric = self.cells([cell("a", 0, 0, 5, 10), cell("b", 5, 0, 10, 10)])
        ranked = rank_streets_in_cells([
            street("Rua Longa", "residential", 0, 5, 3, 5),
            street("Rua Longa", "residential", 3, 5, 10, 5),
        ], metric)

        self.assertEqual(ranked["a"][0]["name"], "Rua Longa")
        self.assertEqual(ranked["b"][0]["name"], "Rua Longa")
        # 5 x 0,001 grau de longitude, perto de 100 m cada: a rua e cortada pela celula.
        self.assertTrue(400 < ranked["a"][0]["meters"] < 600)
        self.assertTrue(400 < ranked["b"][0]["meters"] < 600)

    def test_tiny_fragments_and_cells_without_streets_are_left_out(self):
        from recomendacao_imobiliaria.place_names import rank_streets_in_cells

        _, metric = self.cells([cell("a", 0, 0, 10, 10), cell("far", 50, 50, 60, 60)])
        ranked = rank_streets_in_cells([street("Beco", "residential", 9.9, 5, 10.1, 5)], metric)

        self.assertNotIn("far", ranked)
        self.assertNotIn("a", ranked)      # menos de 40 m dentro da celula

    def test_returns_at_most_three_streets(self):
        from recomendacao_imobiliaria.place_names import rank_streets_in_cells

        _, metric = self.cells([cell("a", 0, 0, 10, 10)])
        ranked = rank_streets_in_cells([street(f"Rua {i}", "residential", 0, i + 1, 10, i + 1) for i in range(6)], metric)

        self.assertEqual(len(ranked["a"]), 3)

    def collection(self):
        def feature(name, kind, geometry, approximate=False):
            return {"type": "Feature", "geometry": mapping(geometry),
                    "properties": {"name": name, "kind": kind, "approximate": approximate}}

        west = box(LON + 0 * STEP, LAT + 0 * STEP, LON + 10 * STEP, LAT + 10 * STEP)
        return {"type": "FeatureCollection", "features": [
            feature("Bairro Central", "bairro", west),
            feature("Quadrante Norte", "quadrante", box(LON - 1, LAT - 1, LON + 1, LAT + 1)),
        ]}

    def test_neighborhood_is_the_one_covering_most_of_the_cell(self):
        from recomendacao_imobiliaria.place_names import assign_neighborhoods

        # Celula com 70% dentro do bairro: o centro dela pode cair fora, mas o bairro prevalece.
        ll, metric = self.cells([cell("a", 3, 0, 13, 10)])
        result = assign_neighborhoods(metric, ll, self.collection()).set_index("h3_id")

        self.assertEqual(result.loc["a", "neighborhood"], "Bairro Central")
        self.assertEqual(result.loc["a", "neighborhood_source"], "limite")

    def test_cell_barely_touching_a_neighborhood_falls_back_to_the_point_rule(self):
        from recomendacao_imobiliaria.place_names import assign_neighborhoods

        ll, metric = self.cells([cell("edge", 9, 0, 19, 10)])   # so ~10% dentro do bairro
        result = assign_neighborhoods(metric, ll, self.collection()).set_index("h3_id")

        self.assertEqual(result.loc["edge", "neighborhood"], "Quadrante Norte")
        self.assertEqual(result.loc["edge", "neighborhood_source"], "quadrante")

    def test_street_label(self):
        self.assertEqual(street_label([{"name": "Rua A"}, {"name": "Avenida B"}]), "Rua A · Avenida B")
        self.assertIsNone(street_label([]))
        self.assertIsNone(street_label(None))


if __name__ == "__main__":
    unittest.main()
