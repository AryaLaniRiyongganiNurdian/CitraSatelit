"""Shared offline evaluation protocol and artifact formatting."""
from dataclasses import dataclass

import numpy as np

from src.core.cbir import MODE_INFO, confusion_matrix, knn_predict, search_topk, zscore_fit
from src.core.stats import coarsen_counts
from src.data.loader import load_rgb, load_tif
from src.data.manifest import CLASSES

BINS = (8, 16, 32, 64, 128, 256)
COUNT_KEYS = {
    "gray": ("counts_gray",), "rgb": ("counts_rgb",), "hsv": ("counts_hsv",),
    "ms13": ("counts_ms",), "ndvi_ndwi": ("counts_ndvi", "counts_ndwi"),
    "ms13_idx": ("counts_ms", "counts_ndvi", "counts_ndwi"),
}


@dataclass
class Dataset:
    index: dict
    rows: list
    rgb_root: object
    tif_root: object
    clock: object
    seed: int = 42
    smoke: bool = False
    all_queries: bool = False

    @property
    def labels(self):
        return self.index["cls_idx"]

    @property
    def classes(self):
        return np.unique(self.labels)

    def rgb(self, i):
        return load_rgb(self.rgb_root / self.rows[i]["rgb_path"])

    def bands(self, i):
        return load_tif(self.tif_root / self.rows[i]["tif_path"])

    def split_rows(self, split, classes):
        return np.flatnonzero((self.index["split"] == split) & np.isin(self.labels, classes))

    def sample(self, split, classes, per_class):
        rng = np.random.default_rng(self.seed)
        selected = []
        for cls in classes:
            rows = self.split_rows(split, [cls])
            if per_class is not None:
                rows = rng.choice(rows, min(per_class, len(rows)), replace=False)
            selected.extend(sorted(rows))
        return np.array(selected, dtype=np.int64)


def features(index, mode, bins, db, queries, *, refit=False):
    if mode in COUNT_KEYS:
        def pmfs(selection):
            channels = []
            for key in COUNT_KEYS[mode]:
                counts = index[key][selection]
                coarse = coarsen_counts(counts, bins).reshape(len(selection), -1, bins).astype(np.float32)
                coarse /= coarse.sum(axis=-1, keepdims=True)
                channels.append(coarse)
            combined = np.concatenate(channels, axis=1)
            return (combined / combined.shape[1]).reshape(len(selection), -1)

        return pmfs(db), pmfs(queries)

    rows = index[f"feat_{mode}"]
    if refit:
        mean, std = zscore_fit(rows[db])
    else:
        mean, std = index[f"z_{mode}_mean"], index[f"z_{mode}_std"]
    return (rows[db] - mean) / std, (rows[queries] - mean) / std


def evaluate(data, mode, metric, bins, classes=None):
    refit = classes is not None
    if classes is None:
        classes = data.classes
    db = data.split_rows(0, classes)
    queries = data.sample(1, classes, None if data.all_queries else 50)
    database, query_features = features(data.index, mode, bins, db, queries, refit=refit)
    precision, predicted, timings = [], [], []
    labels = data.labels[db]
    actual = data.labels[queries]
    k = min(5, len(db))
    for query, target in zip(query_features, actual):
        start = data.clock()
        order, distances = search_topk(query, database, k, metric)
        timings.append(data.clock() - start)
        neighbors = labels[order]
        precision.append(float(np.mean(neighbors == target)))
        predicted.append(knn_predict(neighbors, distances))
    classes = np.asarray(classes)
    actual_ids = np.searchsorted(classes, actual)
    p_class = [float(np.mean(np.asarray(precision)[actual == cls])) for cls in classes]
    names = [CLASSES[cls] for cls in classes]
    payload = {
        "mode": mode, "metric": metric, "bins": bins if mode in COUNT_KEYS else None,
        "protocol": {"n_queries": len(queries), "db_size": len(db), "k": k,
                     "queries_per_class": int(np.bincount(actual_ids).max())},
        "classes": names, "per_class": [
            {"cls": name, "n_queries": int(np.count_nonzero(actual_ids == i)), "precision_at_k": value}
            for i, (name, value) in enumerate(zip(names, p_class))
        ],
        "macro_precision_at_k": float(np.mean(p_class)),
        "knn_accuracy": float(np.mean(np.asarray(predicted) == actual)),
        "confusion_matrix": confusion_matrix(actual_ids, np.searchsorted(classes, predicted), len(classes)).tolist(),
        "source": "precomputed",
    }
    return payload, float(np.mean(timings[:50]))


def combinations():
    for mode, info in MODE_INFO.items():
        for metric in info["metrics"]:
            for bins in BINS if mode == "rgb" else (32,):
                yield mode, metric, bins


def table(columns, rows):
    return {"columns": columns, "rows": rows}


def heatmap(title, entry):
    return {"kind": "heatmap", "title": title, "z": entry["confusion_matrix"],
            "x_labels": entry["classes"], "y_labels": entry["classes"]}


def result(title, description, data, tables, findings, *, charts=(), params=None, n_queries=None):
    return {"title": title, "description": description, "params": params or {},
            "dataset": {"n_images": len(data.rows), "n_queries": n_queries,
                        "note": "Fixture sintetis" if data.smoke else "EuroSAT lokal"},
            "tables": tables, "charts": list(charts), "findings": findings,
            "analysis_md": " ".join(findings)[:1500]}
