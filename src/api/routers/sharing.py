import io
import uuid
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from PIL import Image
from starlette.responses import Response

from src.api import schemas as s
from src.api.errors import ApiError, RESPONSES
from src.api.inspector import explain, preview
from src.api.routers.cbir import check_k, rank_hits
from src.api.routers.images import read_upload
from src.core import cbir, probability as prob, secret_sharing as xor
from src.core.security_demos import raid5_parity, raid5_recover, reuse_key_attack
from src.core.stats import histogram_counts

router = APIRouter(prefix="/sharing", responses=RESPONSES)


@dataclass
class Session:
    original: np.ndarray
    shares: list
    mode: str
    band: int
    cls: str | None


def histogram(array):
    return histogram_counts(array >> 8 if array.dtype == np.uint16 else array, 256)


def statistics(array):
    counts = histogram(array)
    stat = prob.chi2_uniform_stat(counts)
    p = prob.chi2_sf(stat, 255)
    return counts.tolist(), prob.shannon_entropy(counts), dict(
        stat=stat, df=255, p_value=p, uniform_at_alpha_0_05=p > 0.05,
    )


def metrics(original, reconstructed):
    if original.shape != reconstructed.shape or original.dtype != reconstructed.dtype:
        raise ApiError("SHAPE_MISMATCH", "Bentuk atau tipe share berbeda dari citra asli.")
    delta = np.abs(original.astype(np.int32) - reconstructed.astype(np.int32))
    error = xor.mse(original, reconstructed)
    psnr = xor.psnr(original, reconstructed, np.iinfo(original.dtype).max)
    pixels = np.any(delta, axis=-1) if delta.ndim == 3 else delta
    return dict(identical=error == 0, mse=error, psnr_db=None if error == 0 else psnr,
                psnr_is_infinite=error == 0, pixels_different=int(np.count_nonzero(pixels)),
                max_abs_diff=int(delta.max()))


@router.post("/split", response_model=s.SplitResponse, response_model_exclude_unset=True)
def split(req: s.SplitRequest, request: Request):
    data = request.app.state.data
    if not 2 <= req.n <= 8:
        raise ApiError("INVALID_PARAM", "Jumlah share harus 2 sampai 8.", field="n")
    original = data.source(req.image_id, req.band_mode, req.band_index)
    seed = data.settings.seed if req.seed is None else req.seed
    shares = xor.split_xor(original, req.n, np.random.default_rng(seed))
    band = req.band_index if req.band_mode == "ms13" and req.band_index is not None else 0
    if not 0 <= band < 13:
        raise ApiError("INVALID_PARAM", "Band pratinjau harus 0 sampai 12.")
    session_id = f"s_{uuid.uuid4().hex[:8]}"
    items = []
    for i, share in enumerate(shares):
        counts, entropy, chi2 = statistics(share)
        url = f"/api/sharing/{session_id}/share/{i}/download"
        items.append(dict(index=i, preview=preview(share, "share", band=band), histogram=counts,
                          entropy_bits=entropy, chi2=chi2,
                          download_urls={"png": None if req.band_mode == "ms13" else url+"?format=png",
                                         "npy": url+"?format=npy"}))
    data.sessions.put(session_id, Session(original, shares, req.band_mode, band, data.meta(req.image_id)["cls"]))
    bits = np.iinfo(original.dtype).bits
    return dict(session_id=session_id, n=req.n, band_mode=req.band_mode, shape=list(original.shape),
                dtype=str(original.dtype), bits=bits, seed=seed, original_preview=preview(original, "original", band=band),
                shares=items, reconstruction=metrics(original, xor.reconstruct_xor(shares)),
                inspector=explain("Pembagian XOR", "bits", "random-shares", "last-share", "reconstruction-proof",
                                  detail={"bits": {"values": {"bits": bits, "n": req.n}}}))


def _share(session, index):
    if not 0 <= index < len(session.shares):
        raise ApiError("INVALID_PARAM", "Indeks share di luar batas.")
    return session.shares[index]


@router.get("/{session_id}/share/{index}/download", response_class=Response,
            responses={200: {"content": {"image/png": {}, "application/octet-stream": {}}}})
