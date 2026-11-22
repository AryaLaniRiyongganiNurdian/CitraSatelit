import numpy as np

from src.core.color import grid_cells, rgb_to_gray, rgb_to_hsv
from src.core.spectral import ndi_to_level, ndvi, ndwi, scale_to_8bit, synth_rgb
from src.core.stats import coarsen_counts, counts_to_pmf, histogram_counts, mle_gaussian, moments_from_counts


_PMF_METRICS = ("euclid", "chi2", "intersection")
_MULTISPECTRAL_MODES = {"ms13", "ndvi_ndwi", "ms13_idx", "ms_mle"}
MODE_INFO = {
    mode: {
        "kind": kind,
        "metrics": metrics,
        "needs_multispectral": mode in _MULTISPECTRAL_MODES,
    }
    for kind, modes, metrics in (
        ("pmf", ("gray", "rgb", "hsv", "ms13", "ndvi_ndwi", "ms13_idx"), _PMF_METRICS),
        ("moment", ("grid2", "grid4", "mle", "ms_mle"), ("euclid",)),
    )
    for mode in modes
}


def _band_image(bands) -> np.ndarray:
    if bands is None:
        raise ValueError("multispectral modes require bands")
    image = np.asarray(bands)
    if image.ndim != 3 or image.shape[-1] != 13 or image.size == 0:
        raise ValueError("bands must be a nonempty (H, W, 13) image")
    return image


def _require_scale(scale):
    if scale is None:
        raise ValueError("8-bit band conversion requires a fitted scale")
    return scale


def _rgb_image(rgb, bands, scale) -> np.ndarray:
    if rgb is None:
        if bands is None:
            raise ValueError("RGB modes require rgb or bands with a fitted scale")
        return synth_rgb(_band_image(bands), _require_scale(scale))

    image = np.asarray(rgb)
    if image.ndim != 3 or image.shape[-1] != 3 or image.size == 0:
        raise ValueError("rgb must be a nonempty (H, W, 3) image")
    return image


def _channel_counts(image) -> np.ndarray:
    return np.stack([histogram_counts(channel, 256) for channel in np.moveaxis(image, -1, 0)])


def extract_counts(mode, *, rgb=None, bands=None, scale=None) -> np.ndarray:
    """Return full 256-level counts, one row per channel in multichannel modes."""
    if mode not in MODE_INFO or MODE_INFO[mode]["kind"] != "pmf":
        raise ValueError(f"not a PMF feature mode: {mode}")

    if not MODE_INFO[mode]["needs_multispectral"]:
        image = _rgb_image(rgb, bands, scale)
        if mode == "gray":
            return histogram_counts(rgb_to_gray(image), 256)
        if mode == "hsv":
            image = rgb_to_hsv(image)
        return _channel_counts(image)

    image = _band_image(bands)
    if mode == "ms13":
        return _channel_counts(scale_to_8bit(image, _require_scale(scale)))

    indices = np.stack([
        histogram_counts(ndi_to_level(ndvi(image)), 256),
        histogram_counts(ndi_to_level(ndwi(image)), 256),
    ])
    if mode == "ndvi_ndwi":
        return indices
    band_counts = _channel_counts(scale_to_8bit(image, _require_scale(scale)))
    return np.concatenate((band_counts, indices))


def counts_to_feature(counts, bins) -> np.ndarray:
    """Coarsen full counts and concatenate equally weighted channel PMFs."""
    coarse = coarsen_counts(counts, bins)
    if coarse.ndim == 1:
        return counts_to_pmf(coarse)
    if coarse.ndim != 2 or len(coarse) == 0:
        raise ValueError("expected a histogram or a nonempty matrix of channel histograms")

    pmfs = np.concatenate([counts_to_pmf(channel) for channel in coarse])
    return pmfs / len(coarse)


def extract_moment_feature(mode, *, rgb=None, bands=None, scale=None) -> np.ndarray:
    """Return grid moments or channel-wise Gaussian MLE features."""
    if mode not in MODE_INFO or MODE_INFO[mode]["kind"] != "moment":
        raise ValueError(f"not a moment feature mode: {mode}")

    if mode == "ms_mle":
        image = scale_to_8bit(_band_image(bands), _require_scale(scale))
    else:
        image = _rgb_image(rgb, bands, scale)

    feature = []
    if mode in ("mle", "ms_mle"):
        for channel in np.moveaxis(image, -1, 0):
            mean, variance = mle_gaussian(channel)
            feature.extend((mean, np.sqrt(variance)))
    else:
        grid_size = 2 if mode == "grid2" else 4
        h, w = image.shape[:2]
        if min(h, w) < grid_size:
            raise ValueError("grid moments require at least one pixel per cell")

        for r0, r1, c0, c1 in grid_cells(h, w, grid_size):
            for counts in _channel_counts(image[r0:r1, c0:c1]):
                moments = moments_from_counts(counts)
                feature.extend((moments["mean"], moments["std"], moments["skewness"]))

    return np.asarray(feature, dtype=np.float64)


