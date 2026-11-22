import numpy as np
import pytest
import tifffile
from PIL import Image

from src.data.loader import load_rgb, load_tif


def test_load_rgb_returns_rgb_uint8(tmp_path):
    path = tmp_path / "Forest_1.jpg"
    Image.new("L", (64, 64), 75).save(path)

    rgb = load_rgb(path)

    assert rgb.shape == (64, 64, 3)
    assert rgb.dtype == np.uint8
    np.testing.assert_array_equal(rgb, np.full((64, 64, 3), 75, dtype=np.uint8))


@pytest.mark.parametrize("band_axis", [0, 1, 2])
def test_load_tif_moves_band_axis_and_preserves_values(tmp_path, band_axis):
    path = tmp_path / "Forest_1.tif"
    bands = np.arange(64 * 64 * 13, dtype=np.uint16).reshape(64, 64, 13)
    tifffile.imwrite(path, np.moveaxis(bands, -1, band_axis), photometric="minisblack")

    loaded = load_tif(path)

    assert loaded.shape == (64, 64, 13)
    assert loaded.dtype == np.uint16
    np.testing.assert_array_equal(loaded, bands)
