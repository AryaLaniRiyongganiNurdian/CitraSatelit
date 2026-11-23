import math

import numpy as np
import pytest

from src.core import stats


def test_slide_histogram_and_moments():
    pixels = np.array([
        [0, 0, 1, 1],
        [0, 1, 1, 2],
        [1, 2, 2, 3],
        [2, 2, 3, 3],
    ], dtype=np.uint8)
    counts = stats.histogram_counts(pixels, bins=4, levels=4)
    np.testing.assert_array_equal(counts, [3, 5, 5, 3])
    assert counts.dtype == np.int64

    pmf = stats.counts_to_pmf(counts)
    assert pmf.dtype == np.float64
    np.testing.assert_allclose(pmf, counts / 16, rtol=0, atol=1e-9)
    assert np.sum(np.arange(4) ** 2 * pmf) == pytest.approx(3.25, abs=1e-9)
    moments = stats.moments_from_counts(counts)
    assert moments["mean"] == pytest.approx(1.5, abs=1e-9)
    assert moments["variance"] == pytest.approx(1.0, abs=1e-9)
    assert moments["kurtosis"] == pytest.approx(1.9375, abs=1e-9)


@pytest.mark.parametrize("counts,mean,variance,skewness", [
    pytest.param([4, 5, 4, 3], 1.375, 1.109375, 0.1706, id="Q"),
    pytest.param([3, 5, 5, 3], 1.5, 1.0, 0.0, id="A"),
    pytest.param([6, 2, 2, 6], 1.5, 1.75, 0.0, id="B"),
])
def test_slide_image_moments(counts, mean, variance, skewness):
    moments = stats.moments_from_counts(counts)
    assert moments["mean"] == pytest.approx(mean, abs=1e-9)
    assert moments["variance"] == pytest.approx(variance, abs=1e-9)
    assert moments["std"] == pytest.approx(variance ** 0.5, abs=1e-9)
    assert moments["skewness"] == pytest.approx(skewness, abs=1e-3 if skewness else 1e-9)
    assert moments["degenerate"] is False


def test_constant_moments_with_explicit_values():
    assert stats.moments_from_counts([0, 5], values=[4, 10]) == {
        "mean": 10.0, "variance": 0.0, "std": 0.0,
        "skewness": 0.0, "kurtosis": 0.0, "degenerate": True,
    }
    with pytest.raises(ValueError):
        stats.counts_to_pmf([0, 0])


@pytest.mark.parametrize("bins", [8, 16, 32, 64, 128, 256])
def test_integer_binning_matches_histogram_and_coarsening(bins):
    pixels = np.repeat(np.arange(256, dtype=np.uint8), np.arange(1, 257) % 5 + 1)
    reference, _ = np.histogram(pixels, bins=bins, range=(0, 256))
    full_counts = stats.histogram_counts(pixels, 256)
    np.testing.assert_array_equal(stats.histogram_counts(pixels, bins), reference)
    np.testing.assert_array_equal(stats.coarsen_counts(full_counts, bins), reference)


def test_binning_uint16_widens_before_multiplication():
    pixels = np.array([0, 255, 256, 32768, 65535], dtype=np.uint16)
    expected = np.zeros(256, dtype=np.int64)
    expected[[0, 1, 128, 255]] = [2, 1, 1, 1]
    np.testing.assert_array_equal(stats.histogram_counts(pixels, 256, 65536), expected)


def test_slide_binomial_mgf_and_derivatives():
    x = np.arange(11)
    pmf = np.array([math.comb(10, int(k)) * 0.8 ** k * 0.2 ** (10 - k) for k in x])
    t = np.array([-1.0, 0.0, 0.25, 1.0])
    expected = (0.2 + 0.8 * np.exp(t)) ** 10
    np.testing.assert_allclose(stats.mgf_empirical(x, pmf, t), expected, rtol=0, atol=1e-9)
    assert isinstance(stats.mgf_empirical(x, pmf, 0), float)
    assert stats.mgf_empirical(x, pmf, 0) == pytest.approx(1.0, abs=1e-9)
    assert np.sum(x * pmf) == pytest.approx(8.0, abs=1e-9)
    assert np.sum(x ** 2 * pmf) == pytest.approx(65.6, abs=1e-9)

    counts = np.pad(pmf, (0, 256 - len(pmf)))
    result = stats.mgf_check(counts)
    assert result["m1_exact"] * 255 == pytest.approx(8.0, abs=1e-9)
    assert result["m2_exact"] * 255 ** 2 == pytest.approx(65.6, abs=1e-9)
    assert result["m1_fd"] * 255 == pytest.approx(8.0, abs=1e-4)
    assert result["m2_fd"] * 255 ** 2 == pytest.approx(65.6, abs=1e-2)


def test_mgf_check_at_full_intensity():
    counts = np.zeros(256)
    counts[[0, 255]] = 1
    result = stats.mgf_check(counts, h=1e-3)
    assert result["m1_exact"] == pytest.approx(0.5, abs=1e-9)
    assert result["m2_exact"] == pytest.approx(0.5, abs=1e-9)
    assert result["m1_fd"] == pytest.approx(0.5, abs=1e-4)
    assert result["m2_fd"] == pytest.approx(0.5, abs=1e-2)


def test_slide_mle_vectors():
    assert stats.mle_gaussian([100, 120, 110, 130]) == pytest.approx((115, 125), abs=1e-9)
    assert stats.mle_poisson([5, 7, 4, 6, 8]) == pytest.approx(6, abs=1e-9)
    assert stats.mle_exponential([2, 3, 1, 4]) == pytest.approx(2.5, abs=1e-9)
    assert stats.mle_bernoulli([1] * 8 + [0] * 2) == pytest.approx(0.8, abs=1e-9)
    geometric = [1, 2, 2, 5]
    assert stats.mle_geometric(geometric) == pytest.approx(len(geometric) / sum(geometric), abs=1e-9)
