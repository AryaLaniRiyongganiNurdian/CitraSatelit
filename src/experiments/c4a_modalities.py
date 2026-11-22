from src.core.cbir import MODE_INFO
from src.data.manifest import CLASSES
from src.experiments.common import evaluate, heatmap, result, table

CLASSES_C4A = ("Forest", "Pasture", "HerbaceousVegetation", "AnnualCrop")


def run(data, modes):
    classes = sorted(set(data.classes) & {CLASSES.index(name) for name in CLASSES_C4A})
    entries = [
        evaluate(data, mode, metric, 32, classes)[0]
        for mode in modes
        for metric in (("chi2", "euclid") if MODE_INFO[mode]["kind"] == "pmf" else ("euclid",))
    ]
    best = max(entries, key=lambda entry: entry["macro_precision_at_k"])
    rows = [[i["mode"], i["metric"], i["macro_precision_at_k"], i["knn_accuracy"]] for i in entries]
    return result("C4a — Modalitas pada kelas mirip", "Perbandingan mode pada kelas terpilih.", data,
                  [table(["Mode", "Metrik", "P@5", "Akurasi"], rows)],
                  [f"{best['mode']} dengan {best['metric']} mencapai P@5 {best['macro_precision_at_k']:.4f}.",
                   f"Peluang acak untuk {len(classes)} kelas adalah {1 / len(classes):.4f}."],
                  charts=[heatmap(f"{best['mode']} {best['metric']}", best)],
                  params={"modes": list(modes), "bins": 32}, n_queries=best["protocol"]["n_queries"])
