import math

import numpy as np
import pytest

from src.core import cbir
from src.core.stats import counts_to_pmf, moments_from_counts


@pytest.fixture
def images():
    rng = np.random.default_rng(42)
    rgb = rng.integers(0, 256, (9, 11, 3), dtype=np.uint8)
    bands = rng.integers(0, 1001, (9, 11, 13), dtype=np.uint16)
    return {"rgb": rgb, "bands": bands, "scale": {"lo": [0] * 13, "hi": [1000] * 13}}


@pytest.mark.parametrize("mode,channels,multispectral", [
    ("gray", 1, False), ("rgb", 3, False), ("hsv", 3, False),
    ("ms13", 13, True), ("ndvi_ndwi", 2, True), ("ms13_idx", 15, True),
])
def test_pmf_feature_dimensions_and_channel_masses(images, mode, channels, multispectral):
    info = cbir.MODE_INFO[mode]
    assert info["kind"] == "pmf"
    assert info["needs_multispectral"] is multispectral
    assert info["metrics"] == ("euclid", "chi2", "intersection")

    counts = cbir.extract_counts(mode, **images)
    assert counts.shape == ((256,) if channels == 1 else (channels, 256))
    np.testing.assert_array_equal(counts.sum(axis=-1), np.full(channels, 9 * 11).squeeze())
    for bins in (8, 16, 32, 64, 128, 256):
        feature = cbir.counts_to_feature(counts, bins)
        assert feature.shape == (channels * bins,)
        assert feature.sum() == pytest.approx(1.0)
        np.testing.assert_allclose(feature.reshape(channels, bins).sum(axis=1), 1 / channels)


@pytest.mark.parametrize("mode,dimension,multispectral", [
    ("grid2", 36, False), ("grid4", 144, False), ("mle", 6, False), ("ms_mle", 26, True),
])
def test_moment_dimensions_and_metadata(images, mode, dimension, multispectral):
    info = cbir.MODE_INFO[mode]
    assert info["kind"] == "moment"
    assert info["needs_multispectral"] is multispectral
    assert info["metrics"] == ("euclid",)
    assert cbir.extract_moment_feature(mode, **images).shape == (dimension,)


def test_rgb_counts_are_coarsened_in_channel_order():
    rgb = np.array([[[32, 128, 255]]], dtype=np.uint8)

    counts = cbir.extract_counts("rgb", rgb=rgb)
    feature = cbir.counts_to_feature(counts, 32).reshape(3, 32)

    np.testing.assert_array_equal(counts.argmax(axis=1), [32, 128, 255])
    np.testing.assert_array_equal(feature.argmax(axis=1), [4, 16, 31])
    np.testing.assert_allclose(feature.max(axis=1), [1 / 3] * 3)


def test_counts_use_gray_and_hsv_levels():
    rgb = np.array([[[255, 0, 0], [0, 255, 0]]], dtype=np.uint8)
    gray = cbir.extract_counts("gray", rgb=rgb)
    hsv = cbir.extract_counts("hsv", rgb=rgb)
    np.testing.assert_array_equal(np.flatnonzero(gray), [76, 150])
    np.testing.assert_array_equal(np.flatnonzero(hsv[0]), [0, 85])
    np.testing.assert_array_equal(hsv[1:, 255], [2, 2])


