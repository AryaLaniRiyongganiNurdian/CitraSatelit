from pathlib import Path

import numpy as np
import tifffile
from PIL import Image


def load_rgb(path: str | Path) -> np.ndarray:
    """Load a JPEG as an RGB uint8 array."""
    with Image.open(path) as image:
        return np.array(image.convert("RGB"), dtype=np.uint8)


def load_tif(path: str | Path) -> np.ndarray:
    """Load a multispectral TIFF with the 13 bands on the last axis."""
    bands = tifffile.imread(path)
    band_axes = [axis for axis, size in enumerate(bands.shape) if size == 13]
    if bands.ndim != 3 or len(band_axes) != 1:
        raise ValueError(f"{path}: expected one 13-band axis in a 3D TIFF, got {bands.shape}")

    if bands.dtype.kind != "u" or bands.dtype.itemsize != 2:
        raise ValueError(f"{path}: expected a uint16 TIFF, got {bands.dtype}")

    return np.moveaxis(bands, band_axes[0], -1).astype(np.uint16, copy=False)
