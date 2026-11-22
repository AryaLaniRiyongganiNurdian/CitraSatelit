import csv
import re
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TypedDict

import numpy as np

from src.data.env import load_settings


CLASSES = (
    "AnnualCrop", "Forest", "HerbaceousVegetation", "Highway", "Industrial",
    "Pasture", "PermanentCrop", "Residential", "River", "SeaLake",
)


class ManifestRow(TypedDict):
    id: str
    cls: str
    cls_idx: int
    split: str
    rgb_path: str
    tif_path: str
    in_gallery: bool
    in_colab_subset: bool


def scan_images(root: Path, extension: str) -> tuple[dict[str, str], list[str]]:
    if not root.is_dir():
        raise ValueError(f"Direktori dataset tidak ada: {root}")

    paths = {}
    invalid = []
    for cls in CLASSES:
        id_pattern = re.compile(rf"{cls}_[0-9]+")
        for path in sorted((root / cls).glob(f"*{extension}")):
            if not path.is_file():
                continue
            relative_path = path.relative_to(root).as_posix()
            if id_pattern.fullmatch(path.stem):
                paths[path.stem] = relative_path
            else:
                invalid.append(relative_path)
    return paths, invalid


def scan_dataset(
    rgb_dir: Path, tif_dir: Path, *, report_unmatched: bool = False,
) -> tuple[dict[str, str], dict[str, str]]:
    rgb, invalid_rgb = scan_images(rgb_dir, ".jpg")
    tif, invalid_tif = scan_images(tif_dir, ".tif")
    if report_unmatched:
        for modality, ids in (("JPG", rgb.keys() - tif.keys()), ("TIFF", tif.keys() - rgb.keys())):
            print(f"ID hanya di {modality} ({len(ids)}): {', '.join(sorted(ids))}")
        invalid = invalid_rgb + invalid_tif
        if invalid:
            examples = ", ".join(invalid[:5])
            print(f"{len(invalid)} berkas di luar pola ID EuroSAT dilewati. Contoh: {examples}")
    if not rgb and not tif:
        raise ValueError("Tidak ada ID EuroSAT di direktori dataset.")
    return rgb, tif


def select_ids(
    candidates: list[str], count: int, rng: np.random.Generator, cls: str, split: str,
) -> set[str]:
    if len(candidates) < count:
        raise ValueError(
            f"{cls} ({split}): perlu {count} pasangan JPG/TIFF, tersedia {len(candidates)}."
        )
    return set(rng.choice(candidates, size=count, replace=False).tolist())


def manifest_rows(rgb: dict[str, str], tif: dict[str, str], seed: int) -> list[ManifestRow]:
    all_ids = sorted(rgb.keys() | tif.keys())
    paired_ids = rgb.keys() & tif.keys()
    rows: list[ManifestRow] = []
    for cls_idx, cls in enumerate(CLASSES):
        ids = [image_id for image_id in all_ids if image_id.startswith(f"{cls}_")]
        if not ids:
            continue

        rng = np.random.default_rng(seed)
        train_size = len(ids) * 4 // 5
        train = {ids[i] for i in rng.permutation(len(ids))[:train_size]}
        train_paired = [image_id for image_id in ids if image_id in paired_ids and image_id in train]
        test_paired = [
            image_id for image_id in ids if image_id in paired_ids and image_id not in train
        ]
        gallery = select_ids(train_paired, 10, rng, cls, "train") | select_ids(
            test_paired, 15, rng, cls, "test"
        )
        colab = select_ids(train_paired, 160, rng, cls, "train") | select_ids(
            test_paired, 40, rng, cls, "test"
        )

        for image_id in ids:
            rows.append({
                "id": image_id,
                "cls": cls,
                "cls_idx": cls_idx,
                "split": "train" if image_id in train else "test",
                "rgb_path": rgb.get(image_id, ""),
                "tif_path": tif.get(image_id, ""),
                "in_gallery": image_id in gallery,
                "in_colab_subset": image_id in colab,
            })
    return rows


def build_manifest(rgb_dir: Path, tif_dir: Path, seed: int = 42) -> list[ManifestRow]:
    """Build rows with one split assignment per EuroSAT ID."""
    rgb, tif = scan_dataset(rgb_dir, tif_dir)
    return manifest_rows(rgb, tif, seed)


def write_manifest(rgb_dir: Path, tif_dir: Path, destination: Path, seed: int = 42) -> None:
    """Report skipped files and unmatched IDs, then write the manifest CSV."""
    rgb, tif = scan_dataset(rgb_dir, tif_dir, report_unmatched=True)
    rows = manifest_rows(rgb, tif, seed)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = NamedTemporaryFile(
        mode="w", newline="", encoding="utf-8", dir=destination.parent, delete=False,
    )
    temporary_path = Path(temporary.name)
    try:
        with temporary as stream:
            writer = csv.DictWriter(stream, fieldnames=list(ManifestRow.__annotations__))
            writer.writeheader()
            writer.writerows(rows)
        temporary_path.replace(destination)
    finally:
        temporary_path.unlink(missing_ok=True)


def main() -> int:
    try:
        settings = load_settings()
        if settings.rgb_dir is None or settings.allbands_dir is None:
            raise ValueError("Isi EUROSAT_RGB_DIR dan EUROSAT_ALLBANDS_DIR di .env.")
        destination = settings.artifacts_dir / "manifest.csv"
        write_manifest(settings.rgb_dir, settings.allbands_dir, destination, settings.seed)
    except (OSError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 1

    print(f"Manifest tersimpan di {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
