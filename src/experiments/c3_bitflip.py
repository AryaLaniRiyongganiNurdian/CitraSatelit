import numpy as np

from src.core.color import rgb_to_gray
from src.core.probability import geometric_pmf
from src.core.secret_sharing import flip_bits, reconstruct_xor, split_xor
from src.experiments.common import result, table

PROBABILITIES = (0.0005, 0.001, 0.005, 0.01, 0.02, 0.05, 0.1)


def _trial_counts(images, trials, bits, damaged, p, rng):
    error_counts, first_errors = [], []
    for image in images:
        clean = np.broadcast_to(image, (trials, *image.shape))
        shares = split_xor(clean, 3, rng)
        for i in range(damaged):
            shares[i] = flip_bits(shares[i], p, rng, bits)
        wrong = (reconstruct_xor(shares) != clean).reshape(trials, -1)
        error_counts.extend(wrong.sum(axis=1))
        first_errors.extend(np.where(wrong.any(axis=1), wrong.argmax(axis=1) + 1, 0))
    return np.array(error_counts), np.array(first_errors)


def run(data):
    sample = data.sample(1, data.classes, 2)
    images = {
        8: [rgb_to_gray(data.rgb(i)) for i in sample],
        16: [data.bands(i)[..., 3] for i in sample],
    }
    rng = np.random.default_rng(data.seed)
    trials = 3 if data.smoke else 30
    rows, geometric, chebyshev = [], [], []
    series = []
    for bits, sources in images.items():
        pixels = sources[0].size
        for damaged in (1, 2):
            empirical = []
            for p in PROBABILITIES:
                effective = (1 - (1 - 2 * p) ** damaged) / 2
                expected = 1 - (1 - effective) ** bits
                counts, first = _trial_counts(sources, trials, bits, damaged, p, rng)
                observed = float(counts.mean() / pixels)
                empirical.append(observed)
                rows.append([bits, damaged, p, effective, observed, expected, abs(observed - expected)])
                if p == 0.01:
                    for position in range(1, min(pixels, 64) + 1):
                        geometric.append([bits, damaged, position, float(np.mean(first == position)),
                                          geometric_pmf(position, expected)])
                    mu = pixels * expected
                    sigma = np.sqrt(pixels * expected * (1 - expected))
                    for k in range(1, 6):
                        tail = float(np.mean(np.abs(counts - mu) >= k * sigma))
                        chebyshev.append([bits, damaged, k, tail, 1 / k ** 2])
            series.append({"name": f"{bits} bit, {damaged} share", "y": empirical})

    worst = max(rows, key=lambda row: row[-1])
    return result("C3 — Galat bit-flip", "Simulasi galat piksel dan posisi galat pertama.", data,
                  [table(["Bit", "Share rusak", "p", "p efektif", "Empiris", "Teori", "Selisih"], rows),
                   table(["Bit", "Share rusak", "Posisi", "Empiris", "Geometrik"], geometric),
                   table(["Bit", "Share rusak", "k sigma", "Empiris", "Batas Chebyshev"], chebyshev)],
                  [f"Selisih empiris–teori maksimum {worst[-1]:.4f} pada {worst[0]} bit dan p={worst[2]}.",
                   "PMF empiris menghitung semua percobaan, termasuk percobaan tanpa piksel salah."],
                  charts=[{"kind": "line", "title": "Galat piksel", "x": list(PROBABILITIES), "series": series}],
                  params={"p": list(PROBABILITIES), "trials": trials}, n_queries=len(sample))
