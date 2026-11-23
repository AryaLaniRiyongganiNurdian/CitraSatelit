import csv
import io
import shutil
from time import monotonic

import numpy as np
import pytest
import tifffile
from fastapi.testclient import TestClient
from PIL import Image

from src.api.main import create_app
from src.data.env import Settings
from src.experiments.run_all import run_smoke
from tools.build_index import build_index


@pytest.fixture(scope="module")
def fixture_data(tmp_path_factory):
    root = tmp_path_factory.mktemp("api")
    rgb, bands, artifacts = (root / name for name in ("rgb", "tif", "artifacts"))
    for folder in (rgb, bands, artifacts):
        folder.mkdir()
    rng = np.random.default_rng(42)
    rows = []
    for cls, cls_idx in (("Forest", 1), ("River", 8)):
        for i in range(4):
            key = f"{cls}_{i}"
            Image.fromarray(rng.integers(0, 256, (8, 9, 3), dtype=np.uint8)).save(rgb / f"{key}.jpg")
            tifffile.imwrite(bands / f"{key}.tif", rng.integers(0, 1000, (8, 9, 13), dtype=np.uint16),
                             photometric="minisblack")
            rows.append(dict(id=key, cls=cls, cls_idx=cls_idx, split="train" if i < 3 else "test",
                             rgb_path=f"{key}.jpg", tif_path=f"{key}.tif", in_gallery=True,
                             in_colab_subset=False))
    manifest = artifacts / "manifest.csv"
    with manifest.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    build_index(manifest, rgb, bands, artifacts)
    run_smoke(root / "results")
    return root, Settings(rgb, bands, "dev", artifacts, 42)


@pytest.fixture
def client(fixture_data, tmp_path):
    root, settings = fixture_data
    app = create_app(settings, results_dir=root / "results", dist_dir=tmp_path / "dist")
    with TestClient(app) as browser:
        yield browser


def ok(response, ids=()):
    assert response.status_code == 200, response.text[:1000]
    assert "Infinity" not in response.text and "NaN" not in response.text
    payload = response.json()
    if ids:
        assert set(ids) <= {step["id"] for step in payload["inspector"]["steps"]}
        assert all(step["explanation"] for step in payload["inspector"]["steps"])
    return payload


def test_index_images_cbir_and_live(client):
    assert ok(client.get("/api/health"))["n_images"] == 8
    assert ok(client.get("/api/meta"))["dataset"]["n_train"] == 6
    assert ok(client.get("/api/images?cls=Forest"))["total"] == 4
    assert client.get("/api/images/Forest_0/thumb").headers["content-type"] == "image/jpeg"
    assert ok(client.get("/api/images/Forest_0/preview?view=ndvi&scale=2"))["width"] == 18
    features = dict(image_id="Forest_0", mode="rgb", bins=32)
    ok(client.post("/api/cbir/features", json=features), ("counts", "pmf", "moments", "mle", "mgf"))
    ok(client.post("/api/cbir/features", json=features | {"mode": "mle"}), ("moment-table",))
    params = features | {"metric": "chi2"}
    result = ok(client.post("/api/cbir/search", json=params), ("metric-formula", "metric-numbers", "precision"))
    assert result["db_size"] == 7 and all(hit["id"] != "Forest_0" for hit in result["hits"])
    ok(client.post("/api/cbir/bayes", json=dict(image_id="Forest_0", evidence="mean_ndvi")),
       ("prior", "likelihood", "evidence", "posterior", "conditional"))
    ok(client.post("/api/cbir/gnb", json=dict(image_id="Forest_0", mode="mle")),
       ("mle-per-class", "log-likelihood", "posterior"))
    assert ok(client.get("/api/cbir/evaluate?mode=rgb&metric=chi2&bins=32"))["source"] == "precomputed"
    assert ok(client.post("/api/live/cbir", json=dict(mode="rgb", bins=32, metric="chi2")))["source"] == "live"
    assert len(ok(client.post("/api/live/bins", json=dict(mode="rgb", bins_list=[8, 32], metric="chi2")))["points"]) == 2
    assert len(ok(client.get("/api/experiments"))) == 6
    assert ok(client.get("/api/experiments/C1"))["id"] == "C1"


