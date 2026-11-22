"""Build offline experiment artifacts for a synthetic smoke run or full EuroSAT."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

import numpy as np
import tifffile
from PIL import Image

from src.core.cbir import MODE_INFO, zscore_fit
from src.data.env import PROJECT_ROOT, load_settings
from src.experiments import c1_bins, c2_metrics, c3_bitflip, c4a_modalities, c4b_partial_shares, c4c_complexity
from src.experiments.common import Dataset, combinations, evaluate
from tools.build_index import extract_features, fit_scale, read_manifest

C4A_MODES = tuple(MODE_INFO)


def _json_value(value):
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    return value


def run(data, destination, *, c4a_modes=C4A_MODES, c4b_mode="rgb", generated_at=None):
    if generated_at is None:
        generated_at = datetime.now(timezone.utc).isoformat()
    cache = {}

    def evaluation(mode, metric, bins):
        key = f"{mode}:{metric}:{bins}"
        if key not in cache:
            cache[key] = evaluate(data, mode, metric, bins)
        return cache[key]

    jobs = (
        ("C1", lambda: c1_bins.run(data, evaluation)),
        ("C2", lambda: c2_metrics.run(data, evaluation)),
        ("C3", lambda: c3_bitflip.run(data)),
        ("C4a", lambda: c4a_modalities.run(data, c4a_modes)),
        ("C4b", lambda: c4b_partial_shares.run(data, c4b_mode)),
        ("C4c", lambda: c4c_complexity.run(data)),
    )
    payloads = {}
    for name, execute in jobs:
        start = data.clock()
        payload = execute()
        payload.update(id=name, generated_at=generated_at, runtime_s=data.clock() - start)
        payload["params"].update(seed=data.seed, all_queries=data.all_queries)
        payloads[name] = payload
        print(f"{name}: {payload['runtime_s']:.3f}s", flush=True)

    for args in combinations():
        evaluation(*args)
    payloads["eval_cache"] = {key: entry for key, (entry, _) in cache.items()}
    destination.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=destination) as temp:
        staging = Path(temp)
        for name, payload in payloads.items():
            file = f"{name}.json"
            (staging / file).write_text(
                json.dumps(_json_value(payload), ensure_ascii=False, allow_nan=False, indent=2) + "\n",
                encoding="utf-8",
            )
        for path in staging.iterdir():
            path.replace(destination / path.name)


def _make_smoke_data(root, seed, clock):
    rng = np.random.default_rng(seed)
    rows = []
    labels, splits = [], []
    for cls in (0, 1, 2, 5):
        for i in range(10):
            image_id = f"sample_{cls}_{i}"
            rgb = rng.integers(cls * 20, cls * 20 + 100, (8, 8, 3), dtype=np.uint8)
            bands = rng.integers(cls * 200, cls * 200 + 2000, (8, 8, 13), dtype=np.uint16)
            jpg, tif = f"{image_id}.jpg", f"{image_id}.tif"
            Image.fromarray(rgb).save(root / jpg)
            tifffile.imwrite(root / tif, bands, photometric="minisblack")
            test = int(i >= 8)
            labels.append(cls)
            splits.append(test)
            rows.append(dict(id=image_id, rgb_path=jpg, tif_path=tif, split="test" if test else "train"))

    scale = fit_scale(rows, root, seed)
    all_features = {}
    data = Dataset({}, rows, root, root, clock, seed=seed, smoke=True)
    for i in range(len(rows)):
        counts, moments = extract_features(data.rgb(i), data.bands(i), scale)
        for prefix, values in (("counts", counts), ("feat", moments)):
            for key, value in values.items():
                all_features.setdefault(f"{prefix}_{key}", []).append(value)
    index = {
        name: np.stack(values).astype(np.uint16 if name.startswith("counts_") else np.float32)
        for name, values in all_features.items()
    }
    index.update(ids=np.array([row["id"] for row in rows]), cls_idx=np.array(labels), split=np.array(splits))
    for name in MODE_INFO:
        if MODE_INFO[name]["kind"] == "moment":
            mean, std = zscore_fit(index[f"feat_{name}"][index["split"] == 0])
            index[f"z_{name}_mean"], index[f"z_{name}_std"] = mean.astype(np.float32), std.astype(np.float32)
    data.index = index
    return data


def run_smoke(destination, *, c4a_modes=C4A_MODES, c4b_mode="rgb", clock=perf_counter, generated_at=None):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=destination.parent) as temp:
        run(_make_smoke_data(Path(temp), 42, clock), destination, c4a_modes=c4a_modes,
            c4b_mode=c4b_mode, generated_at=generated_at)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", choices=("smoke", "full"), required=True)
    parser.add_argument("--all-queries", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.config == "smoke":
        if args.all_queries:
            parser.error("--all-queries hanya diperlukan untuk konfigurasi full")
        run_smoke(args.output or PROJECT_ROOT / "results" / "smoke")
        return

    settings = load_settings()
    if settings.rgb_dir is None or settings.allbands_dir is None:
        parser.error("Konfigurasikan direktori RGB dan all-bands")
    rows = read_manifest(settings.artifacts_dir / "manifest.csv")
    with np.load(settings.artifacts_dir / "index.npz", allow_pickle=False) as saved:
        index = {key: saved[key] for key in saved.files if key != "thumb_off"}
    if len(rows) != 27000 or index["ids"].tolist() != [row["id"] for row in rows]:
        parser.error("Konfigurasi full memerlukan indeks yang cocok dengan manifest 27.000 citra")
    data = Dataset(index, rows, settings.rgb_dir, settings.allbands_dir, perf_counter,
                   seed=settings.seed, all_queries=args.all_queries)
    run(data, args.output or PROJECT_ROOT / "results")


if __name__ == "__main__":
    main()
