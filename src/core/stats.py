import numpy as np


def histogram_counts(x, bins: int, levels: int = 256) -> np.ndarray:
    """Count integer intensities using equal-width bins over [0, levels)."""
    pixels = np.asarray(x)
    if bins <= 0 or levels <= 0:
        raise ValueError("bins and levels must be positive")
    if pixels.size and not np.issubdtype(pixels.dtype, np.integer):
        raise ValueError("intensities must be integers")
    if np.any(pixels < 0) or np.any(pixels >= levels):
        raise ValueError("intensities must be in [0, levels)")

    indices = pixels.ravel().astype(np.int64) * bins // levels
    return np.bincount(indices, minlength=bins).astype(np.int64, copy=False)


def coarsen_counts(counts256, bins: int) -> np.ndarray:
    """Sum adjacent groups on the last axis of a full 256-bin histogram."""
    counts = np.asarray(counts256)
    if counts.shape[-1:] != (256,) or bins <= 0 or 256 % bins:
        raise ValueError("expected 256 counts and a bin count that divides 256")
    groups = counts.reshape(*counts.shape[:-1], bins, 256 // bins)
    return groups.sum(axis=-1, dtype=np.int64)


def counts_to_pmf(counts) -> np.ndarray:
    counts = np.asarray(counts, dtype=np.float64)
    total = np.sum(counts)
    if not np.isfinite(total) or total <= 0 or np.any(counts < 0):
        raise ValueError("counts must be nonnegative with a finite, positive total")
    return counts / total


def moments_from_counts(counts, values=None) -> dict:
    pmf = counts_to_pmf(counts)
    x = np.arange(pmf.size, dtype=np.float64) if values is None else np.asarray(values, dtype=np.float64)
    if x.shape != pmf.shape or x.ndim != 1:
        raise ValueError("counts and values must be matching vectors")

    mean = float(np.sum(x * pmf))
    variance = max(0.0, float(np.sum(x * x * pmf)) - mean * mean)
    std = float(np.sqrt(variance))
    degenerate = variance < 1e-12
    skewness = kurtosis = 0.0
    if not degenerate:
        standardized = (x - mean) / std
        skewness = float(np.sum(standardized ** 3 * pmf))
        kurtosis = float(np.sum(standardized ** 4 * pmf))

    return {
        "mean": mean,
        "variance": variance,
        "std": std,
        "skewness": skewness,
        "kurtosis": kurtosis,
        "degenerate": degenerate,
    }


def mgf_empirical(values, pmf, t) -> float | np.ndarray:
    x = np.asarray(values, dtype=np.float64)
    weights = np.asarray(pmf, dtype=np.float64)
    if x.ndim != 1 or x.shape != weights.shape:
        raise ValueError("values and pmf must be matching vectors")

    active = weights != 0
    t = np.asarray(t, dtype=np.float64)
    result = np.sum(np.exp(t[..., None] * x[active]) * weights[active], axis=-1)
    return float(result) if t.ndim == 0 else result


def mgf_check(counts256, h=1e-3) -> dict:
    pmf = counts_to_pmf(counts256)
    if pmf.shape != (256,) or not np.isfinite(h) or h <= 0:
        raise ValueError("expected 256 counts and a finite, positive step")

    x = np.arange(256, dtype=np.float64) / 255
    t = np.array([-h, 0.0, h])
    m = mgf_empirical(x, pmf, t)
    minus, center, plus = map(float, m)
    return {
        "t": t.tolist(),
        "m": m.tolist(),
        "m1_fd": (plus - minus) / (2 * h),
        "m1_exact": float(np.sum(x * pmf)),
        "m2_fd": (plus - 2 * center + minus) / h ** 2,
        "m2_exact": float(np.sum(x * x * pmf)),
        "scale_note": "Level intensitas diskala dengan x/255.",
    }


def _samples(x) -> np.ndarray:
    samples = np.asarray(x, dtype=np.float64)
    if samples.size == 0:
        raise ValueError("MLE requires at least one sample")
    return samples


def mle_gaussian(x) -> tuple[float, float]:
    samples = _samples(x)
    mean = np.mean(samples)
    variance = np.mean((samples - mean) ** 2)
    return float(mean), float(variance)


def mle_bernoulli(x) -> float:
    return float(np.mean(_samples(x)))


def mle_poisson(x) -> float:
    return float(np.mean(_samples(x)))


def mle_exponential(x) -> float:
    """Estimate the exponential scale (mean waiting time)."""
    return float(np.mean(_samples(x)))


def mle_geometric(x) -> float:
    samples = _samples(x)
    if np.any(samples < 1):
        raise ValueError("geometric samples start at 1")
    return float(samples.size / np.sum(samples))
