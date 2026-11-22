from time import perf_counter

import numpy as np
from fastapi import APIRouter, Request

from src.api import schemas as s
from src.api.errors import ApiError, RESPONSES
from src.api.inspector import explain
from src.core import cbir, probability, stats
from src.data.manifest import CLASSES
from src.experiments.common import COUNT_KEYS, features

router = APIRouter(prefix="/cbir", responses=RESPONSES)
FORMULA = {
    "euclid": r"d=\sqrt{\sum_i(p_i-q_i)^2}",
    "chi2": r"d=\sum_{p_i+q_i>0}\frac{(p_i-q_i)^2}{p_i+q_i}",
    "intersection": r"d=1-\sum_i\min(p_i,q_i)",
}


def validate_metric(mode, metric):
    if metric not in cbir.MODE_INFO[mode]["metrics"]:
        raise ApiError("INVALID_PARAM", "Metrik tidak berlaku untuk mode ini.", field="metric")


def counts_for(data, key, mode):
    if key in data.positions:
        parts = [np.atleast_2d(data.index[name][data.positions[key]]) for name in COUNT_KEYS[mode]]
        return np.concatenate(parts)
    bands = data.bands(key) if cbir.MODE_INFO[mode]["needs_multispectral"] else None
    return cbir.extract_counts(mode, rgb=data.rgb(key), bands=bands, scale=data.scale)


def moment_for(data, key, mode):
    if key in data.positions:
        return data.index[f"feat_{mode}"][data.positions[key]]
    bands = data.bands(key) if cbir.MODE_INFO[mode]["needs_multispectral"] else None
    return cbir.extract_moment_feature(mode, rgb=data.rgb(key), bands=bands, scale=data.scale)


def query_feature(data, key, mode, bins, normalized=True):
    if mode in COUNT_KEYS:
        return cbir.counts_to_feature(counts_for(data, key, mode), bins)
    vector = moment_for(data, key, mode)
    if normalized:
        return cbir.zscore_apply(vector, data.index[f"z_{mode}_mean"], data.index[f"z_{mode}_std"])
    return vector


def search_database(data, mode, bins):
    with data.feature_lock:
        key = (mode, bins)
        if data.cached_features is None or key != data.cached_features[0]:
            indices = np.arange(len(data.ids))
            matrix, _ = features(data.index, mode, bins, indices, indices[:1])
            data.cached_features = key, matrix
        return data.cached_features[1]


def rank_hits(data, query, cls, mode, metric, bins, k, database="all", excluded=None):
    if not data.ids:
        raise ApiError("NOT_PRECOMPUTED", "Indeks belum tersedia.")
    validate_metric(mode, metric)
    matrix = search_database(data, mode, bins)
    indices = np.arange(len(data.ids)) if database == "all" else np.flatnonzero(data.index["split"] == 0)
    local_index = None
    if excluded is not None:
        position = np.searchsorted(indices, excluded)
        if position < len(indices) and indices[position] == excluded:
            local_index = int(position)
    rows = matrix if len(indices) == len(matrix) else matrix[indices]
    order, distances = cbir.search_topk(query.astype(matrix.dtype), rows, k, metric, query_index=local_index)
    hits = []
    for rank, (i, distance) in enumerate(zip(indices[order], distances), 1):
        meta = data.meta(data.ids[i])
        hits.append(dict(rank=rank, id=meta["id"], cls=meta["cls"], split=meta["split"],
                         distance=float(distance), similarity=float(1 - distance) if metric == "intersection" else None,
                         same_class=None if cls is None else cls == meta["cls"], thumb_url=meta["thumb_url"]))
    precision = float(np.mean([hit["same_class"] for hit in hits])) if hits and cls is not None else None
    return hits, precision, len(indices) - int(local_index is not None)


def check_k(k):
    if k < 1:
        raise ApiError("INVALID_PARAM", "k harus minimal satu.", field="k")
    return k


