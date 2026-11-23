import asyncio
from time import perf_counter

import numpy as np
from fastapi import APIRouter, Request

from src.api import schemas as s
from src.api.errors import ApiError, RESPONSES
from src.api.routers.cbir import check_k, validate_metric
from src.core import cbir
from src.data.manifest import CLASSES
from src.experiments.common import COUNT_KEYS, features

router = APIRouter(prefix="/live", responses=RESPONSES)


def limit():
    return ApiError("LIVE_LIMIT_EXCEEDED", "Percobaan live melebihi batas.")


def _protocol(data, db_per_class, queries_per_class, seed):
    db_size = 60 if db_per_class is None else db_per_class
    query_size = 10 if queries_per_class is None else queries_per_class
    if not (5 <= db_size <= 60 and 1 <= query_size <= 10):
        raise limit()
    if not data.ids:
        raise ApiError("NOT_PRECOMPUTED", "Indeks belum tersedia.")
    labels = data.index["cls_idx"]
    splits = data.index["split"]
    classes = sorted(set(labels[splits == 0]) & set(labels[splits == 1]))
    if not classes:
        raise ApiError("NOT_PRECOMPUTED", "Data latih dan uji belum tersedia.")
    rng = np.random.default_rng(data.settings.seed if seed is None else seed)

    def select(split, cap):
        selected = []
        for cls in classes:
            indices = np.flatnonzero((labels == cls) & (splits == split))
            selected.extend(sorted(rng.choice(indices, min(len(indices), cap), replace=False)))
        return np.asarray(selected)
    return classes, select(0, db_size), select(1, query_size), query_size


def _evaluate(data, req, bins_list):
    started = perf_counter()
    validate_metric(req.mode, req.metric)
    classes, db, queries, query_size = _protocol(data, req.db_per_class, req.queries_per_class, req.seed)
    k_input = getattr(req, "k", None)
    k = min(check_k(5 if k_input is None else k_input), len(db))
    labels = data.index["cls_idx"]
    true = np.searchsorted(classes, labels[queries])
    names = [CLASSES[i] for i in classes]
    outputs = []
    for bins in bins_list:
        db_features, query_features = features(data.index, req.mode, bins, db, queries, refit=True)
        precisions, predictions = [], []
        search_start = perf_counter()
        for query, label in zip(query_features, labels[queries]):
            if perf_counter() - started > 20:
                raise limit()
            order, distances = cbir.search_topk(query, db_features, k, req.metric)
            neighbors = labels[db[order]]
            precisions.append(cbir.precision_at_k(label, neighbors))
            predictions.append(cbir.knn_predict(neighbors, distances))
        search_ms = (perf_counter() - search_start) * 1000
        predicted = np.searchsorted(classes, predictions)
        per_class = [dict(cls=name, n_queries=int(np.count_nonzero(true == i)),
                          precision_at_k=float(np.mean(np.asarray(precisions)[true == i])))
                     for i, name in enumerate(names)]
        payload = dict(mode=req.mode, bins=bins if req.mode in COUNT_KEYS else None, metric=req.metric,
                       protocol=dict(n_queries=len(queries), db_size=len(db), queries_per_class=query_size, k=k),
                       classes=names, per_class=per_class, macro_precision_at_k=float(np.mean(
                           [item["precision_at_k"] for item in per_class])),
                       knn_accuracy=float(np.mean(true == predicted)),
                       confusion_matrix=cbir.confusion_matrix(true, predicted, len(classes)).tolist(),
                       source="live", elapsed_ms=search_ms)
        outputs.append((payload, db_features.shape[1], search_ms / len(queries)))
    return outputs


async def _bounded(data, req, bins):
    try:
        return await asyncio.wait_for(asyncio.to_thread(_evaluate, data, req, bins), timeout=20)
    except TimeoutError as exc:
        raise limit() from exc


@router.post("/cbir", response_model=s.EvaluateResponse, response_model_exclude_unset=True)
async def live_cbir(req: s.LiveCbirRequest, request: Request):
    return (await _bounded(request.app.state.data, req, [req.bins]))[0][0]


@router.post("/bins", response_model=s.LiveBinsResponse, response_model_exclude_unset=True)
async def live_bins(req: s.LiveBinsRequest, request: Request):
    if req.mode not in COUNT_KEYS or not 1 <= len(req.bins_list) <= 6:
        raise ApiError("INVALID_PARAM", "Pilih mode histogram dan satu sampai enam ukuran bin.")
    results = await _bounded(request.app.state.data, req, req.bins_list)
    points = [dict(bins=entry["bins"], dim=dim, macro_precision_at_k=entry["macro_precision_at_k"],
                   search_ms_per_query=elapsed) for entry, dim, elapsed in results]
    return {"points": points, "chart": {
        "kind": "line", "title": "Precision@k menurut bin", "x": req.bins_list,
        "series": [{"name": "Precision@k", "y": [point["macro_precision_at_k"] for point in points]}],
    }}
