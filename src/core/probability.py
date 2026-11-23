from math import erf

import numpy as np

from src.core.stats import counts_to_pmf


def cond_prob(p_a_and_b, p_b) -> float:
    if not p_b > 0:
        raise ValueError("P(B) must be positive")
    return float(p_a_and_b / p_b)


def _joint_probabilities(priors, likelihoods) -> np.ndarray:
    priors = np.asarray(priors, dtype=np.float64)
    likelihoods = np.asarray(likelihoods, dtype=np.float64)
    if priors.ndim != 1 or priors.shape != likelihoods.shape:
        raise ValueError("priors and likelihoods must be matching vectors")
    return priors * likelihoods


def total_prob(priors, likelihoods) -> float:
    return float(np.sum(_joint_probabilities(priors, likelihoods)))


def bayes_posterior(priors, likelihoods) -> tuple[np.ndarray, float]:
    joint = _joint_probabilities(priors, likelihoods)
    evidence = float(np.sum(joint))
    if not evidence > 0:
        raise ValueError("evidence must have positive probability")
    return joint / evidence, evidence


def _class_labels(y, n_classes, n_samples) -> np.ndarray:
    labels = np.asarray(y)
    if n_classes <= 0 or n_samples == 0 or labels.shape != (n_samples,):
        raise ValueError("expected one class label per sample and at least one class and sample")
    if not np.issubdtype(labels.dtype, np.integer) or np.any((labels < 0) | (labels >= n_classes)):
        raise ValueError("labels must be integers in [0, n_classes)")
    return labels.astype(np.int64, copy=False)


def discrete_bayes_fit(evidence_bins, y, n_classes, levels, alpha=1.0) -> dict:
    bins = np.asarray(evidence_bins)
    if bins.ndim != 1 or not np.issubdtype(bins.dtype, np.integer):
        raise ValueError("evidence bins must be an integer vector")
    if levels <= 0 or np.any((bins < 0) | (bins >= levels)):
        raise ValueError("evidence bins must be in [0, levels)")
    if not np.isfinite(alpha) or alpha < 0:
        raise ValueError("alpha must be finite and nonnegative")

    labels = _class_labels(y, n_classes, bins.size)
    indices = labels * levels + bins.astype(np.int64, copy=False)
    joint_counts = np.bincount(indices, minlength=n_classes * levels).reshape(n_classes, levels)
    class_counts = joint_counts.sum(axis=1)
    denominator = class_counts + alpha * levels
    if np.any(denominator == 0):
        raise ValueError("classes without evidence require positive smoothing")
    return {
        "prior": class_counts / bins.size,
        "likelihood": (joint_counts + alpha) / denominator[:, None],
        "joint_counts": joint_counts,
    }


def gaussian_nb_fit(X, y, n_classes, var_floor=1e-6) -> dict:
    samples = np.asarray(X, dtype=np.float64)
    if samples.ndim != 2 or samples.shape[1] == 0:
        raise ValueError("X must be a matrix with at least one feature")
    if not np.isfinite(var_floor) or var_floor <= 0:
        raise ValueError("var_floor must be finite and positive")

    labels = _class_labels(y, n_classes, samples.shape[0])
    class_counts = np.bincount(labels, minlength=n_classes)
    means = np.zeros((n_classes, samples.shape[1]))
    variances = np.full_like(means, var_floor)
    for cls in np.flatnonzero(class_counts):
        group = samples[labels == cls]
        means[cls] = np.mean(group, axis=0)
        variances[cls] = np.maximum(np.mean((group - means[cls]) ** 2, axis=0), var_floor)

    return {"prior": class_counts / len(samples), "mean": means, "variance": variances}


