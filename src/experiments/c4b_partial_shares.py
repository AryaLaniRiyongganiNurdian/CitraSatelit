from collections import defaultdict

import numpy as np

from src.core.cbir import counts_to_feature, extract_counts, search_topk
from src.core.color import rgb_to_gray
from src.core.probability import chi2_sf, chi2_uniform_stat, pearson_r, shannon_entropy
from src.core.secret_sharing import mse, reconstruct_xor, split_xor, tamper_pixel
from src.core.stats import histogram_counts
from src.experiments.common import features, result, table


def run(data, mode, bins=32, metric="chi2"):
    sample = data.sample(1, data.classes, 2)
    db = data.split_rows(0, data.classes)
    database, _ = features(data.index, mode, bins, db, sample)
    rng = np.random.default_rng(data.seed)
    records = defaultdict(list)
    tamper = []
    for i in sample:
        image = data.rgb(i)
        source = rgb_to_gray(image) if mode == "gray" else image
        for n in (2, 3, 4, 8):
            shares = split_xor(source, n, rng)
            for k in range(1, n + 1):
                subsets = [("awal", shares[:k])]
                if k < n:
                    subsets.append(("akhir", shares[-k:]))
                for label, subset in subsets:
                    partial = reconstruct_xor(subset)
                    counts = histogram_counts(partial, 256)
                    image_for_feature = np.repeat(partial[..., None], 3, axis=2) if mode == "gray" else partial
                    query = counts_to_feature(extract_counts(mode, rgb=image_for_feature), bins)
                    hits, _ = search_topk(query, database, min(5, len(db)), metric)
                    values = (shannon_entropy(counts), chi2_sf(chi2_uniform_stat(counts), 255),
                              pearson_r(source, partial), mse(source, partial),
                              float(np.mean(data.labels[db[hits]] == data.labels[i])))
                    records[n, k, label].append(values)
            changed = reconstruct_xor([tamper_pixel(shares[0], 0, 0, bit=2), *shares[1:]])
            delta = np.abs(changed.astype(np.int16) - source)
            pixels = np.any(delta != 0, axis=-1) if source.ndim == 3 else delta != 0
            tamper.append([str(data.index["ids"][i]), n, int(pixels.sum()), int(delta.max())])

    rows = []
    for (n, k, subset), values in sorted(records.items()):
        columns = np.asarray(values).T
        means = [float(np.mean(column[np.isfinite(column)])) if np.isfinite(column).any() else None
                 for column in columns]
        rows.append([n, k, subset, *means, float(np.mean(columns[1] > 0.05))])
    partial_rows = [row for row in rows if row[1] < row[0]]
    best = max(partial_rows, key=lambda row: row[7])
    return result("C4b — Share parsial", "Evaluasi statistik share dan uji perubahan piksel.", data,
                  [table(["n", "k", "Himpunan", "Entropi", "p-value", "Pearson", "MSE", "P@5",
                          "Proporsi p-value > 0,05"], rows),
                   table(["ID", "n", "Piksel berubah", "Selisih maksimum"], tamper)],
                  [f"P@5 parsial tertinggi {best[7]:.4f}; peluang acak {1 / len(data.classes):.4f}.",
                   f"Rata-rata proporsi p-value > 0,05 untuk share parsial adalah "
                   f"{np.mean([row[8] for row in partial_rows]):.4f}."],
                  params={"n": [2, 3, 4, 8], "mode": mode, "bins": bins, "metric": metric},
                  n_queries=len(sample))