def test_sharing_round_trip_and_demos(client):
    split = ok(client.post("/api/sharing/split", json=dict(image_id="Forest_0", n=3, band_mode="gray")),
               ("bits", "random-shares", "last-share", "reconstruction-proof"))
    assert split["reconstruction"]["psnr_db"] is None
    assert split["reconstruction"]["psnr_is_infinite"]
    req = dict(session_id=split["session_id"])
    files = []
    for share in split["shares"]:
        downloaded = client.get(share["download_urls"]["png"])
        assert downloaded.status_code == 200 and "attachment" in downloaded.headers["content-disposition"]
        files.append(("files", (f"{share['index']}.png", downloaded.content, "image/png")))
    response = client.post("/api/sharing/reconstruct-upload", files=files,
                           data={"original_image_id": "Forest_0", "band_mode": "gray"})
    assert ok(response, ("xor-chain", "result"))["metrics"]["identical"]
    ok(client.post("/api/sharing/reconstruct", json=req), ("xor-chain", "result"))
    result = ok(client.post("/api/sharing/tamper", json=req | dict(share_index=0, mode="pixel", x=1, y=2)),
                ("tamper", "effect"))
    assert result["metrics"]["pixels_different"] == 1
    ok(client.post("/api/sharing/security", json=req | {"run_cbir": True}),
       ("uniform-theory", "chi2", "entropy", "cbir-on-share"))
    ok(client.post("/api/sharing/bitflip", json=req | dict(trials=2, p_list=[0.01])),
       ("binomial", "geometric", "chebyshev"))
    ok(client.post("/api/sharing/attacks/reuse-key", json=dict(image_id_1="Forest_0", image_id_2="River_0")),
       ("encrypt", "xor-of-ciphers", "leak"))
    ok(client.post("/api/sharing/attacks/raid5", json=dict(image_ids=["Forest_0", "Forest_1", "River_0"], failed_index=1)),
       ("parity", "recover", "limit"))
    ok(client.post("/api/inspector/pixel-xor", json=dict(image_id="Forest_0", x=0, y=0, n=3, channel="gray")),
       ("binary", "xor", "reconstruct"))
    client.app.state.data.sessions.clock = lambda: monotonic() + 1801
    error(client.post("/api/sharing/reconstruct", json=req), 404, "SESSION_NOT_FOUND")


def test_boolean_laws(client):
    response = client.get("/api/boolean/laws")
    assert response.status_code == 200
    laws = response.json()
    assert len(laws) >= 8
    for law in laws:
        assert law["steps"][0]["expression"] == law["lhs"]
        assert law["steps"][-1]["expression"] == law["rhs"]
        proof = client.post("/api/boolean/prove", json={key: law[key] for key in ("lhs", "rhs")})
        assert proof.status_code == 200
        assert proof.json()["equivalent"] is True


def test_boolean(client):
    ok(client.post("/api/boolean/truth-table", json={"expression": "a^b"}), ("parse", "table", "sop"))
    ok(client.post("/api/boolean/prove", json={"lhs": "a+a'b", "rhs": "a+b"}), ("table-proof", "algebraic", "dual"))
    ok(client.post("/api/boolean/xor-gate", json={}), ("definition", "table", "circuit"))
    assert ok(client.post("/api/boolean/kmap", json={"variables": 3, "minterms": [1, 3, 4, 5]}),
              ("grid", "groups", "result"))["simplified"] == "a'c + ab'"


def error(response, status, code):
    assert response.status_code == status, response.text[:1000]
    payload = response.json()["error"]
    assert set(payload) == {"code", "message", "details"}
    assert payload["code"] == code


def blob(data, fmt):
    stream = io.BytesIO()
    Image.fromarray(data).save(stream, format=fmt)
    return stream.getvalue()


def test_uploads_and_contract_errors(client):
    source = np.zeros((8, 9), dtype=np.uint8)
    png = blob(source, "PNG")
    image = ok(client.post("/api/images/upload", files={"file": ("image.png", png)}))
    assert image["is_upload"]
    error(client.post("/api/cbir/features", json=dict(image_id=image["id"], mode="ms13", bins=32)),
          422, "MODE_REQUIRES_MULTISPECTRAL")
    error(client.get("/api/images/unknown/thumb"), 404, "IMAGE_NOT_FOUND")
    error(client.get("/api/cbir/evaluate?mode=hsv&metric=chi2&bins=8"), 404, "NOT_PRECOMPUTED")
    error(client.post("/api/cbir/features", json=dict(image_id="Forest_0", mode="rgb", bins=4)), 422, "INVALID_PARAM")
    error(client.post("/api/boolean/truth-table", json={"expression": "a+"}), 422, "EXPRESSION_PARSE_ERROR")
    error(client.post("/api/live/cbir", json=dict(mode="rgb", bins=32, metric="chi2", db_per_class=61)),
          413, "LIVE_LIMIT_EXCEEDED")
    error(client.post("/api/images/upload", files={"file": ("image.exe", b"xyz")}), 415, "UNSUPPORTED_FILE")
    error(client.post("/api/images/upload", files={"file": ("image.tif", blob(source, "TIFF"))}),
          422, "TIF_NOT_13_BANDS")
    for name, mb in (("large.jpg", 2), ("large.png", 2), ("large.tif", 5)):
        error(client.post("/api/images/upload", files={"file": (name, b"x" * (mb * 1024**2 + 1))}),
              413, "UPLOAD_TOO_LARGE")
    error(client.post("/api/sharing/reconstruct-upload", files=[
        ("files", ("a.png", png)), ("files", ("b.png", blob(source[:3], "PNG"))),
    ]), 422, "SHAPE_MISMATCH")
    split = ok(client.post("/api/sharing/split", json=dict(image_id="Forest_0", n=2, band_mode="ms13")))
    error(client.get(f"/api/sharing/{split['session_id']}/share/0/download?format=png"),
          422, "FORMAT_NOT_SUPPORTED")