def gaussian_nb_log_posterior(model, X) -> np.ndarray:
    samples = np.asarray(X, dtype=np.float64)
    means, variances, priors = model["mean"], model["variance"], model["prior"]
    if samples.ndim != 2 or samples.shape[1] != means.shape[1]:
        raise ValueError("X must have the same feature count as the fitted model")

    log_prior = np.full_like(priors, -np.inf)
    np.log(priors, where=priors > 0, out=log_prior)
    deviations = samples[:, None, :] - means
    log_density = -0.5 * np.sum(
        np.log(2 * np.pi) + np.log(variances) + deviations ** 2 / variances, axis=-1,
    )
    scores = log_density + log_prior
    shifted = scores - np.max(scores, axis=1, keepdims=True)
    return shifted - np.log(np.sum(np.exp(shifted), axis=1, keepdims=True))


def chi2_uniform_stat(counts) -> float:
    counts = np.asarray(counts, dtype=np.float64)
    total = np.sum(counts)
    if not np.isfinite(total) or total <= 0 or np.any(counts < 0):
        raise ValueError("counts must be nonnegative with a finite, positive total")
    expected = total / counts.size
    return float(np.sum((counts - expected) ** 2 / expected))


def chi2_sf(x, df) -> float:
    """Wilson-Hilferty approximation to the chi-square survival function."""
    if not df > 0:
        raise ValueError("df must be positive")
    if x <= 0:
        return 1.0

    correction = 2 / (9 * df)
    z = (np.cbrt(x / df) - (1 - correction)) / np.sqrt(correction)
    return (1 - erf(z / np.sqrt(2))) / 2


def shannon_entropy(counts) -> float:
    pmf = counts_to_pmf(counts)
    positive = pmf[pmf > 0]
    return float(-np.sum(positive * np.log2(positive)))


def pearson_r(x, y) -> float:
    x = np.asarray(x, dtype=np.float64).ravel()
    y = np.asarray(y, dtype=np.float64).ravel()
    if x.shape != y.shape or x.size == 0:
        raise ValueError("x and y must have the same positive number of samples")

    x = x - np.mean(x)
    y = y - np.mean(y)
    denominator = np.sqrt(np.sum(x * x)) * np.sqrt(np.sum(y * y))
    if denominator == 0:
        return float("nan")
    return float(np.clip(np.sum(x * y) / denominator, -1, 1))


def binom_pmf(n, k, p):
    if n < 0 or not 0 <= p <= 1:
        raise ValueError("n must be nonnegative and p must be in [0, 1]")

    outcomes = np.asarray(k)
    pmf = np.zeros(outcomes.shape, dtype=np.float64)
    if p == 0 or p == 1:
        pmf[...] = outcomes == (n if p == 1 else 0)
    else:
        supported = (outcomes >= 0) & (outcomes <= n) & (outcomes == np.floor(outcomes))
        hits = outcomes[supported].astype(np.int64)
        log_factorials = np.concatenate(([0.0], np.cumsum(np.log(np.arange(1, n + 1)))))
        log_binomial = log_factorials[n] - log_factorials[hits] - log_factorials[n - hits]
        pmf[supported] = np.exp(log_binomial + hits * np.log(p) + (n - hits) * np.log1p(-p))
    return float(pmf) if pmf.ndim == 0 else pmf


def geometric_pmf(k, p):
    if not 0 <= p <= 1:
        raise ValueError("p must be in [0, 1]")
    outcomes = np.asarray(k, dtype=np.float64)
    supported = (outcomes >= 1) & np.isfinite(outcomes) & (outcomes == np.floor(outcomes))
    pmf = np.zeros(outcomes.shape, dtype=np.float64)
    pmf[supported] = p * (1 - p) ** (outcomes[supported] - 1)
    return float(pmf) if pmf.ndim == 0 else pmf


def geometric_mean(p):
    if not 0 <= p <= 1:
        raise ValueError("p must be in [0, 1]")
    return float("inf") if p == 0 else float(1 / p)


def chebyshev_bound(var, r):
    if not var >= 0 or not r > 0:
        raise ValueError("variance must be nonnegative and r must be positive")
    return float(var / r / r)
