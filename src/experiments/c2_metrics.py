import numpy as np

from src.core.cbir import confusion_matrix
from src.core.probability import discrete_bayes_fit, gaussian_nb_fit, gaussian_nb_log_posterior
from src.data.manifest import CLASSES
from src.experiments.common import heatmap, result, table


def run(data, evaluation):
    classes = data.classes
    methods = [("rgb", "euclid"), ("rgb", "chi2"), ("rgb", "intersection"), ("mle", "euclid")]
    rows, per_class, charts = [], [], []
    for mode, metric in methods:
        entry, _ = evaluation(mode, metric, 32)
        name = f"{mode} {metric}"
        rows.append([name, entry["macro_precision_at_k"], entry["knn_accuracy"]])
        per_class.append([name, *(item["precision_at_k"] for item in entry["per_class"])])
        if metric == "chi2":
            charts.append(heatmap(name, entry))

    db = data.split_rows(0, classes)
    queries = data.sample(1, classes, None if data.all_queries else 50)
    labels = np.searchsorted(classes, data.labels)
    for mode in ("mle", "grid2"):
        features = data.index[f"feat_{mode}"]
        model = gaussian_nb_fit(features[db], labels[db], len(classes))
        predicted = gaussian_nb_log_posterior(model, features[queries]).argmax(axis=1)
        rows.append([f"GNB {mode}", None, float(np.mean(predicted == labels[queries]))])
        if mode == "mle":
            charts.append(heatmap("GNB mle", {
                "classes": [CLASSES[cls] for cls in classes],
                "confusion_matrix": confusion_matrix(labels[queries], predicted, len(classes)).tolist(),
            }))

    counts = data.index["counts_gray"]
    intensity_sum = counts @ np.arange(256, dtype=np.int64)
    pixel_count = counts.sum(axis=1, dtype=np.int64)
    bins = (8 * intensity_sum) // (256 * pixel_count)
    model = discrete_bayes_fit(bins[db], labels[db], len(classes), 8)
    predicted = (model["prior"][:, None] * model["likelihood"][:, bins[queries]]).argmax(axis=0)
    rows.append(["Bayes mean_gray", None, float(np.mean(predicted == labels[queries]))])
    best = max(rows, key=lambda row: row[2])
    return result("C2 — Metode pencarian dan klasifikasi", "Perbandingan kNN, GNB dan Bayes diskret.", data,
                  [table(["Metode", "P@5", "Akurasi"], rows),
                   table(["Metode", *(CLASSES[cls] for cls in classes)], per_class)],
                  [f"Akurasi tertinggi {best[2]:.4f} diperoleh {best[0]}."],
                  charts=charts, params={"bins": 32, "bayes_levels": 8}, n_queries=len(queries))