@router.post("/features", response_model=s.FeaturesResponse, response_model_exclude_unset=True)
def cbir_features(req: s.FeaturesRequest, request: Request):
    data = request.app.state.data
    start = perf_counter()
    image = data.meta(req.image_id)
    channels = []
    if req.mode in COUNT_KEYS:
        raw = np.atleast_2d(counts_for(data, req.image_id, req.mode))
        vector = cbir.counts_to_feature(raw, req.bins)
        for i, counts in enumerate(raw):
            coarse = stats.coarsen_counts(counts, req.bins)
            moments = stats.moments_from_counts(counts)
            channels.append(dict(name=f"Kanal {i+1}", counts=coarse.tolist(),
                                 pmf=stats.counts_to_pmf(coarse).tolist(), moments=moments,
                                 mle=dict(mu_hat=moments["mean"], sigma2_hat=moments["variance"]),
                                 mgf=stats.mgf_check(counts)))
        ids = ("counts", "pmf", "moments", "mle", "mgf")
    else:
        vector = moment_for(data, req.image_id, req.mode)
        ids = ("moment-table",)
    return dict(image=image, mode=req.mode, bins=req.bins, kind=cbir.MODE_INFO[req.mode]["kind"],
                dim=len(vector), channels=channels, vector_head=vector[:16].tolist(),
                elapsed_ms=(perf_counter() - start) * 1000, inspector=explain("Ekstraksi fitur", *ids))


@router.post("/search", response_model=s.SearchResponse, response_model_exclude_unset=True)
def search(req: s.SearchRequest, request: Request):
    data = request.app.state.data
    k = check_k(5 if req.k is None else req.k)
    database = req.database or "all"
    image = data.meta(req.image_id)
    validate_metric(req.mode, req.metric)
    start = perf_counter()
    query = query_feature(data, req.image_id, req.mode, req.bins)
    feature_ms = (perf_counter() - start) * 1000
    start = perf_counter()
    hits, precision, size = rank_hits(data, query, image["cls"], req.mode, req.metric, req.bins, k, database,
                                     data.positions.get(req.image_id))
    detail = {"metric-formula": {"latex_template": FORMULA[req.metric]}}
    if hits:
        other = query_feature(data, hits[0]["id"], req.mode, req.bins)
        distance = hits[0]["distance"]
        detail["metric-numbers"] = {
            "values": {"d": distance, "p_0": float(query[0]), "q_0": float(other[0])},
            "latex_substituted": rf"p_0={query[0]:.6f},\quad q_0={other[0]:.6f},\quad d={distance:.6f}",
        }
        if precision is not None:
            detail["precision"] = {"values": {"precision_at_k": precision}}
    return dict(query=image, mode=req.mode, bins=req.bins, metric=req.metric, k=k, database=database, db_size=size,
                hits=hits, precision_at_k=precision, elapsed_ms=dict(feature=feature_ms, search=(perf_counter()-start)*1000),
                inspector=explain("Pencarian CBIR", "metric-formula", "metric-numbers", "precision", detail=detail))


def _train(data):
    if not data.ids:
        raise ApiError("NOT_PRECOMPUTED", "Indeks latih belum tersedia.")
    train = np.flatnonzero(data.index["split"] == 0)
    classes, labels = np.unique(data.index["cls_idx"][train], return_inverse=True)
    return train, [CLASSES[i] for i in classes], labels


def _unit_probabilities(probs):
    scaled = probs * 1_000_000
    whole = np.floor(scaled).astype(np.int64)
    remaining = 1_000_000 - whole.sum()
    order = np.argsort(-(scaled - whole), kind="stable")
    whole[order[:remaining]] += 1
    return whole / 1_000_000


