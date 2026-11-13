import unittest

import numpy as np

from recomendacao_imobiliaria.change_detection import (
    FEATURE_BANDS,
    AnnualComposite,
    ChangeParams,
    build_features,
    load_change_model,
    predict_probability,
    accumulate_max,
    agreement_metrics,
    aggregate_to_cells,
    annual_change,
    block_counts,
    ndvi_of,
)

PARAMS = ChangeParams(min_patch_pixels=1)
SHAPE = (6, 6)


def yearly(values, valid=None):
    """Maximo anual e contagem a partir de uma lista de NDVI (um valor por data)."""
    ndvi_max = np.full(SHAPE, -1.0, dtype="float32")
    observations = np.zeros(SHAPE, dtype="uint8")
    for index, value in enumerate(values):
        mask = np.ones(SHAPE, dtype=bool) if valid is None else valid[index]
        accumulate_max(ndvi_max, observations, np.full(SHAPE, value, dtype="float32"), mask)
    return ndvi_max, observations


class ChangeDetectionTest(unittest.TestCase):
    def test_vegetated_area_that_never_greens_again_is_detected(self):
        result = annual_change(*yearly([0.3, 0.7, 0.6]), *yearly([0.15, 0.2, 0.18]), PARAMS)
        self.assertTrue(result["changed"].all())

    def test_cropland_that_greens_up_once_is_not_change(self):
        # Solo exposto em duas datas, mas verde em uma: ciclo agricola, nao obra.
        result = annual_change(*yearly([0.3, 0.7, 0.6]), *yearly([0.15, 0.65, 0.18]), PARAMS)
        self.assertFalse(result["changed"].any())

    def test_area_already_bare_before_is_not_new_change(self):
        result = annual_change(*yearly([0.2, 0.25, 0.2]), *yearly([0.15, 0.2, 0.18]), PARAMS)
        self.assertFalse(result["changed"].any())

    def test_pixels_with_few_valid_observations_are_not_evaluated(self):
        cloudy = [np.ones(SHAPE, dtype=bool), np.zeros(SHAPE, dtype=bool), np.zeros(SHAPE, dtype=bool)]
        result = annual_change(*yearly([0.3, 0.7, 0.6]), *yearly([0.15, 0.2, 0.18], valid=cloudy), PARAMS)
        self.assertFalse(result["valid"].any())
        self.assertFalse(result["changed"].any())

    def test_cloud_cannot_fake_a_low_maximum(self):
        # A unica data verde esta sob nuvem em um canto: la restam 2 observacoes.
        valid = [np.ones(SHAPE, dtype=bool) for _ in range(3)]
        valid[1] = valid[1].copy()
        valid[1][0, 0] = False
        after_max, after_obs = yearly([0.15, 0.2, 0.18], valid=valid)
        result = annual_change(*yearly([0.3, 0.7, 0.6]), after_max, after_obs, PARAMS)
        self.assertFalse(result["valid"][0, 0])
        self.assertFalse(result["changed"][0, 0])
        self.assertTrue(result["changed"][1, 1])

    def test_small_isolated_patches_are_removed(self):
        before = yearly([0.3, 0.7, 0.6])
        after_max, after_obs = yearly([0.6, 0.7, 0.65])
        after_max[0, 0] = 0.2            # 1 pixel isolado
        after_max[3:5, 2:5] = 0.2        # mancha de 6 pixels
        result = annual_change(*before, after_max, after_obs, ChangeParams(min_patch_pixels=5))
        self.assertFalse(result["changed"][0, 0])
        self.assertEqual(int(result["changed"].sum()), 6)

    def test_ndvi_ignores_pixels_without_signal(self):
        ndvi = ndvi_of(np.array([0.04, 0.0], dtype="float32"), np.array([0.40, 0.0], dtype="float32"))
        self.assertAlmostEqual(float(ndvi[0]), 0.818, places=3)
        self.assertTrue(np.isnan(ndvi[1]))

    def test_aggregation_uses_only_pixels_of_each_cell(self):
        labels = np.array([[1, 1, 2, 2], [1, 1, 2, 2], [0, 0, 2, 2]])
        changed = np.array([[1, 0, 0, 0], [0, 0, 0, 0], [1, 1, 1, 1]], dtype=bool)
        valid = np.ones_like(changed)
        valid[0, 3] = False
        frame = aggregate_to_cells(changed, valid, labels, ["a", "b"]).set_index("h3_id")

        self.assertAlmostEqual(frame.loc["a", "changed_fraction"], 0.25)
        self.assertAlmostEqual(frame.loc["b", "changed_fraction"], 0.4)   # 2 de 5 validos
        self.assertAlmostEqual(frame.loc["b", "valid_fraction"], 5 / 6, places=3)
        self.assertAlmostEqual(frame.loc["a", "changed_area_ha"], 0.01)

    def test_block_metrics(self):
        detected = block_counts(np.array([[1, 1, 0, 0], [1, 1, 0, 0], [0, 0, 0, 0], [0, 0, 1, 1]], dtype=bool), 2) >= 2
        truth = np.array([[True, False], [True, True]])
        metrics = agreement_metrics(detected, truth)

        self.assertEqual((metrics["tp"], metrics["fp"], metrics["fn"]), (2, 0, 1))
        self.assertEqual(metrics["precision"], 1.0)
        self.assertAlmostEqual(metrics["recall"], 0.667, places=3)

    def test_aggregation_adds_probable_level_when_present(self):
        labels = np.array([[1, 1, 2, 2], [1, 1, 2, 2]])
        changed = np.zeros(labels.shape, dtype=bool)
        probable = np.array([[1, 1, 0, 0], [0, 0, 0, 0]], dtype=bool)
        frame = aggregate_to_cells(changed, np.ones_like(changed), labels, ["a", "b"], probable).set_index("h3_id")

        self.assertAlmostEqual(frame.loc["a", "probable_fraction"], 0.5)
        self.assertAlmostEqual(frame.loc["b", "probable_fraction"], 0.0)
        self.assertNotIn("probable_fraction", aggregate_to_cells(changed, np.ones_like(changed), labels, ["a", "b"]))


