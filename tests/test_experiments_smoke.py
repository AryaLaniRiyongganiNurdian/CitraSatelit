import json

from src.experiments.run_all import run_smoke


def test_smoke_produces_experiment_results_and_all_precomputed_payloads_twice(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    options = dict(clock=lambda: 0, generated_at="2026-11-22T00:00:00Z")
    run_smoke(first, **options)
    run_smoke(second, **options)
    assert {file.name: file.read_bytes() for file in first.glob("*.json")} == {
        file.name: file.read_bytes() for file in second.glob("*.json")
    }

    for name in ("C1", "C2", "C3", "C4a", "C4b", "C4c"):
        result = json.loads((first / f"{name}.json").read_text(encoding="utf-8"))
        assert set(result) == {"id", "title", "description", "generated_at", "runtime_s", "params",
                               "dataset", "tables", "charts", "findings", "analysis_md"}
        assert result["id"] == name
        assert 0 < len(result["analysis_md"]) <= 1500
        assert set(result["dataset"]) == {"n_images", "n_queries", "note"}
        assert result["dataset"]["n_images"] > 0
        assert result["tables"] and result["findings"]
        for table in result["tables"]:
            assert all(len(row) == len(table["columns"]) for row in table["rows"])

        assert all(chart["kind"] in {"bar", "line", "scatter", "heatmap"} and chart["title"]
                   for chart in result["charts"])
        if name == "C4a":
            assert set(result["params"]["modes"]) == {
                "gray", "rgb", "hsv", "ms13", "ndvi_ndwi", "ms13_idx", "grid2", "grid4", "mle", "ms_mle",
            }
        if name == "C4b":
            assert (result["params"]["mode"], result["params"]["bins"], result["params"]["metric"]) == (
                "rgb", 32, "chi2",
            )

    cache = json.loads((first / "eval_cache.json").read_text(encoding="utf-8"))
    combos = {(i["mode"], i["metric"], i["bins"]) for i in cache.values()}
    metrics = ("euclid", "chi2", "intersection")
    pmf_modes = ("gray", "rgb", "hsv", "ms13", "ndvi_ndwi", "ms13_idx")
    expected = {(mode, metric, 32) for mode in pmf_modes for metric in metrics}
    expected |= {(mode, "euclid", None) for mode in ("grid2", "grid4", "mle", "ms_mle")}
    expected |= {("rgb", metric, bins) for metric in metrics for bins in (8, 16, 64, 128, 256)}
    assert combos == expected and len(cache) == len(expected)
    for entry in cache.values():
        assert entry["source"] == "precomputed"
        assert set(entry["protocol"]) == {"n_queries", "db_size", "queries_per_class", "k"}
        assert len(entry["classes"]) == len(entry["per_class"]) == len(entry["confusion_matrix"])
        assert sum(map(sum, entry["confusion_matrix"])) == entry["protocol"]["n_queries"]
        assert 0 <= entry["macro_precision_at_k"] <= 1
        assert 0 <= entry["knn_accuracy"] <= 1
