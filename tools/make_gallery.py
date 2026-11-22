"""Copy the paired gallery images selected by the manifest."""
import shutil
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.env import PROJECT_ROOT, load_settings
from tools.build_index import read_manifest


def make_gallery(manifest, rgb_root, tif_root, destination):
    rows = [row for row in read_manifest(manifest) if row["in_gallery"].lower() == "true"]
    if not rows:
        raise ValueError("Manifest has no gallery selections")
    copies = {}
    for row in rows:
        image_id = row["id"]
        if Path(image_id).name != image_id:
            raise ValueError(f"Invalid gallery ID: {image_id}")
        for field, root, suffix in (("rgb_path", rgb_root, ".jpg"), ("tif_path", tif_root, ".tif")):
            original = root / row[field]
            if not original.is_file():
                raise FileNotFoundError(original)
            copies[f"{image_id}{suffix}"] = original
    destination.mkdir(parents=True, exist_ok=True)
    if {path.name for path in destination.iterdir()} - copies.keys():
        raise ValueError("Gallery contains entries outside the current manifest")
    for name, original in copies.items():
        shutil.copyfile(original, destination / name)
    return len(rows)


def main():
    settings = load_settings()
    if settings.rgb_dir is None or settings.allbands_dir is None:
        raise SystemExit("Konfigurasikan direktori RGB dan all-bands")
    count = make_gallery(settings.artifacts_dir / "manifest.csv", settings.rgb_dir,
                         settings.allbands_dir, PROJECT_ROOT / "app_assets" / "gallery")
    print(f"Galeri: {count} pasangan JPG/TIFF")


if __name__ == "__main__":
    main()
