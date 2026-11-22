import numpy as np

from src.core.cbir import counts_to_feature, extract_counts
from src.experiments.common import BINS, result, table


def run(data, evaluation):
    rng = np.random.default_rng(data.seed)
    selection = rng.choice(len(data.rows), min(200, len(data.rows)), replace=False)
    images = [data.rgb(i) for i in selection]
    rows = []
    for bins in BINS:
        entry, search_seconds = evaluation("rgb", "chi2", bins)
        start = data.clock()
        for image in images:
            counts_to_feature(extract_counts("rgb", rgb=image), bins)
        extract_ms = (data.clock() - start) * 1000 / len(images)
        rows.append([bins, bins * 3, entry["macro_precision_at_k"], extract_ms, search_seconds * 1000])
    best = max(rows, key=lambda row: row[2])
    chart = {"kind": "line", "title": "Precision@5 menurut jumlah bin", "x": list(BINS),
             "series": [{"name": "Precision@5", "y": [row[2] for row in rows]}]}
    return result("C1 — Pengaruh bin", "Pencarian histogram RGB dengan chi-square.", data,
                  [table(["Bin", "Dimensi", "P@5", "Ekstraksi ms", "Pencarian ms"], rows)],
                  [f"Bin {best[0]} mencapai P@5 tertinggi sebesar {best[2]:.4f}."],
                  charts=[chart], params={"bins": list(BINS), "metric": "chi2"},
                  n_queries=entry["protocol"]["n_queries"])