def test_static_mount_coexists_with_api(fixture_data, tmp_path, client):
    assert client.get("/docs").status_code == 200
    dist = tmp_path / "available"
    dist.mkdir()
    (dist / "index.html").write_text("Fixture frontend", encoding="utf-8")
    root, settings = fixture_data
    with TestClient(create_app(settings, results_dir=root / "results", dist_dir=dist)) as browser:
        for path in ("/", "/cbir", "/sharing", "/boolean", "/percobaan", "/inspector"):
            assert browser.get(path).text == "Fixture frontend"
        assert browser.get("/api/health").status_code == 200
        assert browser.get("/openapi.json").status_code == 200


def test_space_index_features_work_without_raw_nongallery_tiff(fixture_data, tmp_path):
    root, settings = fixture_data
    space = Settings(None, None, "space", settings.artifacts_dir, 42)
    with TestClient(create_app(space, results_dir=root / "results", gallery_dir=tmp_path)) as browser:
        error(browser.get("/api/images/Forest_0/preview?view=ndvi"), 422, "MODE_REQUIRES_MULTISPECTRAL")
        error(browser.post("/api/sharing/split", json=dict(image_id="Forest_0", n=2, band_mode="ms13")),
              422, "MODE_REQUIRES_MULTISPECTRAL")
        assert ok(browser.post("/api/cbir/features", json=dict(image_id="Forest_0", bins=32, mode="ms13")))["dim"] == 416


def test_space_gallery_discovery_without_manifest(fixture_data, tmp_path):
    root, settings = fixture_data
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    for name in ("index.npz", "thumbs.pack", "scale.json"):
        shutil.copyfile(settings.artifacts_dir / name, artifacts / name)
    gallery = tmp_path / "gallery"
    gallery.mkdir()
    shutil.copyfile(settings.allbands_dir / "Forest_0.tif", gallery / "Forest_0.tif")

    space = Settings(None, None, "space", artifacts, 42)
    with TestClient(create_app(space, results_dir=root / "results", gallery_dir=gallery)) as browser:
        assert ok(browser.get("/api/meta"))["dataset"]["gallery_size"] == 1
        images = ok(browser.get("/api/images?gallery_only=true"))
        assert [image["id"] for image in images["items"]] == ["Forest_0"]
        ok(browser.get("/api/images/Forest_0/preview?view=ndvi"))
        error(browser.get("/api/images/Forest_1/preview?view=ndvi"), 422, "MODE_REQUIRES_MULTISPECTRAL")


@pytest.mark.parametrize("mode,download_format", [("band", "png"), ("ms13", "npy")])
def test_uint16_shares_roundtrip_without_reference(client, mode, download_format):
    split = ok(client.post("/api/sharing/split", json=dict(
        image_id="Forest_0", n=2, band_mode=mode, band_index=3 if mode == "band" else 0,
    )))
    files = []
    for item in split["shares"]:
        result = client.get(item["download_urls"][download_format])
        assert result.status_code == 200
        files.append(("files", (f"{item['index']}.{download_format}", result.content)))
    restored = ok(client.post("/api/sharing/reconstruct-upload", files=files, data={"band_mode": mode}),
                  ("xor-chain", "result"))
    assert restored["is_complete"] and restored["metrics"] is None
    assert restored["preview"]["data_uri"] == split["original_preview"]["data_uri"]
    if mode == "band":
        with_reference = ok(client.post(
            "/api/sharing/reconstruct-upload", files=files,
            data={"band_mode": "band", "original_image_id": "Forest_0"},
        ))
        assert with_reference["metrics"] is None
        assert with_reference["preview"] == restored["preview"]


def test_internal_errors_use_contract_format(fixture_data, monkeypatch):
    root, settings = fixture_data
    app = create_app(settings, results_dir=root / "results")
    with TestClient(app, raise_server_exceptions=False) as browser:
        def fail(image_id):
            raise RuntimeError("fixture failure")
        monkeypatch.setattr(app.state.data, "meta", fail)
        error(browser.get("/api/images/Forest_0/thumb"), 500, "INTERNAL_ERROR")