def test_full_spectral_counts_append_ndvi_then_ndwi():
    levels = np.arange(13, dtype=np.uint16) * 10
    levels[[3, 7]] = [20, 60]
    bands = levels.reshape(1, 1, 13)
    scale = {"lo": [0] * 13, "hi": [510] * 13}

    bands_counts = cbir.extract_counts("ms13", bands=bands, scale=scale)
    indices_counts = cbir.extract_counts("ndvi_ndwi", bands=bands)
    combined = cbir.extract_counts("ms13_idx", bands=bands, scale=scale)

    np.testing.assert_array_equal(bands_counts.argmax(axis=1), levels // 2)
    np.testing.assert_array_equal(indices_counts.argmax(axis=1), [191, 64])
    np.testing.assert_array_equal(combined, np.concatenate([bands_counts, indices_counts]))


def test_rgb_modes_use_synthetic_rgb_when_only_bands_are_available():
    bands = np.zeros((1, 1, 13), dtype=np.uint16)
    bands[0, 0, 1:4] = [32, 64, 96]
    scale = {"lo": [0] * 13, "hi": [510] * 13}

    counts = cbir.extract_counts("rgb", bands=bands, scale=scale)
    mle = cbir.extract_moment_feature("mle", bands=bands, scale=scale)

    np.testing.assert_array_equal(counts.argmax(axis=1), [48, 32, 16])
    np.testing.assert_array_equal(mle, [48, 0, 32, 0, 16, 0])


@pytest.mark.parametrize("mode", ["ms13", "ndvi_ndwi", "ms13_idx", "ms_mle"])
def test_multispectral_modes_require_bands(mode, images):
    extract = cbir.extract_moment_feature if mode == "ms_mle" else cbir.extract_counts
    with pytest.raises(ValueError, match="bands"):
        extract(mode, rgb=images["rgb"], scale=images["scale"])


@pytest.mark.parametrize("mode,g", [("grid2", 2), ("grid4", 4)])
def test_grid_moments_of_a_uniform_image(mode, g):
    rgb = np.broadcast_to(np.array([20, 100, 220], dtype=np.uint8), (9, 11, 3))
    actual = cbir.extract_moment_feature(mode, rgb=rgb)
    expected = np.tile([20, 0, 0, 100, 0, 0, 220, 0, 0], g * g)

    np.testing.assert_array_equal(actual, expected)


def test_grid_moments_order_and_population_std():
    bases = np.arange(12, dtype=np.uint8).reshape(2, 2, 3) * 10
    rgb = np.repeat(np.repeat(bases, 2, axis=0), 2, axis=1)
    rgb[1::2, 1::2] += 4

    grid = cbir.extract_moment_feature("grid2", rgb=rgb).reshape(4, 3, 3)

    np.testing.assert_allclose(grid[..., 0], bases.reshape(4, 3) + 1)
    np.testing.assert_allclose(grid[..., 1], math.sqrt(3))
    np.testing.assert_allclose(grid[..., 2], 2 / math.sqrt(3))


def test_mle_features_use_population_standard_deviations_and_scaled_bands():
    rgb = np.array([[[2, 6, 10], [4, 10, 16]]], dtype=np.uint8)
    np.testing.assert_array_equal(cbir.extract_moment_feature("mle", rgb=rgb), [3, 1, 8, 2, 13, 3])
    indices = np.arange(13, dtype=np.uint16)
    weights = indices + 1
    bands = np.array([[weights * indices, weights * (indices + 2)]])
    scale = {"lo": [0] * 13, "hi": (255 * weights).tolist()}

    ms_mle = cbir.extract_moment_feature("ms_mle", bands=bands, scale=scale)

    np.testing.assert_array_equal(ms_mle.reshape(13, 2), np.column_stack([weights, np.ones(13)]))


def test_zscore_uses_only_training_statistics_and_floors_std():
    train = np.array([[2, 4, 1e-10], [6, 4, 3e-10]])
    test = np.array([[10, 4, 1e-8 + 2e-10]])

    mean, std = cbir.zscore_fit(train)

    np.testing.assert_allclose(mean, [4, 4, 2e-10], rtol=0, atol=1e-15)
    np.testing.assert_allclose(std, [2, 1e-8, 1e-8], rtol=0, atol=1e-15)
    np.testing.assert_allclose(cbir.zscore_apply(train, mean, std), [[-1, 0, -0.01], [1, 0, 0.01]])
    np.testing.assert_allclose(cbir.zscore_apply(test, mean, std), [[3, 0, 1]])


def test_slide_qa_and_qb_distances_and_a_ranks_before_b():
    q, a, b = map(counts_to_pmf, ([4, 5, 4, 3], [3, 5, 5, 3], [6, 2, 2, 6]))
    database = np.stack([b, a])

    for metric, expected, tolerance in [
        ("euclid", [0.3187, 0.0884], 5e-5),
        ("chi2", [0.2095, 0.01587], 5e-5),
        ("intersection", [1 - 0.6875, 1 - 0.9375], 1e-12),
    ]:
        np.testing.assert_allclose(cbir.distance_batch(q, database, metric), expected, rtol=0, atol=tolerance)
        indices, distances = cbir.search_topk(q, database, k=2, metric=metric)
        np.testing.assert_array_equal(indices, [1, 0])
        np.testing.assert_allclose(distances, expected[::-1], rtol=0, atol=tolerance)


@pytest.mark.parametrize("counts", [
    pytest.param(None, marks=pytest.mark.skip(reason="Histogram asli Latihan 12 belum tersedia")),
])
def test_slide_exercise_12_q_c1_c2(counts):
    q, c1, c2 = map(counts_to_pmf, counts)
    database = np.stack([c1, c2])

    np.testing.assert_allclose(cbir.distance_batch(q, database, "euclid"), [0.125, 0.75])
    np.testing.assert_allclose(1 - cbir.distance_batch(q, database, "intersection"), [0.875, 0.25])
    moments = [moments_from_counts(histogram) for histogram in counts]
    np.testing.assert_allclose([moment["mean"] for moment in moments], [1.5] * 3)
    np.testing.assert_allclose([moment["variance"] for moment in moments], [0.75, 1.0, 2.25])


@pytest.mark.parametrize("metric", ["euclid", "chi2", "intersection"])
def test_distance_batch_matches_scalar_loop(metric):
    query = [0.25, 0.75, 0.0, 0.0]
    matrix = [[0.5, 0.5, 0.0, 0.0], [0.0, 0.75, 0.25, 0.0], query, [0, 0, 0.25, 0.75]]
    expected = []
    for row in matrix:
        pairs = list(zip(query, row))
        if metric == "euclid":
            result = math.sqrt(sum((p - q) ** 2 for p, q in pairs))
        elif metric == "chi2":
            result = sum((p - q) ** 2 / (p + q) for p, q in pairs if p + q > 0)
        else:
            result = 1 - sum(min(p, q) for p, q in pairs)
        expected.append(result)

    with np.errstate(all="raise"):
        actual = cbir.distance_batch(query, matrix, metric, batch_size=2)

    np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-12)