def download(session_id: str, index: int, request: Request, format: str = Query("png")):
    session = request.app.state.data.sessions.get(session_id)
    array = _share(session, index)
    stream = io.BytesIO()
    if format == "npy":
        np.save(stream, array, allow_pickle=False)
        mime = "application/octet-stream"
    elif format == "png" and session.mode != "ms13":
        Image.fromarray(array).save(stream, format="PNG")
        mime = "image/png"
    else:
        raise ApiError("FORMAT_NOT_SUPPORTED", "Format share ini tidak didukung.")
    return Response(stream.getvalue(), media_type=mime,
                    headers={"Content-Disposition": f'attachment; filename="share_{index}.{format}"'})


def reconstruction(shares, indices, total, original=None, band=0):
    restored = xor.reconstruct_xor(shares)
    return dict(used_indices=indices, n_total=total, is_complete=len(indices) == total,
                preview=preview(restored, "reconstruction", band=band),
                metrics=None if original is None else metrics(original, restored),
                entropy_bits=prob.shannon_entropy(histogram(restored)),
                inspector=explain("Rekonstruksi", "xor-chain", "result",
                                  detail={"xor-chain": {"values": {"jumlah_share": len(indices)}}}))


@router.post("/reconstruct", response_model=s.ReconstructResponse, response_model_exclude_unset=True)
def reconstruct(req: s.ReconstructRequest, request: Request):
    session = request.app.state.data.sessions.get(req.session_id)
    indices = list(range(len(session.shares))) if req.share_indices is None else req.share_indices
    if not indices or len(set(indices)) != len(indices):
        raise ApiError("INVALID_PARAM", "Pilih indeks share yang unik.")
    return reconstruction([_share(session, index) for index in indices], indices,
                          len(session.shares), session.original, session.band)


def _read_npy(stream):
    version = np.lib.format.read_magic(stream)
    readers = {(1, 0): np.lib.format.read_array_header_1_0, (2, 0): np.lib.format.read_array_header_2_0}
    reader = readers.get(version)
    if reader is None:
        raise ValueError("unsupported NPY version")
    shape, _, dtype = reader(stream)
    if len(shape) not in (2, 3) or not all(0 < v <= 1024 for v in shape[:2]) or (
        len(shape) == 3 and shape[-1] not in (3, 13)
    ) or dtype not in (np.uint8, np.uint16):
        raise ValueError("invalid NPY shape or dtype")
    stream.seek(0)
    return np.load(stream, allow_pickle=False)


@router.post("/reconstruct-upload", response_model=s.ReconstructResponse, response_model_exclude_unset=True)
async def reconstruct_upload(request: Request, files: list[UploadFile] = File(...),
                             original_image_id: str | None = Form(None), band_mode: s.BandMode | None = Form(None)):
    if not 2 <= len(files) <= 8:
        raise ApiError("INVALID_PARAM", "Unggah 2 sampai 8 share.")
    shares = []
    for file in files:
        suffix = Path(file.filename or "").suffix.lower()
        stream = await read_upload(file, 28 * 1024**2)
        try:
            if suffix == ".npy":
                array = _read_npy(stream)
            elif suffix == ".png" and band_mode != "ms13":
                with Image.open(stream, formats=["PNG"]) as image:
                    if max(image.size) > 1024:
                        raise ApiError("UPLOAD_TOO_LARGE", "Sisi share melebihi batas.")
                    if image.mode not in ("L", "RGB", "I", "I;16", "I;16B"):
                        raise ValueError("unexpected PNG bands")
                    array = np.asarray(image, dtype=np.uint16 if image.mode.startswith("I") else np.uint8)
            else:
                raise ValueError("unexpected share format")
        except (OSError, EOFError, ValueError) as exc:
            raise ApiError("FORMAT_NOT_SUPPORTED", "Share harus berupa PNG atau NPY yang valid.") from exc
        shares.append(array)
    first = shares[0]
    if any(arr.shape != first.shape or arr.dtype != first.dtype for arr in shares):
        raise ApiError("SHAPE_MISMATCH", "Bentuk atau tipe share tidak sama.")
    if first.ndim == 2:
        inferred = "gray" if first.dtype == np.uint8 else "band"
    elif first.shape[-1] == 3 and first.dtype == np.uint8:
        inferred = "rgb"
    elif first.shape[-1] == 13 and first.dtype == np.uint16:
        inferred = "ms13"
    else:
        raise ApiError("FORMAT_NOT_SUPPORTED", "Jumlah kanal dan tipe share tidak didukung.")
    if band_mode is not None and band_mode != inferred:
        raise ApiError("SHAPE_MISMATCH", "Bentuk share berbeda dari band_mode yang dipilih.")
    original = None
    if original_image_id is not None:
        data = request.app.state.data
        if inferred == "band":
            data.meta(original_image_id)
        else:
            original = data.source(original_image_id, inferred)
    return reconstruction(shares, list(range(len(shares))), len(shares), original)


