import colorsys

import numpy as np
import pytest
from PIL import Image

from src.core import color


@pytest.fixture
def rgb_image():
    return np.random.default_rng(42).integers(0, 256, size=(31, 29, 3), dtype=np.uint8)


def test_rgb_to_gray_matches_pillow(rgb_image):
    expected = np.asarray(Image.fromarray(rgb_image).convert("L"))
    actual = color.rgb_to_gray(rgb_image)

    assert actual.shape == rgb_image.shape[:2]
    assert actual.dtype == np.uint8
    assert np.max(np.abs(actual.astype(np.int16) - expected)) <= 1


def test_rgb_to_gray_uses_spec_weights_and_rounds_half_up():
    rgb = np.array([[
        [0, 0, 0], [255, 0, 0], [0, 255, 0], [0, 0, 255],
        [255, 255, 255], [40, 20, 200],
    ]], dtype=np.uint8)

    np.testing.assert_array_equal(color.rgb_to_gray(rgb), [[0, 76, 150, 29, 255, 47]])


def test_rgb_to_hsv_matches_colorsys(rgb_image):
    reference = np.array([
        colorsys.rgb_to_hsv(*(pixel / 255))
        for pixel in rgb_image.reshape(-1, 3)
    ]).reshape(rgb_image.shape)
    reference[..., 0] = np.clip(np.floor(reference[..., 0] * 256), 0, 255)
    reference[..., 1:] = np.floor(reference[..., 1:] * 255 + 0.5)

    actual = color.rgb_to_hsv(rgb_image)

    assert actual.shape == rgb_image.shape
    assert actual.dtype == np.uint8
    np.testing.assert_allclose(actual, reference, rtol=0, atol=1)


def test_rgb_to_hsv_handles_boundaries_and_zero_chroma():
    rgb = np.array([
        [[255, 0, 0], [255, 255, 0], [0, 255, 0], [0, 255, 255], [0, 0, 255], [255, 0, 255]],
        [[0, 0, 0], [127, 127, 127], [255, 0, 1], [4, 3, 0], [4, 0, 3], [2, 1, 1]],
    ], dtype=np.uint8)
    expected = [
        [[0, 255, 255], [42, 255, 255], [85, 255, 255], [128, 255, 255], [170, 255, 255], [213, 255, 255]],
        [[0, 0, 0], [0, 0, 127], [255, 255, 255], [32, 255, 4], [224, 255, 4], [0, 128, 2]],
    ]

    with np.errstate(all="raise"):
        np.testing.assert_array_equal(color.rgb_to_hsv(rgb), expected)


def test_grid_cells_cover_an_uneven_image_in_row_major_order():
    cells = color.grid_cells(8, 11, 3)

    assert cells == [
        (0, 2, 0, 3), (0, 2, 3, 7), (0, 2, 7, 11),
        (2, 5, 0, 3), (2, 5, 3, 7), (2, 5, 7, 11),
        (5, 8, 0, 3), (5, 8, 3, 7), (5, 8, 7, 11),
    ]
    coverage = np.zeros((8, 11), dtype=np.uint8)
    for r0, r1, c0, c1 in cells:
        coverage[r0:r1, c0:c1] += 1
    np.testing.assert_array_equal(coverage, np.ones_like(coverage))
