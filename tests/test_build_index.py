import csv
import json

import numpy as np
import tifffile
from PIL import Image

from src.core.cbir import extract_counts, zscore_fit
from src.core.stats import coarsen_counts, histogram_counts
from src.data.loader import load_rgb
from tools.build_index import build_index
from tools.make_gallery import make_gallery


def test_build_index_and_gallery_on_30_synthetic_images(tmp_path):
    rng = np.random.default_rng(42)
    rows = []
    root = tmp_path / "data"
    root.mkdir()
    for i in range(30):
        jpg = f"sample_{i}.jpg"
        tif = f"sample_{i}.tif"
        Image.fromarray(rng.integers(0, 256, (8, 9, 3), dtype=np.uint8)).save(root / jpg)
        bands = rng.integers(0, 1000, (8, 9, 13), dtype=np.uint16)
        if i % 10 >= 8:
            bands += 5000
        tifffile.imwrite(root / tif, bands, photometric="minisblack")
        rows.append(dict(id=f"sample_{i}", cls_idx=i // 10,
                         split="test" if i % 10 >= 8 else "train",
                         rgb_path=jpg, tif_path=tif, in_gallery=i % 10 == 0))

    manifest = tmp_path / "manifest.csv"
    with manifest.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    destination = tmp_path / "artifacts"
    build_index(manifest, root, root, destination)
    scale = json.loads((destination / "scale.json").read_text(encoding="utf-8"))
    assert set(scale) == {"lo", "hi"}
    assert len(scale["lo"]) == len(scale["hi"]) == 13 and max(scale["hi"]) < 1000

    pack = (destination / "thumbs.pack").read_bytes()
    with np.load(destination / "index.npz", allow_pickle=False) as index:
        assert index["ids"].dtype == np.dtype("U32")
        assert index["ids"].tolist() == [row["id"] for row in rows]
        for key in ("cls_idx", "split"):
            assert index[key].dtype == np.int8 and index[key].shape == (30,)
        assert index["split"].sum() == 6
        offsets = index["thumb_off"]
        assert offsets.dtype == np.int64 and offsets.shape == (31,)
        assert offsets[0] == 0 and offsets[-1] == len(pack)
        for i, row in enumerate(rows):
            assert pack[offsets[i]:offsets[i+1]] == (root / row["rgb_path"]).read_bytes()
        shapes = {"gray": (), "rgb": (3,), "hsv": (3,), "ms": (13,), "ndvi": (), "ndwi": ()}
        expected_keys = {"ids", "cls_idx", "split", "thumb_off"}
        for name, channels in shapes.items():
            key = f"counts_{name}"
            expected_keys.add(key)
            assert index[key].shape == (30, *channels, 256)
            assert index[key].dtype == np.uint16
            np.testing.assert_array_equal(index[key].sum(axis=-1), np.full((30, *channels), 72))
        rgb = load_rgb(root / rows[0]["rgb_path"])
        np.testing.assert_array_equal(index["counts_rgb"][0], extract_counts("rgb", rgb=rgb))
        for bins in (8, 16, 32, 64, 128, 256):
            direct = [histogram_counts(rgb[..., i], bins) for i in range(3)]
            np.testing.assert_array_equal(coarsen_counts(index["counts_rgb"][0], bins), direct)

        for mode, dim in (("grid2", 36), ("grid4", 144), ("mle", 6), ("ms_mle", 26)):
            feature = index[f"feat_{mode}"]
            expected_keys.update((f"feat_{mode}", f"z_{mode}_mean", f"z_{mode}_std"))
            assert feature.shape == (30, dim) and feature.dtype == np.float32
            for field, value in zip(("mean", "std"), zscore_fit(feature[index["split"] == 0])):
                saved = index[f"z_{mode}_{field}"]
                assert saved.shape == (dim,) and saved.dtype == np.float32
                np.testing.assert_allclose(saved, value)
        assert set(index.files) == expected_keys

    gallery = tmp_path / "gallery"
    make_gallery(manifest, root, root, gallery)
    assert len(list(gallery.rglob("*.jpg"))) == len(list(gallery.rglob("*.tif"))) == 3
    for row in rows[::10]:
        for key in ("rgb_path", "tif_path"):
            assert next(gallery.rglob(row[key])).read_bytes() == (root / row[key]).read_bytes()
