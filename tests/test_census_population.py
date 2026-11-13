import io
import unittest
import zipfile

import numpy as np
import pandas as pd

from recomendacao_imobiliaria.census_population import (
    allocate_to_cells,
    check_ibge_code,
    latest_aggregates_url,
    read_sector_population,
    round_preserving_total,
    uf_of,
)

try:
    import geopandas as gpd
    from shapely.geometry import box
except ModuleNotFoundError:  # ambiente sem geopandas
    gpd = None


def aggregates_zip(path, rows):
    header = '"CD_SETOR";"SITUACAO";"CD_MUN";"NM_MUN";"v0001";"v0002";"v0007"'
    body = "\n".join(";".join(f'"{value}"' for value in row) for row in rows)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("Agregados_por_setores_basico_BR.csv", (header + "\n" + body).encode("latin-1"))


class CensusFilesTest(unittest.TestCase):
    def test_reads_only_the_requested_municipality_and_handles_missing_values(self):
        buffer = io.BytesIO()
        aggregates_zip(buffer, [
            ("315250105000001", "Urbana", "3152501", "Pouso Alegre", "466", "279", "270"),
            ("315250105000002", "Urbana", "3152501", "Pouso Alegre", ".", "285", "X"),
            ("315960505000001", "Urbana", "3159605", "Santa Rita do Sapucaí", "999", "1", "1"),
        ])
        frame = read_sector_population(buffer, "3152501")

        self.assertEqual(list(frame["cd_setor"]), ["315250105000001", "315250105000002"])
        self.assertEqual(frame.loc[0, "population"], 466)
        self.assertEqual(frame.loc[0, "households"], 270)
        self.assertTrue(np.isnan(frame.loc[1, "population"]))   # "." = sem valor, nunca zero inventado
        self.assertTrue(np.isnan(frame.loc[1, "households"]))

    def test_unknown_municipality_fails_instead_of_returning_nothing(self):
        buffer = io.BytesIO()
        aggregates_zip(buffer, [("315960505000001", "Urbana", "3159605", "Santa Rita", "10", "1", "1")])
        with self.assertRaises(RuntimeError):
            read_sector_population(buffer, "3152501")

    def test_ibge_code_validation(self):
        self.assertEqual(uf_of("3152501"), "MG")
        self.assertEqual(uf_of("3550308"), "SP")
        for bad in ("315250", "31525011", "abcdefg", "9952501", "3152501' OR '1'='1"):
            with self.assertRaises(ValueError):
                check_ibge_code(bad)

    def test_picks_the_most_recent_aggregates_file(self):
        html = (
            '<a href="Agregados_por_setores_basico_BR_20250101.zip">a</a>'
            '<a href="Agregados_por_setores_basico_BR_20260520.zip">b</a>'
            '<a href="Agregados_por_setores_caracteristicas_domicilio1_BR_20261021.zip">c</a>'
        )
        self.assertTrue(latest_aggregates_url(html).endswith("Agregados_por_setores_basico_BR_20260520.zip"))
        self.assertIsNone(latest_aggregates_url("<html></html>"))

    def test_rounding_keeps_the_total(self):
        values = np.array([10.4, 10.4, 10.4, 0.8])
        rounded = round_preserving_total(values)
        self.assertEqual(int(rounded.sum()), 32)
        self.assertTrue(((rounded - values) < 1).all() and ((rounded - values) > -1).all())


@unittest.skipIf(gpd is None, "geopandas nao instalado")
class CensusAllocationTest(unittest.TestCase):
    def cells(self):
        return gpd.GeoDataFrame({"h3_id": ["a", "b", "c"]},
                                geometry=[box(0, 0, 10, 10), box(10, 0, 20, 10), box(20, 0, 30, 10)])

    def sectors(self, rows):
        return gpd.GeoDataFrame(
            {"cd_setor": [r[0] for r in rows], "population": [r[1] for r in rows], "households": [r[2] for r in rows]},
            geometry=[r[3] for r in rows],
        )

    def test_population_is_split_by_area_and_conserved(self):
        sectors = self.sectors([("s1", 100.0, 40.0, box(0, 0, 20, 10)), ("s2", 60.0, 20.0, box(20, 0, 30, 10))])
        result, summary = allocate_to_cells(sectors, self.cells())
        by_cell = result.set_index("h3_id")

        self.assertAlmostEqual(by_cell.loc["a", "population"], 50.0)
        self.assertAlmostEqual(by_cell.loc["b", "population"], 50.0)
        self.assertAlmostEqual(by_cell.loc["c", "population"], 60.0)
        self.assertAlmostEqual(by_cell.loc["a", "households"], 20.0)
        self.assertAlmostEqual(summary["population_allocated"], 160.0)
        self.assertEqual(summary["sectors_outside_grid"], 0)

    def test_sector_partly_outside_the_grid_keeps_all_its_people_in_the_covered_cells(self):
        # Metade do setor cai fora da grade: a populacao inteira fica nas celulas que ele toca.
        sectors = self.sectors([("s1", 100.0, 40.0, box(25, 0, 40, 10))])
        result, summary = allocate_to_cells(sectors, self.cells())

        self.assertAlmostEqual(result.set_index("h3_id").loc["c", "population"], 100.0)
        self.assertAlmostEqual(summary["population_allocated"], 100.0)
        self.assertEqual(summary["sectors_partly_outside_grid"], 1)

    def test_sector_with_no_cell_is_reported_not_silently_dropped(self):
        sectors = self.sectors([("s1", 70.0, 30.0, box(100, 0, 110, 10)), ("s2", 30.0, 10.0, box(0, 0, 10, 10))])
        result, summary = allocate_to_cells(sectors, self.cells())

        self.assertEqual(summary["sectors_outside_grid"], 1)
        self.assertAlmostEqual(summary["population_outside_grid"], 70.0)
        self.assertAlmostEqual(summary["population_allocated"], 30.0)

    def test_missing_population_counts_as_zero_without_breaking_the_rest(self):
        sectors = self.sectors([("s1", np.nan, np.nan, box(0, 0, 10, 10)), ("s2", 20.0, 5.0, box(10, 0, 20, 10))])
        result, _ = allocate_to_cells(sectors, self.cells())
        by_cell = result.set_index("h3_id")

        self.assertEqual(by_cell.loc["a", "population"], 0.0)
        self.assertAlmostEqual(by_cell.loc["b", "population"], 20.0)


if __name__ == "__main__":
    unittest.main()
