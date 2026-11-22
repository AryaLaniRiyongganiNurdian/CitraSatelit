import io
import json
from collections import OrderedDict
from threading import RLock
from time import monotonic

import numpy as np
from PIL import Image

from src.api.errors import ApiError
from src.core.color import rgb_to_gray
from src.core.spectral import synth_rgb
from src.data.loader import load_rgb, load_tif
from src.data.manifest import CLASSES
from tools.build_index import read_manifest


class ExpiringLRU:
    def __init__(self, limit, missing_code):
        self.entries = OrderedDict()
        self.lock = RLock()
        self.limit = limit
        self.missing_code = missing_code
        self.clock = monotonic

    def put(self, key, payload):
        with self.lock:
            now = self.clock()
            for old, (deadline, _) in list(self.entries.items()):
                if deadline <= now:
                    del self.entries[old]
            self.entries[key] = (now + 1800, payload)
            while len(self.entries) > self.limit:
                self.entries.popitem(last=False)

    def get(self, key):
        with self.lock:
            entry = self.entries.get(key)
            if entry is None or entry[0] <= self.clock():
                self.entries.pop(key, None)
                raise ApiError(self.missing_code, "Data tidak ditemukan atau kedaluwarsa.")
            self.entries.move_to_end(key)
            return entry[1]


class State:
    def __init__(self, settings, results, gallery):
        self.settings = settings
        self.results = results
        self.gallery = gallery
        self.uploads = ExpiringLRU(64, "IMAGE_NOT_FOUND")
        self.sessions = ExpiringLRU(20, "SESSION_NOT_FOUND")
        self.feature_lock = RLock()
        self.cached_features = None
        artifacts = settings.artifacts_dir
        manifest = artifacts / "manifest.csv"
        self.manifest = {row["id"]: row for row in read_manifest(manifest)} if manifest.is_file() else {}
        self.index = {}
        index = artifacts / "index.npz"
        if index.is_file():
            with np.load(index, allow_pickle=False) as saved:
                self.index = {key: saved[key] for key in saved.files}
        self.ids = self.index.get("ids", np.array([], dtype=str)).tolist()
        self.positions = {key: i for i, key in enumerate(self.ids)}
        self.scale = read_json(artifacts / "scale.json", {"lo": [0] * 13, "hi": [65535] * 13})
        self.cache = read_json(results / "eval_cache.json", {})
        self.size = (64, 64)
        if self.ids and (artifacts / "thumbs.pack").is_file():
            with Image.open(io.BytesIO(self.packed(self.ids[0]))) as image:
                self.size = image.size

    def meta(self, key):
        if key.startswith("up_"):
            return self.uploads.get(key)[0]
        if key not in self.positions:
            raise ApiError("IMAGE_NOT_FOUND", "Citra tidak ditemukan.", image_id=key)
        i = self.positions[key]
        row = self.manifest.get(key, {})
        width, height = self.size
        return dict(id=key, cls=CLASSES[self.index["cls_idx"][i]],
                    split=("train", "test")[self.index["split"][i]], width=width, height=height,
                    bands=3, has_rgb=True, has_ms=True, in_gallery=row.get("in_gallery") == "True",
                    is_upload=False, thumb_url=f"/api/images/{key}/thumb")

    def packed(self, key):
        i = self.positions[key]
        offsets = self.index["thumb_off"]
        with (self.settings.artifacts_dir / "thumbs.pack").open("rb") as stream:
            stream.seek(int(offsets[i]))
            return stream.read(int(offsets[i + 1] - offsets[i]))

    def rgb(self, key):
        meta = self.meta(key)
        if meta["is_upload"]:
            return self.uploads.get(key)[1]
        row = self.manifest.get(key, {})
        if self.settings.app_mode == "dev" and self.settings.rgb_dir and row.get("rgb_path"):
            return load_rgb(self.settings.rgb_dir / row["rgb_path"])
        return load_rgb(io.BytesIO(self.packed(key)))

    def bands(self, key):
        meta = self.meta(key)
        if meta["is_upload"]:
            array = self.uploads.get(key)[2]
            if array is not None:
                return array
        else:
            row = self.manifest.get(key, {})
            if self.settings.app_mode == "dev" and self.settings.allbands_dir and row.get("tif_path"):
                return load_tif(self.settings.allbands_dir / row["tif_path"])
            file = self.gallery / f"{key}.tif"
            if file.is_file():
                return load_tif(file)
        raise ApiError("MODE_REQUIRES_MULTISPECTRAL", "Data piksel multispektral tidak tersedia.", image_id=key)

    def source(self, key, mode, band=None):
        if mode == "rgb":
            return self.rgb(key)
        if mode == "gray":
            return rgb_to_gray(self.rgb(key))
        image = self.bands(key)
        if mode == "band":
            if band is None or not 0 <= band < 13:
                raise ApiError("INVALID_PARAM", "Pilih band 0 sampai 12.", field="band_index")
            return image[..., band]
        return image

    def add_upload(self, key, rgb, bands):
        if rgb is None:
            rgb = synth_rgb(bands, self.scale)
        height, width = rgb.shape[:2]
        meta = dict(id=key, cls=None, split=None, width=width, height=height, bands=13 if bands is not None else 3,
                    has_rgb=True, has_ms=bands is not None, in_gallery=False, is_upload=True,
                    thumb_url=f"/api/images/{key}/thumb")
        self.uploads.put(key, (meta, rgb, bands))
        return meta


def read_json(path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default
