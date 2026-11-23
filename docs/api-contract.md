# API Contract v1.0

Sumber kebenaran data. Tipe TypeScript ada di `frontend/src/types/api.ts` (lihat `frontend-handoff.md`). Model pydantic di `src/api/schemas.py` harus bernama sama dan berbentuk sama.

## Konvensi
- Base: `/api`. Format JSON, nama field `snake_case`, tanpa `Infinity`/`NaN`.
- Angka desimal dibulatkan 6 digit. Array berisi list.
- `image_id`: ID indeks (`Forest_123`) atau ID upload (`up_<8 hex>`). Prefiks `up_` berarti upload.
- Gambar dalam JSON: objek `ImagePreview` `{data_uri, width, height, kind, note}`; `data_uri` berupa `data:image/png;base64,...`, diperbesar nearest-neighbor (parameter `scale`, bawaan 4).
- Gambar biner: `GET /images/{id}/thumb` (JPEG atau PNG) dan unduhan share.
- Tanpa autentikasi. Semua endpoint aman diulang (idempoten) kecuali yang membuat sesi atau upload.
- Format galat (HTTP 4xx/5xx):
```json
{"error": {"code": "INVALID_PARAM", "message": "bins harus salah satu dari 8,16,32,64,128,256", "details": {"field": "bins"}}}
```
- Kode galat: `IMAGE_NOT_FOUND`(404), `SESSION_NOT_FOUND`(404), `NOT_PRECOMPUTED`(404), `INVALID_PARAM`(422), `MODE_REQUIRES_MULTISPECTRAL`(422), `TIF_NOT_13_BANDS`(422), `EXPRESSION_PARSE_ERROR`(422), `SHAPE_MISMATCH`(422), `LIVE_LIMIT_EXCEEDED`(422), `FORMAT_NOT_SUPPORTED`(422), `UPLOAD_TOO_LARGE`(413), `UNSUPPORTED_FILE`(415), `INTERNAL_ERROR`(500).
- Batas: upload `.jpg/.png` 2 MB, `.tif` 5 MB, sisi terpanjang 1024 piksel. Sesi sharing TTL 30 menit.

## Inspector (panel Math & Proof)
Setiap endpoint komputasi mengembalikan `inspector: Inspector`:
```json
{"title": "Jarak chi-square", "steps": [
  {"id": "chi2-formula", "title": "Rumus", "latex_template": "d_{\\chi^2}(p,q)=\\sum_i \\frac{(p_i-q_i)^2}{p_i+q_i}",
   "latex_substituted": null, "explanation": "Selisih kuadrat dibagi jumlah, bin kecil lebih berbobot.", "values": {}, "table": null, "chart": null},
  {"id": "chi2-numbers", "title": "Substitusi angka", "latex_template": null,
   "latex_substituted": "d=\\frac{(0.250-0.312)^2}{0.562}+\\cdots=0.016", "explanation": "Angka dari citra aktif.", "values": {"d": 0.016},
   "table": {"columns": ["bin","p","q","(p-q)^2/(p+q)"], "rows": [[0,0.25,0.3125,0.0069]], "caption": "5 kontribusi terbesar"}, "chart": null}
]}
```
Aturan: `latex_*` kompatibel KaTeX; `explanation` Bahasa Indonesia; langkah selalu terurut; `id` stabil (dipakai test dan sebagai React key). Jumlah langkah minimum per endpoint ada di kolom "Inspector" tabel bawah.

## Daftar endpoint

