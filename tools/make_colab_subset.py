"""Pack the manifest's EuroSAT subset and its train-fitted index."""
import argparse
import csv
import hashlib
import sys
from collections import Counter
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data.env import load_settings
from src.data.manifest import CLASSES
from tools.build_index import build_index, read_manifest

ARCHIVE_NAME = "eurosat_subset_v1.zip"
MAX_ARCHIVE_BYTES = 250_000_000


def _image_path(root, name, suffix, image_id):
    relative = PurePosixPath(name)
    if (not name or relative.is_absolute() or ".." in relative.parts or "\\" in name
            or ":" in name or relative.suffix != suffix):
        raise ValueError(f"Path {suffix} tidak valid untuk {image_id}")
    path = root.joinpath(*relative.parts)
    if not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Citra {suffix} untuk {image_id} tidak tersedia di dataset")
    return path


def _add_file(bundle, name, path):
    digest = hashlib.sha256()
    member = ZipInfo(name)
    member.compress_type = ZIP_DEFLATED
    with path.open("rb") as source, bundle.open(member, "w") as target:
        while block := source.read(1024 * 1024):
            digest.update(block)
            target.write(block)
    return f"{digest.hexdigest()}  {name}"


def make_subset(manifest, rgb_root, tif_root, destination, *, seed=42,
                max_bytes=MAX_ARCHIVE_BYTES, require_full=False):
    """Return the number of pairs packaged. Leave an existing ZIP intact on validation failure."""
    if destination.suffix.lower() != ".zip":
        raise ValueError("Nama arsip harus berakhiran .zip")
    rows = [row for row in read_manifest(manifest) if row["in_colab_subset"].lower() == "true"]
    rows.sort(key=lambda row: (int(row["cls_idx"]), row["id"]))
    split_counts = Counter((row["cls"], row["split"]) for row in rows)
    if not rows or {row["split"] for row in rows} != {"train", "test"}:
        raise ValueError("Manifest subset harus memuat data train dan test")
    expected = {(cls, split): count for cls in CLASSES for split, count in (("train", 160), ("test", 40))}
    if require_full and split_counts != expected:
        raise ValueError("Subset Colab perlu 160 train dan 40 test per kelas")

    members = {}
    for row in rows:
        for field, root, prefix, suffix in (
            ("rgb_path", rgb_root, "rgb", ".jpg"),
            ("tif_path", tif_root, "tif", ".tif"),
        ):
            image = _image_path(root, row[field], suffix, row["id"])
            name = f"{prefix}/{PurePosixPath(row[field]).as_posix()}"
            if name in members:
                raise ValueError(f"Path duplikat untuk {row['id']}: {name}")
            members[name] = image

    destination.parent.mkdir(parents=True, exist_ok=True)
    checksum = destination.with_name(destination.name + ".sha256")
    with TemporaryDirectory(dir=destination.parent) as folder:
        stage = Path(folder)
        subset_csv = stage / "manifest.csv"
        with subset_csv.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        build_index(subset_csv, rgb_root, tif_root, stage, seed=seed)
        for name in ("manifest.csv", "index.npz", "scale.json", "thumbs.pack"):
            members[name] = stage / name

        archive = stage / destination.name
        with ZipFile(archive, "w", ZIP_DEFLATED) as bundle:
            sums = [_add_file(bundle, name, path) for name, path in sorted(members.items())]
            bundle.writestr(ZipInfo("SHA256SUMS"), "\n".join(sums) + "\n", compress_type=ZIP_DEFLATED)
        if archive.stat().st_size > max_bytes:
            raise ValueError(f"Batas ukuran arsip terlampaui ({archive.stat().st_size} > {max_bytes} byte)")

        with archive.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        staged_checksum = stage / checksum.name
        staged_checksum.write_text(f"{digest}  {destination.name}\n", encoding="ascii", newline="\n")
        archive.replace(destination)
        staged_checksum.replace(checksum)
    return len(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-bytes", type=int, default=MAX_ARCHIVE_BYTES)
    args = parser.parse_args()
    settings = load_settings()
    if settings.rgb_dir is None or settings.allbands_dir is None:
        parser.error("Konfigurasikan EUROSAT_RGB_DIR dan EUROSAT_ALLBANDS_DIR.")
    destination = args.output or settings.artifacts_dir / ARCHIVE_NAME
    try:
        count = make_subset(settings.artifacts_dir / "manifest.csv", settings.rgb_dir, settings.allbands_dir,
                            destination, seed=settings.seed, max_bytes=args.max_bytes, require_full=True)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(f"{count} pasangan · {destination.stat().st_size:,} byte · {destination}")


if __name__ == "__main__":
    main()