def test_search_breaks_ties_by_index_and_excludes_only_the_query():
    database = [[1, 0], [1, 0], [0, 1], [1, 0]]
    query = database[1]

    indices, distances = cbir.search_topk(query, database, k=3, metric="chi2", query_index=1)
    np.testing.assert_array_equal(indices, [0, 3, 2])
    np.testing.assert_array_equal(distances, [0, 0, 2])

    indices, _ = cbir.search_topk(query, database, k=2, metric="chi2")
    np.testing.assert_array_equal(indices, [0, 1])


def test_precision_at_k_is_the_fraction_of_same_class_hits():
    assert cbir.precision_at_k(2, [2, 0, 2, 3, 2]) == pytest.approx(3 / 5)


def test_knn_predict_uses_votes_then_total_distance():
    assert cbir.knn_predict([1, 3, 3], [0.1, 0.5, 0.6]) == 3
    assert cbir.knn_predict([1, 3, 3, 1], [0.1, 0.2, 0.3, 0.9]) == 3


def test_confusion_matrix_rows_are_true_classes_and_columns_are_predictions():
    matrix = cbir.confusion_matrix([0, 0, 1, 2, 2], [1, 1, 1, 0, 2], n_classes=4)
    np.testing.assert_array_equal(matrix, [[0, 2, 0, 0], [0, 1, 0, 0], [1, 0, 1, 0], [0, 0, 0, 0]])
