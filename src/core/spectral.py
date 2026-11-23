import numpy as np


def _normalized_difference(bands_u16, positive_band, negative_band) -> np.ndarray:
    bands = np.asarray(bands_u16)
    positive = bands[..., positive_band].astype(np.float64)
    negative = bands[..., negative_band].astype(np.float64)
    denominator = positive + negative
    return np.divide(
        positive - negative,
        denominator,
        out=np.zeros_like(denominator),
        where=denominator != 0,
    )


def ndvi(bands_u16) -> np.ndarray:
    """Return the normalized difference of B08 and B04."""
    return _normalized_difference(bands_u16, 7, 3)


def ndwi(bands_u16) -> np.ndarray:
    """Return the normalized difference of B03 and B08."""
    return _normalized_difference(bands_u16, 2, 7)


def ndi_to_level(v) -> np.ndarray | np.uint8:
    """Map spectral index values from [-1, 1] to levels from 0 to 255."""
    clipped = np.clip(np.asarray(v, dtype=np.float64), -1, 1)
    return np.floor((clipped + 1) * 127.5 + 0.5).astype(np.uint8)


def fit_percentile_scale(samples_u16, lo_q=2, hi_q=98) -> dict:
    """Select the lower-ranked percentile value per band across all sample pixels."""
    samples = np.asarray(samples_u16)
    if samples.shape[-1:] != (13,) or samples.size == 0:
        raise ValueError("expected nonempty samples with 13 bands on the last axis")
    if not 0 <= lo_q <= hi_q <= 100:
        raise ValueError("percentiles must satisfy 0 <= lo_q <= hi_q <= 100")

    ordered = np.sort(samples.reshape(-1, 13), axis=0)
    last = len(ordered) - 1
    lo_idx = int(np.floor(lo_q / 100 * last))
    hi_idx = int(np.floor(hi_q / 100 * last))
    return {"lo": ordered[lo_idx].tolist(), "hi": ordered[hi_idx].tolist()}


def scale_to_8bit(bands_u16, scale) -> np.ndarray:
    """Apply the per-band scale, using zero for zero-width intervals."""
    bands = np.asarray(bands_u16, dtype=np.int32)
    lo, hi = np.asarray([scale["lo"], scale["hi"]])
    span = hi - lo
    numerator = (bands - lo) * 255
    scaled = np.floor_divide(numerator, span, out=np.zeros_like(numerator), where=span != 0)
    return np.clip(scaled, 0, 255).astype(np.uint8)


def synth_rgb(bands_u16, scale) -> np.ndarray:
    """Return scaled B04, B03 and B02 as red, green and blue."""
    return scale_to_8bit(bands_u16, scale)[..., [3, 2, 1]]