@router.post("/tamper", response_model=s.TamperResponse, response_model_exclude_unset=True)
def tamper(req: s.TamperRequest, request: Request):
    data = request.app.state.data
    session = data.sessions.get(req.session_id)
    source = _share(session, req.share_index)
    rng = np.random.default_rng(data.settings.seed if req.seed is None else req.seed)
    if req.mode == "pixel" and req.x is not None and req.y is not None:
        modified = xor.tamper_pixel(source, req.x, req.y, req.bit)
    elif req.mode == "block" and None not in (req.x, req.y, req.block_size):
        modified = xor.tamper_block(source, req.x, req.y, req.block_size, rng)
    elif req.mode == "bitflip" and req.p is not None:
        modified = xor.flip_bits(source, req.p, rng, np.iinfo(source.dtype).bits)
    else:
        raise ApiError("INVALID_PARAM", "Lengkapi parameter simulasi tamper.")
    shares = session.shares.copy()
    shares[req.share_index] = modified
    restored = xor.reconstruct_xor(shares)
    delta = np.abs(session.original.astype(np.int32) - restored).astype(source.dtype)
    changed = int(np.count_nonzero(source != modified))
    return dict(share_index=req.share_index, changed_values=changed,
                tampered_share_preview=preview(modified, "tampered", band=session.band),
                reconstruct_preview=preview(restored, "reconstruction", band=session.band),
                diff_preview=preview(delta, "difference", band=session.band),
                metrics=metrics(session.original, restored),
                inspector=explain("Simulasi tamper", "tamper", "effect",
                                  detail={"effect": {"values": {"elemen_berubah": changed}}}))


def _share_feature(data, array, mode, bins):
    bands = array if array.ndim == 3 and array.shape[-1] == 13 else None
    if cbir.MODE_INFO[mode]["needs_multispectral"] and bands is None:
        raise ApiError("MODE_REQUIRES_MULTISPECTRAL", "Mode membutuhkan share 13 band.")
    rgb = None
    if bands is None:
        array = (array >> 8).astype(np.uint8) if array.dtype == np.uint16 else array
        rgb = np.repeat(array[..., None], 3, axis=-1) if array.ndim == 2 else array
    args = dict(rgb=rgb, bands=bands, scale=data.scale)
    if cbir.MODE_INFO[mode]["kind"] == "pmf":
        return cbir.counts_to_feature(cbir.extract_counts(mode, **args), bins)
    moment = cbir.extract_moment_feature(mode, **args)
    return cbir.zscore_apply(moment, data.index[f"z_{mode}_mean"], data.index[f"z_{mode}_std"])