| Metode dan path | Request | Response | Inspector (id minimum) |
|---|---|---|---|
| `GET /health` | - | `HealthResponse` | - |
| `GET /meta` | - | `MetaResponse` | - |
| `GET /images` | query: `cls?`, `split?`, `gallery_only?=true`, `limit?=50`, `offset?=0` | `ImagesListResponse` | - |
| `GET /images/{id}/thumb` | - | biner gambar | - |
| `GET /images/{id}/preview` | query: `view=rgb\|synth_rgb\|ndvi\|ndwi\|band`, `band?=0..12`, `scale?=4` | `ImagePreview` | - |
| `POST /images/upload` | multipart `file` | `ImageMeta` | - |
| `POST /cbir/features` | `FeaturesRequest` | `FeaturesResponse` | `counts`, `pmf`, `moments`, `mle`, `mgf` (mode pmf); `moment-table` (mode momen) |
| `POST /cbir/search` | `SearchRequest` | `SearchResponse` | `metric-formula`, `metric-numbers` (query vs hasil ke-1), `precision` |
| `POST /cbir/bayes` | `BayesRequest` | `BayesResponse` | `prior`, `likelihood`, `evidence`, `posterior`, `conditional` |
| `POST /cbir/gnb` | `GnbRequest` | `GnbResponse` | `mle-per-class`, `log-likelihood`, `posterior` |
| `GET /cbir/evaluate` | query: `mode`, `bins`, `metric` | `EvaluateResponse` | - |
| `POST /live/cbir` | `LiveCbirRequest` | `EvaluateResponse` (`source:"live"`) | - |
| `POST /live/bins` | `LiveBinsRequest` | `LiveBinsResponse` | - |
| `POST /sharing/split` | `SplitRequest` | `SplitResponse` | `bits`, `random-shares`, `last-share`, `reconstruction-proof` |
| `GET /sharing/{session_id}/share/{index}/download` | query: `format=png\|npy` | biner (`Content-Disposition: attachment`) | - |
| `POST /sharing/reconstruct` | `ReconstructRequest` | `ReconstructResponse` | `xor-chain`, `result` |
| `POST /sharing/reconstruct-upload` | multipart: `files` (2..8), `original_image_id?`, `band_mode?` | `ReconstructResponse` | `xor-chain`, `result` |
| `POST /sharing/tamper` | `TamperRequest` | `TamperResponse` | `tamper`, `effect` |
| `POST /sharing/security` | `SecurityRequest` | `SecurityResponse` | `uniform-theory`, `chi2`, `entropy`, `cbir-on-share` |
| `POST /sharing/bitflip` | `BitflipRequest` | `BitflipResponse` | `binomial`, `geometric`, `chebyshev` |
| `POST /sharing/attacks/reuse-key` | `ReuseKeyRequest` | `ReuseKeyResponse` | `encrypt`, `xor-of-ciphers`, `leak` |
| `POST /sharing/attacks/raid5` | `Raid5Request` | `Raid5Response` | `parity`, `recover`, `limit` |
| `POST /inspector/pixel-xor` | `PixelXorRequest` | `PixelXorResponse` | `binary`, `xor`, `reconstruct` |
| `GET /boolean/laws` | - | `BooleanLaw[]` | - |
| `POST /boolean/truth-table` | `TruthTableRequest` | `TruthTableResponse` | `parse`, `table`, `sop` |
| `POST /boolean/prove` | `ProveRequest` | `ProveResponse` | `table-proof`, `algebraic` (jika ada), `dual` |
| `POST /boolean/xor-gate` | `{}` | `XorGateResponse` | `definition`, `table`, `circuit` |
| `POST /boolean/kmap` | `KMapRequest` | `KMapResponse` | `grid`, `groups`, `result` |
| `GET /experiments` | - | `ExperimentSummary[]` | - |
| `GET /experiments/{id}` | `id` in `C1,C2,C3,C4a,C4b,C4c` | `ExperimentResult` | - |

## Semantik penting

**Fitur dan pencarian**
- `bins` hanya berpengaruh pada mode pmf. Mode momen mengabaikannya, respons mengembalikan `bins` yang dipakai (kosong tidak diizinkan: kirim nilai bawaan 32).
- Mode `ms13`, `ndvi_ndwi`, `ms13_idx`, `ms_mle` pada upload `.jpg/.png` memberi `MODE_REQUIRES_MULTISPECTRAL`. Mode RGB pada upload `.tif` memakai RGB sintesis.
- Metrik pada mode momen selalu `euclid`; metrik lain memberi `INVALID_PARAM`.
- `precision_at_k` bernilai `null` untuk upload (kelas tak diketahui).
- Hasil `distance` untuk `intersection` adalah `1-I`; `similarity` berisi `I`.

**Bayes**
- `evidence` in `mean_gray`, `mean_ndvi`, `mean_ndwi`; dua terakhir butuh multispektral. `levels` 4..16, `alpha` > 0.
- `rows[*].posterior` berjumlah 1 (toleransi 1e-9). `conditional_example` mengambil kelas dengan posterior tertinggi sebagai event A dan bin bukti sebagai event B.

**Sharing**
- `n` 2..8. `band_mode` `band` wajib `band_index` 0..12; `ms13` mengabaikan `band_index` kecuali untuk pratinjau (`preview_band`).
- `reconstruction.identical` harus `true` pada `split`. `psnr_db=null` dan `psnr_is_infinite=true` bila MSE 0.
- `reconstruct` dengan `share_indices=null` memakai semua share. Himpunan lebih sedikit dari `n` memberi `is_complete=false` dan pratinjau berupa derau.
- `tamper.mode`: `pixel` (butuh `x`,`y`, opsional `bit`), `bitflip` (butuh `p`), `block` (butuh `x`,`y`,`block_size`). Sesi tidak diubah.
- `security.subsets` berisi himpunan awal-k dan akhir-k untuk `k=1..n` (duplikat dihapus). `reveals_secret=true` hanya pada `k=n`.
- `bitflip`: `p` dalam (0, 0.5], `p_list` maksimum 12 nilai, `trials` maksimum 30, `corrupted_shares` 1..n. `theory_curves` selalu memuat `bits` 8 dan 16.

