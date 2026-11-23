import numpy as np
import pytest

from src.core import spectral


def test_ndvi_and_ndwi_match_hand_calculations():
    bands = np.full((2, 3, 13), 47, dtype=np.uint16)
    bands[..., 2] = [[1000, 3000, 0], [0, 4000, 32768]]  # B03
    bands[..., 3] = [[1000, 3000, 0], [4000, 0, 32768]]  # B04
    bands[..., 7] = [[3000, 1000, 0], [0, 0, 65535]]  # B08
    fraction = 32767 / 98303

    with np.errstate(all="raise"):
        ndvi = spectral.ndvi(bands)
        ndwi = spectral.ndwi(bands)

    assert ndvi.shape == ndwi.shape == (2, 3)
    assert ndvi.dtype == ndwi.dtype == np.float64
    np.testing.assert_allclose(ndvi, [[0.5, -0.5, 0], [-1, 0, fraction]], rtol=0, atol=1e-12)
    np.testing.assert_allclose(ndwi, [[-0.5, 0.5, 0], [0, 1, -fraction]], rtol=0, atol=1e-12)


@pytest.mark.parametrize("value,level", [(-1, 0), (0, 128), (1, 255)])
def test_ndi_to_level_scalar(value, level):
    result = spectral.ndi_to_level(value)

    assert np.asarray(result).dtype == np.uint8
    assert result == level


def test_ndi_to_level_clips_and_rounds():
    values = np.array([[-1.2, -0.5, 0.0], [0.5, 1.0, 1.2]])

    levels = spectral.ndi_to_level(values)

    assert levels.dtype == np.uint8
    np.testing.assert_array_equal(levels, [[0, 64, 128], [191, 255, 255]])


def test_fit_percentile_scale_matches_numpy_per_band():
    rng = np.random.default_rng(42)
    levels = np.arange(120, dtype=np.uint16)
    pixels = np.stack([
        rng.permutation(levels) + band * 1000 for band in range(13)
    ], axis=1)
    samples = pixels.reshape(2, 5, 12, 13)

    scale = spectral.fit_percentile_scale(samples)

    lower = np.percentile(pixels, [2, 98], axis=0, method="lower")
    assert scale == {"lo": lower[0].tolist(), "hi": lower[1].tolist()}
    linear = np.percentile(pixels, [2, 98], axis=0)
    np.testing.assert_allclose([scale["lo"], scale["hi"]], linear, rtol=0, atol=1)


def test_fit_percentile_scale_takes_floor_rank_for_sparse_values():
    offsets = np.arange(13, dtype=np.uint16)
    samples = np.array([400, 1000, 0, 100], dtype=np.uint16).reshape(2, 1, 2, 1) + offsets

    scale = spectral.fit_percentile_scale(samples, lo_q=25, hi_q=75)

    assert scale == {"lo": offsets.tolist(), "hi": (400 + offsets).tolist()}


def test_scale_to_8bit_clips_handles_constant_bands_and_floors():
    values = np.array([[0, 100, 101, 150, 200, 32768, 65535]], dtype=np.uint16)
    bands = np.repeat(values[..., None], 13, axis=-1)
    lo = [100] * 13
    hi = [200] * 13
    hi[1] = lo[1]
    lo[2], hi[2] = 0, 65535

    with np.errstate(all="raise"):
        scaled = spectral.scale_to_8bit(bands, {"lo": lo, "hi": hi})

    assert scaled.dtype == np.uint8
    assert scaled.shape == bands.shape
    np.testing.assert_array_equal(scaled[0, :, 0], [0, 0, 2, 127, 255, 255, 255])
    np.testing.assert_array_equal(scaled[0, :, 1], [0, 0, 0, 0, 0, 0, 0])
    np.testing.assert_array_equal(scaled[0, :, 2], [0, 0, 0, 0, 0, 127, 255])
    np.testing.assert_array_equal(scaled[0, :, -1], scaled[0, :, 0])


def test_synth_rgb_scales_b04_b03_b02_in_channel_order():
    bands = np.zeros((1, 2, 13), dtype=np.uint16)
    bands[0, 0, 1:4] = [1, 200, 500]
    bands[0, 1, 1:4] = [4, 125, 300]
    lo = [0] * 13
    hi = [10] * 13
    hi[1:4] = [4, 200, 500]
    lo[2:4] = [100, 300]

    rgb = spectral.synth_rgb(bands, {"lo": lo, "hi": hi})

    assert rgb.dtype == np.uint8
    assert rgb.shape == (1, 2, 3)
    np.testing.assert_array_equal(rgb, [[[255, 255, 63], [0, 63, 255]]])
