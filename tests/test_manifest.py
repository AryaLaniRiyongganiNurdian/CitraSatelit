import csv
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

from src.data.manifest import build_manifest, write_manifest


@pytest.fixture
def dataset(tmp_path):
    rgb_dir = tmp_path / "rgb"
    tif_dir = tmp_path / "allbands"
    for cls in ("Forest", "SeaLake"):
        (rgb_dir / cls).mkdir(parents=True)
        (tif_dir / cls).mkdir(parents=True)
        for i in reversed(range(250)):
            (rgb_dir / cls / f"{cls}_{i}.jpg").touch()
            (tif_dir / cls / f"{cls}_{i}.tif").touch()
    return rgb_dir, tif_dir


def test_manifest_is_deterministic_and_stratified(dataset):
    rows = build_manifest(*dataset, seed=42)
    assert rows == build_manifest(*dataset, seed=42)
    assert len({row["id"] for row in rows}) == len(rows) == 500

    for cls, cls_idx in (("Forest", 1), ("SeaLake", 9)):
        by_class = [row for row in rows if row["cls"] == cls]
        assert {row["cls_idx"] for row in by_class} == {cls_idx}
        assert Counter(row["split"] for row in by_class) == {"train": 200, "test": 50}
        assert Counter(row["split"] for row in by_class if row["in_gallery"]) == {
            "train": 10, "test": 15,
        }
        assert Counter(row["split"] for row in by_class if row["in_colab_subset"]) == {
            "train": 160, "test": 40,
        }
        ids = sorted(row["id"] for row in by_class)
        train_indices = np.random.default_rng(42).permutation(len(ids))[:200]
        assert {row["id"] for row in by_class if row["split"] == "train"} == {
            ids[i] for i in train_indices
        }
        for row in by_class:
            assert Path(row["rgb_path"]) == Path(cls, row["id"] + ".jpg")
            assert Path(row["tif_path"]) == Path(cls, row["id"] + ".tif")


def test_manifest_writes_relative_paths_and_reports_unmatched_ids(dataset, tmp_path, capsys):
    rgb_dir, tif_dir = dataset
    (tif_dir / "Forest" / "Forest_0.tif").unlink()
    (rgb_dir / "SeaLake" / "SeaLake_0.jpg").unlink()
    destination = tmp_path / "artifacts" / "manifest.csv"

    write_manifest(rgb_dir, tif_dir, destination, seed=42)

    with destination.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        assert reader.fieldnames == [
            "id", "cls", "cls_idx", "split", "rgb_path", "tif_path", "in_gallery", "in_colab_subset",
        ]
        rows = {row["id"]: row for row in reader}
    assert rows["Forest_0"]["tif_path"] == ""
    assert rows["SeaLake_0"]["rgb_path"] == ""
    assert not Path(rows["Forest_0"]["rgb_path"]).is_absolute()
    assert not Path(rows["SeaLake_0"]["tif_path"]).is_absolute()
    output = capsys.readouterr().out
    assert "Forest_0" in output
    assert "SeaLake_0" in output


def test_manifest_skips_and_reports_files_outside_the_id_format(dataset, tmp_path, capsys):
    rgb_dir, tif_dir = dataset
    destination = tmp_path / "manifest.csv"
    write_manifest(rgb_dir, tif_dir, destination, seed=42)
    expected = destination.read_bytes()
    capsys.readouterr()

    invalid_paths = [tif_dir / "SeaLake" / f"Jakarta_{i:06}.tif" for i in range(7)]
    for path in invalid_paths:
        path.touch()

    write_manifest(rgb_dir, tif_dir, destination, seed=42)

    assert destination.read_bytes() == expected
    assert all(path.is_file() for path in invalid_paths)
    output = capsys.readouterr().out
    assert "7 berkas di luar pola ID EuroSAT dilewati" in output
    assert "SeaLake/Jakarta_000000.tif" in output
    assert "SeaLake/Jakarta_000006.tif" not in output