@router.post("/bayes", response_model=s.BayesResponse, response_model_exclude_unset=True)
def bayes(req: s.BayesRequest, request: Request):
    data = request.app.state.data
    image = data.meta(req.image_id)
    levels = 8 if req.levels is None else req.levels
    alpha = 1 if req.alpha is None else req.alpha
    if not 4 <= levels <= 16 or alpha <= 0:
        raise ApiError("INVALID_PARAM", "Gunakan levels 4 sampai 16 dan alpha positif.")
    channel = req.evidence.removeprefix("mean_")
    mode = "gray" if channel == "gray" else "ndvi_ndwi"
    offset = int(channel == "ndwi")
    counts = np.atleast_2d(counts_for(data, req.image_id, mode))[offset]
    x = np.arange(256, dtype=np.int64)
    value = float((counts @ x) / counts.sum())
    bin_id = int(value * levels // 256)
    train, names, labels = _train(data)
    histogram = data.index[f"counts_{channel}"][train]
    evidence_bins = (histogram @ x * levels) // (histogram.sum(axis=1, dtype=np.int64) * 256)
    model = probability.discrete_bayes_fit(evidence_bins, labels, len(names), levels, alpha)
    prior, likelihood = model["prior"], model["likelihood"][:, bin_id]
    posterior, evidence = probability.bayes_posterior(prior, likelihood)
    winner = int(posterior.argmax())
    rows = [dict(cls=name, prior=float(prior[i]), likelihood=float(likelihood[i]),
                 joint=float(prior[i]*likelihood[i]), posterior=float(p))
            for i, (name, p) in enumerate(zip(names, _unit_probabilities(posterior)))]
    return dict(image=image, evidence=req.evidence, levels=levels, evidence_value=value, evidence_bin=bin_id,
                evidence_total=evidence, rows=rows, predicted=names[winner],
                conditional_example=dict(event_a=names[winner], event_b=f"bin {bin_id}",
                                         p_a_and_b=rows[winner]["joint"], p_b=evidence,
                                         p_a_given_b=rows[winner]["posterior"]),
                inspector=explain("Bayes diskret", "prior", "likelihood", "evidence", "posterior", "conditional",
                                  detail={"evidence": {"values": {"peluang": evidence, "bin": bin_id}}}))


@router.post("/gnb", response_model=s.GnbResponse, response_model_exclude_unset=True)
def gnb(req: s.GnbRequest, request: Request):
    data = request.app.state.data
    image = data.meta(req.image_id)
    query = moment_for(data, req.image_id, req.mode)
    train, names, labels = _train(data)
    model = probability.gaussian_nb_fit(data.index[f"feat_{req.mode}"][train], labels, len(names))
    priors, var = model["prior"], model["variance"]
    logits = np.log(priors) - 0.5 * np.sum(np.log(2 * np.pi * var) + (query-model["mean"])**2 / var, axis=1)
    posterior = _unit_probabilities(np.exp(probability.gaussian_nb_log_posterior(model, [query])[0]))
    return dict(image=image, mode=req.mode, predicted=names[int(logits.argmax())],
                rows=[dict(cls=name, prior=float(prior), log_posterior_unnorm=float(score), posterior=float(post))
                      for name, prior, score, post in zip(names, priors, logits, posterior)],
                inspector=explain("Gaussian Naive Bayes", "mle-per-class", "log-likelihood", "posterior"))


@router.get("/evaluate", response_model=s.EvaluateResponse, response_model_exclude_unset=True)
def evaluate(request: Request, mode: s.FeatureMode, metric: s.Metric, bins: int = 32):
    data = request.app.state.data
    validate_metric(mode, metric)
    if bins not in (8, 16, 32, 64, 128, 256):
        raise ApiError("INVALID_PARAM", "Jumlah bin tidak valid.", field="bins")
    key = f"{mode}:{metric}:{32 if mode not in COUNT_KEYS else bins}"
    if key not in data.cache:
        raise ApiError("NOT_PRECOMPUTED", "Evaluasi belum tersedia.", available=sorted(data.cache))
    return data.cache[key]