@router.post("/security", response_model=s.SecurityResponse, response_model_exclude_unset=True)
def security(req: s.SecurityRequest, request: Request):
    data = request.app.state.data
    session = data.sessions.get(req.session_id)
    cls = session.cls
    n = len(session.shares)
    subsets = []
    for k in range(1, n + 1):
        choices = [("awal", list(range(k)))]
        if k < n:
            choices.append(("akhir", list(range(n-k, n))))
        for label, idx in choices:
            partial = xor.reconstruct_xor([session.shares[i] for i in idx])
            _, entropy, chi2 = statistics(partial)
            pearson = prob.pearson_r(session.original, partial)
            scores = None
            if req.run_cbir and cls is not None:
                mode, bins, metric = req.mode or "rgb", req.bins or 32, req.metric or "chi2"
                query = _share_feature(data, partial, mode, bins)
                hits, precision, _ = rank_hits(data, query, cls, mode, metric, bins,
                                               check_k(5 if req.k is None else req.k))
                if precision is not None:
                    scores = dict(precision_at_k=precision, chance_level=0.1, hits=hits)
            subsets.append(dict(label=f"{label}-{k}", k_shares=k, subset=idx, entropy_bits=entropy, chi2=chi2,
                                pearson_r_with_original=pearson if np.isfinite(pearson) else None,
                                mse_vs_original=xor.mse(session.original, partial), cbir=scores, reveals_secret=k == n))
    return dict(n=n, bits=np.iinfo(session.original.dtype).bits, subsets=subsets,
                theory=dict(p_uniform=1/256, max_entropy_bits=8, statement="Share parsial berdistribusi seragam."),
                inspector=explain("Uji keamanan", "uniform-theory", "chi2", "entropy", "cbir-on-share"))


@router.post("/bitflip", response_model=s.BitflipResponse, response_model_exclude_unset=True)
def bitflip(req: s.BitflipRequest, request: Request):
    data = request.app.state.data
    session = data.sessions.get(req.session_id)
    trials = req.trials if req.trials is not None else 30
    damaged = req.corrupted_shares if req.corrupted_shares is not None else 1
    if not (1 <= trials <= 30 and 1 <= damaged <= len(session.shares)
            and 1 <= len(req.p_list) <= 12 and all(0 < p <= 0.5 for p in req.p_list)):
        raise ApiError("INVALID_PARAM", "Parameter percobaan bit-flip tidak valid.")
    focus = req.p_focus if req.p_focus is not None else req.p_list[0]
    if not 0 < focus <= 0.5:
        raise ApiError("INVALID_PARAM", "p_focus harus dalam (0, 0,5].")
    original = session.original
    n = original.shape[0] * original.shape[1]
    channels = original.shape[-1] if original.ndim == 3 else 1
    bits = np.iinfo(original.dtype).bits
    rng = np.random.default_rng(data.settings.seed if req.seed is None else req.seed)
    samples = {}

    def effective(p):
        return 0.5 if p == 0.5 else float(-np.expm1(damaged * np.log1p(-2 * p)) / 2)

    def theory(p, width):
        return float(-np.expm1(width * channels * np.log1p(-effective(p))))

    def simulate(p):
        counts, first = [], []
        for _ in range(trials):
            corrupted = [xor.flip_bits(share, p, rng, bits) for share in session.shares[:damaged]]
            delta = xor.reconstruct_xor(corrupted + session.shares[damaged:]) != original
            if delta.ndim == 3:
                delta = delta.any(axis=-1)
            wrong = np.flatnonzero(delta)
            counts.append(len(wrong))
            first.append(int(wrong[0]) + 1 if len(wrong) else 0)
        return np.asarray(counts), np.asarray(first)

    points = []
    for p in dict.fromkeys([*req.p_list, focus]):
        samples[p] = simulate(p)
    for p in req.p_list:
        counts, _ = samples[p]
        observed = counts.mean() / n
        expected = theory(p, bits)
        points.append(dict(p=p, p_effective=effective(p), empirical_pixel_error=observed,
                           empirical_std=float(np.sqrt(np.mean((counts - counts.mean()) ** 2))) / n,
                           theory_pixel_error=expected, abs_diff=abs(observed-expected),
                           mean_wrong_pixels=counts.mean(), n_pixels=n))
    counts, first = samples[focus]
    q = theory(focus, bits)
    mu, sigma = n*q, np.sqrt(n*q*(1-q))
    positions = list(range(1, min(n, 64)+1))
    observed_positions = first[first > 0]
    geometric = dict(p_wrong=q, k=positions,
                     pmf_theory=[prob.geometric_pmf(k, q) for k in positions],
                     pmf_empirical=[float(np.mean(first == k)) for k in positions],
                     mean_theory=prob.geometric_mean(q),
                     mean_empirical=float(observed_positions.mean()) if len(observed_positions) else 0)
    chebyshev = dict(p_focus=focus, mu=mu, sigma=sigma,
                     rows=[dict(k_sigma=k, r=k*sigma, bound=1/k**2,
                                empirical_tail=float(np.mean(np.abs(counts-mu) >= k*sigma)))
                           for k in range(1, 6)])
    curves = [dict(bits=width, p=req.p_list, error=[theory(p, width) for p in req.p_list])
              for width in (8, 16)]
    chart = dict(kind="line", title="Galat piksel", x=req.p_list,
                 series=[dict(name="Empiris", y=[point["empirical_pixel_error"] for point in points]),
                         dict(name="Teori", y=[point["theory_pixel_error"] for point in points])])
    return dict(bits=bits, n_pixels=n, points=points, theory_curves=curves, geometric=geometric,
                chebyshev=chebyshev, chart=chart,
                inspector=explain("Simulasi bit-flip", "binomial", "geometric", "chebyshev"))


