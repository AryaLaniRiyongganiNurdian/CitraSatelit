import hashlib
import io
import json
from zipfile import ZipFile

import numpy as np
import pytest
import tifffile
from PIL import Image

from tools.make_colab_subset import make_subset


@pytest.fixture
def source(tmp_path):
    jpg, tif = tmp_path / "jpg", tmp_path / "tif"
    for folder in (jpg, tif):
        (folder / "Forest").mkdir(parents=True)
    rows = ["id,cls,cls_idx,split,rgb_path,tif_path,in_gallery,in_colab_subset"]
    rng = np.random.default_rng(42)
    for i, split in enumerate(("train", "test", "train")):
        stem = f"Forest/Forest_{i}"
        Image.fromarray(rng.integers(0, 256, (8, 8, 3), dtype=np.uint8)).save(jpg / (stem + ".jpg"))
        tifffile.imwrite(tif / (stem + ".tif"), rng.integers(0, 2000, (8, 8, 13), dtype=np.uint16),
                         photometric="minisblack")
        rows.append(f"Forest_{i},Forest,1,{split},{stem}.jpg,{stem}.tif,False,{i < 2}")
    manifest = tmp_path / "source.csv"
    manifest.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return manifest, jpg, tif


def test_archive_structure_and_determinism(source, tmp_path):
    archive = tmp_path / "subset.zip"
    make_subset(*source, archive)
    first = archive.read_bytes()
    make_subset(*source, archive)
    assert archive.read_bytes() == first
    assert (tmp_path / "subset.zip.sha256").read_text().split()[0] == hashlib.sha256(first).hexdigest()

    with ZipFile(archive) as bundle:
        names = set(bundle.namelist())
        expected = {"manifest.csv", "index.npz", "scale.json", "thumbs.pack",
                    "rgb/Forest/Forest_0.jpg", "rgb/Forest/Forest_1.jpg",
                    "tif/Forest/Forest_0.tif", "tif/Forest/Forest_1.tif"}
        assert names == expected | {"SHA256SUMS"}
        sums = dict(line.split("  ", 1)[::-1] for line in bundle.read("SHA256SUMS").decode().splitlines())
        assert set(sums) == expected
        assert all(hashlib.sha256(bundle.read(name)).hexdigest() == digest for name, digest in sums.items())
        assert "Forest_2" not in bundle.read("manifest.csv").decode()
        assert len(json.loads(bundle.read("scale.json"))["lo"]) == 13
        with np.load(io.BytesIO(bundle.read("index.npz")), allow_pickle=False) as index:
            assert index["ids"].tolist() == ["Forest_0", "Forest_1"]
            assert index["split"].tolist() == [0, 1]
            assert index["counts_ms"].shape == (2, 13, 256)
            assert index["thumb_off"][-1] == len(bundle.read("thumbs.pack"))


def test_size_limit_keeps_previous_archive(source, tmp_path):
    archive = tmp_path / "subset.zip"
    make_subset(*source, archive)
    first = archive.read_bytes()
    with pytest.raises(ValueError, match="ukuran"):
        make_subset(*source, archive, max_bytes=64)
    assert archive.read_bytes() == first


def test_subset_requires_paired_images(source, tmp_path):
    (source[2] / "Forest/Forest_1.tif").unlink()
    archive = tmp_path / "subset.zip"
    with pytest.raises(ValueError, match="Forest_1"):
        make_subset(*source, archive)
    assert not archive.exists()