def zscore_fit(train) -> tuple[np.ndarray, np.ndarray]:
    """Fit population mean and floored standard deviation on training rows."""
    features = np.asarray(train, dtype=np.float64)
    if features.ndim != 2 or features.size == 0:
        raise ValueError("train must be a nonempty feature matrix")

    mean = features.mean(axis=0)
    std = np.sqrt(np.mean((features - mean) ** 2, axis=0))
    return mean, np.maximum(std, 1e-8)


def zscore_apply(features, mean, std) -> np.ndarray:
    return (np.asarray(features) - mean) / std


def _distance_chunk(query, rows, metric) -> np.ndarray:
    if metric == "intersection":
        return 1 - np.minimum(query, rows).sum(axis=1)

    squared = rows - query
    np.square(squared, out=squared)
    if metric == "euclid":
        return np.sqrt(squared.sum(axis=1))

    denominator = rows + query
    positive = denominator > 0
    np.divide(squared, denominator, out=squared, where=positive)
    return np.sum(squared, axis=1, where=positive)


def distance_batch(query, database, metric, *, batch_size=2000) -> np.ndarray:
    """Compute one distance per database row, using 1 - I for intersection."""
    query = np.asarray(query)
    database = np.asarray(database)
    if query.ndim != 1 or database.ndim != 2 or database.shape[1] != query.size:
        raise ValueError("query and database must have the same feature dimension")
    if metric not in _PMF_METRICS:
        raise ValueError(f"unknown metric: {metric}")
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    dtype = np.result_type(query.dtype, database.dtype, np.float32)
    query = query.astype(dtype, copy=False)
    distances = np.empty(len(database), dtype=dtype)
    for start in range(0, len(database), batch_size):
        stop = start + batch_size
        rows = database[start:stop].astype(dtype, copy=False)
        distances[start:stop] = _distance_chunk(query, rows, metric)
    return distances


def search_topk(query, database, k, metric, *, query_index=None) -> tuple[np.ndarray, np.ndarray]:
    """Return sorted database indices and distances, excluding the supplied query index."""
    if k <= 0:
        raise ValueError("k must be positive")

    distances = distance_batch(query, database, metric)
    indices = np.arange(len(distances))
    if query_index is not None:
        indices = indices[indices != query_index]

    ranking = np.argsort(distances[indices], kind="stable")[:k]
    selected = indices[ranking]
    return selected, distances[selected]


def precision_at_k(query_class, neighbor_classes) -> float:
    labels = np.asarray(neighbor_classes)
    if labels.ndim != 1 or labels.size == 0:
        raise ValueError("expected at least one neighbor class")
    return float(np.mean(labels == query_class))


def knn_predict(neighbor_classes, distances) -> int:
    """Vote among the selected neighbors, using total distance to break vote ties."""
    labels = np.asarray(neighbor_classes)
    distances = np.asarray(distances, dtype=np.float64)
    if labels.ndim != 1 or labels.size == 0 or labels.shape != distances.shape:
        raise ValueError("expected matching nonempty neighbor classes and distances")

    classes, votes = np.unique(labels, return_counts=True)
    contenders = classes[votes == votes.max()]
    totals = np.array([distances[labels == label].sum() for label in contenders])
    winners = contenders[totals == totals.min()]
    if len(winners) != 1:
        raise ValueError("kNN votes and total distances are tied; see docs/open-questions.md")
    return int(winners[0])


def confusion_matrix(y_true, y_pred, n_classes) -> np.ndarray:
    true = np.asarray(y_true, dtype=np.int64)
    predicted = np.asarray(y_pred, dtype=np.int64)
    if true.ndim != 1 or true.shape != predicted.shape or n_classes <= 0:
        raise ValueError("expected matching label vectors and a positive class count")
    if np.any((true < 0) | (true >= n_classes) | (predicted < 0) | (predicted >= n_classes)):
        raise ValueError("class labels must be in [0, n_classes)")

    cell_indices = true * n_classes + predicted
    return np.bincount(cell_indices, minlength=n_classes ** 2).reshape(n_classes, n_classes)
