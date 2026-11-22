"""Build histograms, moment features and an original JPEG pack."""
import argparse
import csv
import json
import multiprocessing as mp
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from src.core.cbir import extract_counts, extract_moment_feature, zscore_fit
from src.core.spectral import fit_percentile_scale
from src.data.env import load_settings
from src.data.loader import load_rgb, load_tif

COUNT_SHAPES = {"gray": (), "rgb": (3,), "hsv": (3,), "ms": (13,), "ndvi": (), "ndwi": ()}
MOMENT_DIMS = {"grid2": 36, "grid4": 144, "mle": 6, "ms_mle": 26}
_worker_inputs = None


def read_manifest(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def fit_scale(rows, tif_root, seed):
    train = [row["tif_path"] for row in rows if row["split"] == "train"]
    rng = np.random.default_rng(seed)
    selected = rng.choice(len(train), size=min(2000, len(train)), replace=False)
    return fit_percentile_scale([load_tif(tif_root / train[i]) for i in selected])


def _init_worker(rgb_root, tif_root, scale):
    global _worker_inputs
    _worker_inputs = rgb_root, tif_root, scale


def extract_features(rgb, bands, scale):
    kwargs = dict(rgb=rgb, bands=bands, scale=scale)
    counts = {name: extract_counts(name, **kwargs) for name in ("gray", "rgb", "hsv")}
    counts["ms"] = extract_counts("ms13", **kwargs)
    counts["ndvi"], counts["ndwi"] = extract_counts("ndvi_ndwi", **kwargs)
    return counts, {name: extract_moment_feature(name, **kwargs) for name in MOMENT_DIMS}


def _extract(row):
    rgb_root, tif_root, scale = _worker_inputs
    path = rgb_root / row["rgb_path"]
    rgb, bands = load_rgb(path), load_tif(tif_root / row["tif_path"])
    if rgb.shape[:2] != bands.shape[:2] or rgb.shape[0] * rgb.shape[1] > 65535:
        raise ValueError(f"Incompatible image sizes for {row['id']}")
    counts, moments = extract_features(rgb, bands, scale)
    return counts, moments, path.read_bytes()


def build_index(manifest, rgb_root, tif_root, destination, *, seed=42):
    rows = read_manifest(manifest)
    ids = [row["id"] for row in rows]
    if not rows or len(set(ids)) != len(ids) or any(len(key) > 32 for key in ids):
        raise ValueError("Expected unique image IDs of at most 32 characters")
    if any(not row["rgb_path"] or not row["tif_path"] for row in rows):
        raise ValueError("The index requires paired JPEG and TIFF images")

    scale = fit_scale(rows, tif_root, seed)
    split = np.array([{"train": 0, "test": 1}[row["split"]] for row in rows], dtype=np.int8)
    n = len(rows)
    offsets = np.zeros(n + 1, dtype=np.int64)
    payload = dict(ids=np.array(ids, dtype="U32"), split=split,
                   cls_idx=np.array([int(row["cls_idx"]) for row in rows], dtype=np.int8))
    payload["thumb_off"] = offsets
    for name, shape in COUNT_SHAPES.items():
        payload[f"counts_{name}"] = np.empty((n, *shape, 256), dtype=np.uint16)
    for name, dim in MOMENT_DIMS.items():
        payload[f"feat_{name}"] = np.empty((n, dim), dtype=np.float32)

    destination.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=destination) as folder:
        staging = Path(folder)
        with (staging / "thumbs.pack").open("wb") as pack, mp.get_context("spawn").Pool(
            4, initializer=_init_worker, initargs=(rgb_root, tif_root, scale),
        ) as pool:
            for i, (counts, moments, jpeg) in enumerate(pool.imap(_extract, rows, chunksize=16)):
                for name, value in counts.items():
                    payload[f"counts_{name}"][i] = value
                for name, value in moments.items():
                    payload[f"feat_{name}"][i] = value
                pack.write(jpeg)
                offsets[i + 1] = pack.tell()
        for name in MOMENT_DIMS:
            stats = zscore_fit(payload[f"feat_{name}"][split == 0])
            for field, value in zip(("mean", "std"), stats):
                payload[f"z_{name}_{field}"] = value.astype(np.float32)
        np.savez_compressed(staging / "index.npz", **payload)
        (staging / "scale.json").write_text(json.dumps(scale) + "\n", encoding="utf-8")
        for name in ("scale.json", "thumbs.pack", "index.npz"):
            (staging / name).replace(destination / name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    settings = load_settings()
    if settings.rgb_dir is None or settings.allbands_dir is None:
        parser.error("Konfigurasikan direktori RGB dan all-bands")
    build_index(settings.artifacts_dir / "manifest.csv", settings.rgb_dir, settings.allbands_dir,
                settings.artifacts_dir, seed=settings.seed)


if __name__ == "__main__":
    main()
