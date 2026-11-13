import unittest

from recomendacao_imobiliaria.scoring import AreaFeatures, score_area


class ScoringTest(unittest.TestCase):
    def test_zoning_blocks_scores_when_use_is_not_allowed(self):
        result = score_area(
            AreaFeatures(
                h3_id="blocked",
                residential_allowed=False,
                commercial_allowed=False,
                poi_supermarket_cnt=0,
                poi_pharmacy_cnt=0,
                poi_school_cnt=0,
            )
        )

        self.assertEqual(result.score_residencial, 0.0)
        self.assertEqual(result.score_comercial, 0.0)
        self.assertEqual(result.explain["main_recommendations"][0]["use"], "nenhum")

    def test_commercial_gap_generates_recommendation(self):
        result = score_area(
            AreaFeatures(
                h3_id="gap",
                poi_supermarket_cnt=0,
                poi_pharmacy_cnt=2,
                poi_school_cnt=1,
                commercial_allowed=True,
            )
        )

        uses = [item["use"] for item in result.explain["main_recommendations"]]
        self.assertIn("mercado", uses)

    def test_explain_includes_confidence_and_factors(self):
        result = score_area(
            AreaFeatures(
                h3_id="explain",
                zona="ZMC",
                ndvi_mean_90=0.4,
                ndbi_mean_90=0.3,
                ndbi_slope_180=0.05,
                ndvi_slope_180=-0.02,
                poi_supermarket_cnt=0,
                poi_pharmacy_cnt=0,
                poi_school_cnt=0,
                dist_min_supermarket_m=500,
                dist_min_pharmacy_m=600,
                dist_min_school_m=700,
            )
        )

        self.assertIn("confidence", result.explain)
        self.assertIn("positive_factors", result.explain)
        self.assertIn("contributions", result.explain)
        self.assertGreater(result.explain["confidence"], 0)

    def test_growth_ignores_citywide_seasonal_trend(self):
        from recomendacao_imobiliaria.scoring import urban_growth_signal

        # Queda de NDVI igual a da cidade inteira (estacao seca) nao e crescimento.
        seasonal = AreaFeatures(
            h3_id="seasonal", ndvi_slope_180=-0.001, ndbi_slope_180=0.0009,
            ndvi_slope_baseline=-0.001, ndbi_slope_baseline=0.0009,
        )
        building = AreaFeatures(
            h3_id="building", ndvi_slope_180=-0.0015, ndbi_slope_180=0.0014,
            ndvi_slope_baseline=-0.001, ndbi_slope_baseline=0.0009,
        )

        self.assertEqual(urban_growth_signal(seasonal), 0.0)
        self.assertGreater(urban_growth_signal(building), 0.5)

    def test_growth_trend_is_ignored_outside_zoned_perimeter(self):
        from recomendacao_imobiliaria.scoring import urban_growth_signal

        # Mesma tendencia: fora do perimetro zoneado (lavoura, solo exposto) nao conta.
        trend = dict(ndvi_slope_180=-0.0015, ndbi_slope_180=0.0014, ndbi_mean_90=-0.05)
        rural = AreaFeatures(h3_id="rural", growth_trend_reliable=False, **trend)
        urban = AreaFeatures(h3_id="urban", zona="ZM1", **trend)

        self.assertEqual(urban_growth_signal(rural), 0.0)
        self.assertGreater(urban_growth_signal(urban), 0.5)

    def test_yearly_change_detection_replaces_index_trend(self):
        from recomendacao_imobiliaria.scoring import urban_growth_signal

        # Slopes fortes, mas a deteccao anual nao viu mudanca: nao ha crescimento.
        stable = AreaFeatures(
            h3_id="stable", zona="ZM1", ndvi_slope_180=-0.002, ndbi_slope_180=0.002,
            change_fraction=0.0, change_valid_fraction=0.9,
        )
        growing = AreaFeatures(h3_id="growing", zona="ZM1", change_fraction=0.15, change_valid_fraction=0.9)
        cloudy = AreaFeatures(
            h3_id="cloudy", zona="ZM1", ndvi_slope_180=-0.002, ndbi_slope_180=0.002,
            change_fraction=0.0, change_valid_fraction=0.2,
        )

        self.assertEqual(urban_growth_signal(stable), 0.0)
        self.assertAlmostEqual(urban_growth_signal(growing), 0.8)
        self.assertGreater(urban_growth_signal(cloudy), 0.5)   # pouca area valida: volta aos slopes
        self.assertEqual(score_area(growing).explain["growth_source"], "deteccao_anual_10m")

    def test_demand_follows_population_not_a_fixed_target(self):
        rates = {"supermarket": 1 / 10_000, "pharmacy": 1 / 5_000, "school": 1 / 8_000}
        empty = dict(h3_id="x", zona="ZM1", poi_supermarket_cnt=0, poi_pharmacy_cnt=0, poi_school_cnt=0, service_rates=rates)

        no_people = score_area(AreaFeatures(population_catchment=0.0, **empty))
        crowded = score_area(AreaFeatures(population_catchment=40_000.0, **empty))

        # Sem moradores nao ha demanda, mesmo sem nenhum estabelecimento mapeado.
        self.assertEqual(no_people.explain["commercial_gap"], 0.0)
        self.assertEqual(no_people.explain["main_recommendations"], [])
        self.assertEqual(crowded.explain["commercial_gap"], 1.0)
        self.assertGreater(crowded.score_comercial, no_people.score_comercial)
        self.assertEqual(crowded.explain["demand"]["basis"], "populacao_do_entorno")

    def test_unmet_is_expected_minus_mapped_establishments(self):
        rates = {"supermarket": 1 / 10_000, "pharmacy": 1 / 10_000, "school": 1 / 10_000}
        base = dict(h3_id="x", zona="ZM1", poi_pharmacy_cnt=9, poi_school_cnt=9, population_catchment=20_000.0, service_rates=rates)

        short = score_area(AreaFeatures(poi_supermarket_cnt=1, **base)).explain["demand"]
        served = score_area(AreaFeatures(poi_supermarket_cnt=2, **base)).explain["demand"]
        half = score_area(AreaFeatures(poi_supermarket_cnt=0, **{**base, "population_catchment": 5_000.0})).explain["demand"]

        self.assertEqual(short["expected_establishments"]["supermarket"], 2.0)
        self.assertEqual(short["unmet_establishments"]["supermarket"], 1.0)
        self.assertEqual(served["unmet_establishments"]["supermarket"], 0.0)
        self.assertEqual(half["unmet_establishments"]["supermarket"], 0.5)

    def test_without_population_the_fixed_targets_still_apply(self):
        result = score_area(AreaFeatures(h3_id="x", zona="ZM1", poi_supermarket_cnt=0, poi_pharmacy_cnt=0, poi_school_cnt=0))

        self.assertEqual(result.explain["demand"]["basis"], "metas_fixas_por_celula")
        self.assertEqual(result.explain["commercial_gap"], 1.0)

    def test_population_adds_to_confidence(self):
        rates = {"supermarket": 1e-4, "pharmacy": 1e-4, "school": 1e-4}
        common = dict(h3_id="x", zona="ZM1", poi_supermarket_cnt=0, poi_pharmacy_cnt=0, poi_school_cnt=0)
        with_pop = score_area(AreaFeatures(population_catchment=1000.0, service_rates=rates, **common))
        without = score_area(AreaFeatures(**common))

        self.assertGreater(with_pop.explain["confidence"], without.explain["confidence"])

    def test_zoning_is_only_validated_when_layer_is_official(self):
        sample = score_area(AreaFeatures(h3_id="sample", zona="ZM1"))
        official = score_area(AreaFeatures(h3_id="official", zona="ZM1", zoning_official=True))

        self.assertEqual(sample.explain["zoning"]["validation_status"], "unverified_zoning")
        self.assertEqual(official.explain["zoning"]["validation_status"], "validated_official")
        self.assertLess(sample.explain["confidence"], official.explain["confidence"])

    def test_confidence_scales_with_available_distances(self):
        one = score_area(AreaFeatures(h3_id="one", dist_min_school_m=500))
        three = score_area(AreaFeatures(
            h3_id="three", dist_min_school_m=500, dist_min_pharmacy_m=500, dist_min_supermarket_m=500,
        ))

        self.assertLess(one.explain["confidence"], three.explain["confidence"])


if __name__ == "__main__":
    unittest.main()