@router.post("/attacks/reuse-key", response_model=s.ReuseKeyResponse, response_model_exclude_unset=True)
def reuse(req: s.ReuseKeyRequest, request: Request):
    data = request.app.state.data
    first, second = data.rgb(req.image_id_1), data.rgb(req.image_id_2)
    if first.shape != second.shape:
        raise ApiError("SHAPE_MISMATCH", "Kedua citra harus mempunyai bentuk yang sama.")
    rng = np.random.default_rng(data.settings.seed if req.seed is None else req.seed)
    demo = reuse_key_attack(first, second, rng)
    m1, m2, key = 0x48, 0x69, 0xB5
    c1, c2 = m1 ^ key, m2 ^ key
    scalar = {field: f"{value:08b}" for field, value in dict(m1=m1, m2=m2, k=key, c1=c1, c2=c2,
                                                             c1_xor_c2=c1^c2, m1_xor_m2=m1^m2).items()}
    scalar["equal"] = c1 ^ c2 == m1 ^ m2
    arrays = {"i1": first, "i2": second} | {key: demo[key] for key in ("c1", "c2", "c1_xor_c2", "i1_xor_i2")}
    return dict(scalar_demo=scalar, previews={key: preview(value, key) for key, value in arrays.items()},
                identical=bool(np.array_equal(demo["c1_xor_c2"], demo["i1_xor_i2"])),
                key_recovered_from_known_plaintext=bool(np.array_equal(demo["key"], demo["recovered_key"])),
                inspector=explain("Reuse key", "encrypt", "xor-of-ciphers", "leak"))


@router.post("/attacks/raid5", response_model=s.Raid5Response, response_model_exclude_unset=True)
def raid(req: s.Raid5Request, request: Request):
    if len(req.image_ids) < 2 or not 0 <= req.failed_index < len(req.image_ids):
        raise ApiError("INVALID_PARAM", "Pilih minimal dua blok dan indeks yang valid.")
    data = request.app.state.data
    arrays = [data.rgb(key) for key in req.image_ids]
    if any(array.shape != arrays[0].shape for array in arrays):
        raise ApiError("SHAPE_MISMATCH", "Bentuk blok harus sama.")
    parity = raid5_parity(arrays)
    recovered = raid5_recover(arrays, parity, req.failed_index)
    example = [np.array(i, dtype=np.uint8) for i in (10, 7, 12)]
    demo_index = req.failed_index % len(example)
    p = raid5_parity(example)
    rebuilt = raid5_recover(example, p, demo_index)
    return dict(scalar_demo=dict(d=[f"{int(i):04b}" for i in example], p=f"{int(p):04b}",
                                 failed_index=demo_index, recovered=f"{int(rebuilt):04b}",
                                 ok=bool(rebuilt == example[demo_index])),
                previews=dict(disks=[preview(array, "disk") for array in arrays],
                              parity=preview(parity, "parity"), recovered=preview(recovered, "recovered")),
                identical=bool(np.array_equal(recovered, arrays[req.failed_index])),
                limitation="Satu paritas hanya memulihkan satu blok hilang.",
                inspector=explain("RAID-5", "parity", "recover", "limit"))
