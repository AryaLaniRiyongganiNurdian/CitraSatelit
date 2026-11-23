"""Data preparation and reporting used by the generated Colab notebook."""
import hashlib
import os
import re
import shutil
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from urllib.request import urlopen
from zipfile import ZipFile

from dotenv import load_dotenv
import numpy as np

from src.experiments.common import Dataset
from tools.build_index import read_manifest
from time import perf_counter

ARCHIVE_NAME = "eurosat_subset_v1.zip"
EXPERIMENTS = ("C1", "C2", "C3", "C4a", "C4b", "C4c")


def _sha256(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def download_subset(cache, urls, digest=""):
    """Fetch a release (primary then mirror) and verify its published digest."""
    cache.mkdir(parents=True, exist_ok=True)
    destination = cache / ARCHIVE_NAME
    errors = []
    for url in filter(None, urls):
        try:
            expected = digest
            if not expected:
                with urlopen(url + ".sha256", timeout=60) as stream:
                    fields = stream.read(4096).decode("ascii").split()
                expected = fields[0] if fields else ""
            if not re.fullmatch("[0-9a-fA-F]{64}", expected):
                raise ValueError("SHA-256 rilis tidak valid")
            expected = expected.lower()
            if destination.is_file() and _sha256(destination) == expected:
                return destination
            with TemporaryDirectory(dir=cache) as folder:
                stage = Path(folder) / ARCHIVE_NAME
                with urlopen(url, timeout=60) as stream, stage.open("wb") as target:
                    shutil.copyfileobj(stream, target)
                if _sha256(stage) != expected:
                    raise ValueError("SHA-256 arsip berbeda dari rilis")
                stage.replace(destination)
            return destination
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
    raise RuntimeError("Arsip tidak tersedia. Atur COLAB_ARCHIVE atau COLAB_SUBSET_URL. " + " | ".join(errors))


def extract_verified(archive, cache, digest=""):
    """Read checked members into a cache keyed by the verified ZIP contents."""
    archive_digest = _sha256(archive)
    sidecar = archive.with_name(archive.name + ".sha256")
    fields = sidecar.read_text(encoding="ascii").split() if sidecar.is_file() else []
    expected = digest or (fields[0] if fields else archive_digest)
    if expected.lower() != archive_digest:
        raise ValueError("Checksum ZIP tidak cocok")

    destination = cache / archive_digest
    with ZipFile(archive) as bundle:
        entries = bundle.namelist()
        checks = {}
        for line in bundle.read("SHA256SUMS").decode("utf-8").splitlines():
            digest, name = line.split("  ", 1)
            path = PurePosixPath(name)
            if (not re.fullmatch("[0-9a-f]{64}", digest) or not path.parts or path.is_absolute()
                    or ".." in path.parts or ":" in name or "\\" in name or name in checks):
                raise ValueError(f"Entri checksum tidak valid: {name}")
            checks[name] = digest
        if len(entries) != len(set(entries)) or set(entries) != set(checks) | {"SHA256SUMS"}:
            raise ValueError("Daftar anggota ZIP berbeda dari SHA256SUMS")
        if destination.is_dir():
            for name, digest in checks.items():
                if _sha256(destination / name) != digest:
                    raise ValueError(f"Checksum cache tidak cocok: {name}")
            return destination

        cache.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=cache) as folder:
            stage = Path(folder) / "dataset"
            for name, digest in checks.items():
                path = stage / name
                path.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(name) as stream, path.open("wb") as target:
                    shutil.copyfileobj(stream, target)
                if _sha256(path) != digest:
                    raise ValueError(f"Checksum anggota tidak cocok: {name}")
            stage.replace(destination)
    return destination


def dataset_from_mode(mode, workspace, cache, *, archive=None, urls=(), digest=""):
    if mode == "colab_instant":
        bundle = archive if archive is not None else download_subset(cache, urls, digest)
        root = extract_verified(bundle, cache / "datasets", digest)
        rgb, tif, artifacts = root / "rgb", root / "tif", root
    elif mode == "full_local":
        load_dotenv(workspace / ".env", override=False)
        rgb_dir, tif_dir = os.getenv("EUROSAT_RGB_DIR"), os.getenv("EUROSAT_ALLBANDS_DIR")
        if not rgb_dir or not tif_dir:
            raise ValueError("Isi EUROSAT_RGB_DIR dan EUROSAT_ALLBANDS_DIR untuk full_local.")
        rgb, tif = workspace / Path(rgb_dir).expanduser(), workspace / Path(tif_dir).expanduser()
        artifacts = workspace / (os.getenv("ARTIFACTS_DIR") or "artifacts")
    else:
        raise ValueError(f"Mode dataset tidak dikenal: {mode}")

    rows = read_manifest(artifacts / "manifest.csv")
    with np.load(artifacts / "index.npz", allow_pickle=False) as saved:
        index = {key: saved[key] for key in saved.files if key != "thumb_off"}
    if index["ids"].tolist() != [row["id"] for row in rows]:
        raise ValueError("ID indeks dan manifest berbeda.")
    return Dataset(index, rows, rgb, tif, perf_counter, seed=42, all_queries=mode == "colab_instant"), artifacts