def composite(year, ndvi_max, shape=(40, 40)):
    full = lambda value: np.full(shape, value, dtype="float32")  # noqa: E731
    return AnnualComposite(
        year, full(ndvi_max), np.full(shape, 5, dtype="uint8"), [],
        full(0.1), full(0.4), {band: np.full(shape, 1500, dtype="uint16") for band in FEATURE_BANDS},
        np.ones(shape, dtype=bool),
    )


class ChangeClassifierTest(unittest.TestCase):
    def test_features_are_deterministic_and_complete(self):
        before, after = composite(2019, 0.8), composite(2023, 0.2)
        first, second = build_features(before, after), build_features(before, after)

        self.assertEqual(list(first), list(second))
        self.assertAlmostEqual(float(first["d_max"][0, 0]), -0.6, places=5)
        self.assertEqual(sum(name.startswith("ctx_") for name in first), 6)
        self.assertTrue(all(value.shape == (40, 40) for value in first.values()))

    def test_shipped_model_matches_the_feature_builder(self):
        try:
            import lightgbm  # noqa: F401
        except ImportError:
            self.skipTest("lightgbm nao instalado neste ambiente")
        loaded = load_change_model()
        if loaded is None:
            self.skipTest("modelo ainda nao treinado")
        booster, meta = loaded
        features = build_features(composite(2019, 0.8), composite(2023, 0.2))

        self.assertEqual(sorted(meta["features"]), sorted(features))
        self.assertEqual(booster.num_feature(), len(meta["features"]))
        probability = predict_probability(booster, meta["features"], features, np.ones((40, 40), dtype=bool))
        self.assertTrue(((probability >= 0) & (probability <= 1)).all())

    def test_prediction_requires_every_model_feature(self):
        with self.assertRaises(ValueError):
            predict_probability(None, ["nao_existe"], {}, np.ones((2, 2), dtype=bool))


if __name__ == "__main__":
    unittest.main()