**Boolean**
- Variabel satu huruf; maksimum 6 (tabel), 4 (K-Map). `minterms` K-Map dalam rentang `0..2^variables-1`; urutan bit: variabel pertama = bit paling signifikan.
- `prove.algebraic_proof` hanya terisi untuk identitas di katalog. `GET /boolean/laws` menyajikan kedua sisi identitas dan langkah `ProofStep` dari katalog yang sama.
- Evaluasi ekspresi dan rangkaian memakai `truth-table`. Ekuivalensi dan dualitas memakai `prove`. Definisi dan rangkaian XOR tersedia di `xor-gate`.

**Percobaan**
- `GET /cbir/evaluate` hanya melayani kombinasi terhitung: semua pasangan mode-metrik yang valid pada `bins=32`, dan `mode=rgb` untuk semua `bins`. Selain itu `NOT_PRECOMPUTED` dengan `details.available`.
- `live`: database `db_per_class` 5..60 (maks 600 total), `queries_per_class` 1..10, `seed` bawaan 42. Database dari split train, query dari split test pada indeks.

## Contoh ringkas

`POST /api/cbir/search`
```json
{"image_id": "Forest_101", "mode": "rgb", "bins": 32, "metric": "chi2", "k": 5, "database": "all"}
```
Respons (dipangkas):
```json
{"query": {"id": "Forest_101", "cls": "Forest", "split": "test", "width": 64, "height": 64, "bands": 3, "has_rgb": true, "has_ms": true, "in_gallery": true, "is_upload": false, "thumb_url": "/api/images/Forest_101/thumb"},
 "mode": "rgb", "bins": 32, "metric": "chi2", "k": 5, "database": "all", "db_size": 26999,
 "hits": [{"rank": 1, "id": "Forest_873", "cls": "Forest", "split": "train", "distance": 0.0213, "similarity": null, "same_class": true, "thumb_url": "/api/images/Forest_873/thumb"}],
 "precision_at_k": 0.8, "elapsed_ms": {"feature": 0.4, "search": 142.0}, "inspector": {"title": "Pencarian CBIR", "steps": []}}
```

`POST /api/sharing/split`
```json
{"image_id": "River_12", "n": 3, "band_mode": "gray", "band_index": null, "seed": 42}
```
Respons (dipangkas):
```json
{"session_id": "s_9f3a1c2e", "n": 3, "band_mode": "gray", "shape": [64, 64], "dtype": "uint8", "bits": 8, "seed": 42,
 "original_preview": {"data_uri": "data:image/png;base64,...", "width": 256, "height": 256, "kind": "original", "note": null},
 "shares": [{"index": 0, "preview": {"data_uri": "data:image/png;base64,...", "width": 256, "height": 256, "kind": "share", "note": null}, "histogram": [], "entropy_bits": 7.97, "chi2": {"stat": 241.3, "df": 255, "p_value": 0.71, "uniform_at_alpha_0_05": true}, "download_urls": {"png": "/api/sharing/s_9f3a1c2e/share/0/download?format=png", "npy": "/api/sharing/s_9f3a1c2e/share/0/download?format=npy"}}],
 "reconstruction": {"identical": true, "mse": 0.0, "psnr_db": null, "psnr_is_infinite": true, "pixels_different": 0, "max_abs_diff": 0},
 "inspector": {"title": "Secret sharing (3,3)", "steps": []}}
```

`POST /api/boolean/kmap`
```json
{"variables": 3, "minterms": [1, 3, 4, 5]}
```
Respons (dipangkas): `"simplified": "a'c + ab'"`, `"col_labels": ["00","01","11","10"]`, `"grid": [[0,1,1,0],[1,1,0,0]]`.

## Penentuan skema `ExperimentResult`
Lihat tipe di `api.ts`. `tables` dan `charts` bersifat generik; frontend merender apa adanya. `findings` adalah daftar kalimat siap tampil. `analysis_md` adalah Markdown pendek (maksimum 1.500 karakter) berisi jawaban dari "Kapan CBIR berhasil dan gagal? Mengapa share tampak seperti noise? Apa kaitan kedua bagian?" yang relevan dengan percobaan tersebut.