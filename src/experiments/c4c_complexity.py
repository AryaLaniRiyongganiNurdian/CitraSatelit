import numpy as np

from src.core.cbir import search_topk
from src.experiments.common import features, result, table


def run(data):
    rng = np.random.default_rng(data.seed)
    n = len(data.rows)
    sizes = [10, 20, n] if data.smoke else [100, 300, 1000, 3000, 10000, 27000]
    order = rng.permutation(n)
    query_ids = data.sample(1, data.classes, 5)
    rows = []
    for size in sizes:
        indices = order[:size]
        database, queries = features(data.index, "rgb", 32, indices, query_ids)
        start = data.clock()
        for query in queries:
            search_topk(query, database, 5, "chi2")
        milliseconds = (data.clock() - start) * 1000 / len(queries)
        ids = data.index["ids"][indices].tolist()
        targets = rng.choice(ids, size=1000)
        comparisons = float(np.mean([ids.index(target) + 1 for target in targets]))
        rows.append([size, milliseconds, comparisons, (size + 1) / 2])

    x, y, _, _ = np.asarray(rows).T
    dx, dy = x - x.mean(), y - y.mean()
    slope = float(np.sum(dx * dy) / np.sum(dx ** 2))
    residuals = dy - slope * dx
    total = float(np.sum(dy ** 2))
    r_squared = 1 - float(np.sum(residuals ** 2)) / total if total else None
    charts = [{"kind": "line", "title": "Waktu pencarian", "x": sizes,
               "series": [{"name": "ms/query", "y": y.tolist()}]}]
    findings = [f"Pada N={sizes[-1]}, rata-rata scan {rows[-1][2]:.1f} perbandingan; teori {rows[-1][3]:.1f}."]
    if r_squared is not None:
        findings.append(f"Regresi waktu memberi kemiringan {slope:.6f} ms/citra dan R²={r_squared:.4f}.")
    return result("C4c — Kompleksitas", "Skala waktu CBIR dan scan pencocokan eksak.", data,
                  [table(["Database", "ms/query", "Scan empiris", "Scan teori"], rows),
                   table(["Kemiringan", "R²"], [[slope, r_squared]])],
                  findings, charts=charts, params={"trials": 1000, "sizes": sizes},
                  n_queries=len(query_ids))
