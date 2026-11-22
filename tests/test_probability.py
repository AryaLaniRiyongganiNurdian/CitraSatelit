import numpy as np
import pytest
from scipy.stats import binom, chi2
from sklearn.naive_bayes import GaussianNB

from src.core import probability


def test_slide_conditional_probability():
    assert probability.cond_prob(16 / 100, 40 / 100) == pytest.approx(0.40, abs=1e-9)
    with pytest.raises(ValueError):
        probability.cond_prob(0, 0)


@pytest.mark.parametrize("priors,likelihoods,evidence,target_idx,posterior", [
    pytest.param([0.8, 0.2], [0.01, 0.05], 0.018, 1, 0.010 / 0.018, id="produk-rusak"),
    pytest.param([0.60, 0.40], [0.10, 0.05], 0.08, 0, 0.75, id="transjakarta"),
    pytest.param([0.70, 0.30], [0.02, 0.08], 0.038, 1, 0.024 / 0.038, id="gateway"),
])
def test_slide_bayes_examples(priors, likelihoods, evidence, target_idx, posterior):
    assert probability.total_prob(priors, likelihoods) == pytest.approx(evidence, abs=1e-9)
    result, result_evidence = probability.bayes_posterior(priors, likelihoods)
    assert result_evidence == pytest.approx(evidence, abs=1e-9)
    assert result.sum() == pytest.approx(1, abs=1e-9)
    assert result[target_idx] == pytest.approx(posterior, abs=1e-9)


def test_discrete_bayes_joint_counts_and_laplace_smoothing():
    model = probability.discrete_bayes_fit([0, 0, 1, 0, 2], [0, 0, 0, 1, 1], 2, 3)
    np.testing.assert_array_equal(model["joint_counts"], [[2, 1, 0], [1, 0, 1]])
    np.testing.assert_allclose(model["prior"], [3 / 5, 2 / 5], rtol=0, atol=1e-9)
    np.testing.assert_allclose(
        model["likelihood"], [[3 / 6, 2 / 6, 1 / 6], [2 / 5, 1 / 5, 2 / 5]],
        rtol=0, atol=1e-9,
    )
    posterior, evidence = probability.bayes_posterior(model["prior"], model["likelihood"][:, 2])
    assert evidence == pytest.approx(0.26, abs=1e-9)
    np.testing.assert_allclose(posterior, [5 / 13, 8 / 13], rtol=0, atol=1e-9)


def test_chi2_uniform_statistic_and_wilson_hilferty():
    assert probability.chi2_uniform_stat([12, 8, 10, 10]) == pytest.approx(0.8, abs=1e-9)
    quantiles = [0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]
    for df in range(30, 256):
        x = chi2.ppf(quantiles, df)
        estimated = [probability.chi2_sf(stat, df) for stat in x]
        np.testing.assert_allclose(estimated, chi2.sf(x, df), rtol=0, atol=0.01)
    assert probability.chi2_sf(0, 255) == 1.0


def test_entropy_uniform_and_spike():
    assert probability.shannon_entropy(np.ones(256)) == pytest.approx(8.0, abs=1e-9)
    assert probability.shannon_entropy([0, 7, 0]) == pytest.approx(0.0, abs=1e-9)


def test_pearson_r_matches_corrcoef():
    x = np.array([1, 2, 4, 8], dtype=np.uint16)
    y = np.array([15, 10, 12, 2], dtype=np.uint16)
    assert probability.pearson_r(x, y) == pytest.approx(np.corrcoef(x, y)[0, 1], abs=1e-9)


@pytest.mark.parametrize("n,p", [(0, 0.3), (10, 0.8), (100, 0.01), (4096, 0.03), (8, 0), (8, 1)])
def test_binomial_pmf_matches_scipy(n, p):
    k = np.arange(-1, n + 2)
    np.testing.assert_allclose(probability.binom_pmf(n, k, p), binom.pmf(k, n, p), rtol=0, atol=1e-9)
    assert probability.binom_pmf(n, n, p) == pytest.approx(binom.pmf(n, n, p), abs=1e-9)


def test_geometric_pmf_and_slide_mean():
    assert probability.geometric_mean(0.2) == pytest.approx(5.0, abs=1e-9)
    k = np.arange(1, 6)
    np.testing.assert_allclose(probability.geometric_pmf(k, 0.2), 0.8 ** (k - 1) * 0.2, rtol=0, atol=1e-9)
    assert probability.geometric_pmf(1, 1.0) == 1.0
    assert probability.geometric_pmf(2, 1.0) == 0.0


@pytest.mark.parametrize("k", range(1, 6))
def test_chebyshev_bound_at_k_standard_deviations(k):
    assert probability.chebyshev_bound(4.0, r=k * 2.0) == pytest.approx(1 / k ** 2, abs=1e-9)


def test_gaussian_nb_matches_sklearn_on_separated_clusters():
    rng = np.random.default_rng(42)
    train = np.vstack([rng.normal(-4, 0.5, (40, 2)), rng.normal(4, 0.5, (40, 2))])
    labels = np.repeat([0, 1], 40)
    query = np.vstack([rng.normal(-4, 0.5, (10, 2)), rng.normal(4, 0.5, (10, 2))])
    model = probability.gaussian_nb_fit(train, labels, n_classes=2)
    expected = GaussianNB(var_smoothing=0.0).fit(train, labels)
    actual = probability.gaussian_nb_log_posterior(model, query)
    assert actual.shape == (20, 2)
    np.testing.assert_array_equal(actual.argmax(axis=1), np.repeat([0, 1], 10))
    np.testing.assert_allclose(actual, expected.predict_log_proba(query), rtol=0, atol=1e-9)
    np.testing.assert_allclose(np.exp(actual).sum(axis=1), 1, rtol=0, atol=1e-9)


def test_gaussian_nb_uses_variance_floor_and_stable_normalization():
    model = probability.gaussian_nb_fit([[0], [0], [2], [2]], [0, 0, 1, 1], 2, var_floor=1.0)
    actual = probability.gaussian_nb_log_posterior(model, [[0], [1], [1000]])
    expected_scores = -0.5 * (np.array([[0], [1], [1000]]) - np.array([0, 2])) ** 2
    expected = expected_scores - np.logaddexp.reduce(expected_scores, axis=1, keepdims=True)
    np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-9)
