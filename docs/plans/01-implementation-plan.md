# 01 - Implementation Plan (Strict TDD)

Aturan kerja untuk Codex:
1. Tulis test dulu (merah), baru implementasi (hijau), refactor kecil. Satu milestone = satu cabang/commit berurutan.
2. Jangan menebak. Jika spesifikasi di `00-design-spec.md` atau `docs/api-contract.md` ambigu, hentikan dan tulis pertanyaan di `docs/open-questions.md`.
3. `src/core` tidak boleh impor pustaka terlarang (dijaga `tests/test_core_purity.py`).
4. Referensi `scipy`, `sklearn`, `cv2`, `colorsys` hanya di `tests/`.
5. Jalankan `pytest -q` sebelum menyatakan selesai. Catat pemakaian AI di `AI_USAGE_LOG.md`.

Perintah standar: `pytest -q`, `pytest -q tests/test_<modul>.py`, `uvicorn src.api.main:app --reload --port 8000`, `npm run dev` (di `frontend/`).

## M0 - Scaffold dan data tooling
Berkas: `pyproject.toml`/`requirements.txt` (numpy, pillow, tifffile, fastapi, uvicorn, pydantic, python-multipart, matplotlib, seaborn, python-dotenv), `requirements-dev.txt` (pytest, scipy, scikit-learn, opencv-python-headless, httpx, nbformat), `.env.example` (`EUROSAT_RGB_DIR`, `EUROSAT_ALLBANDS_DIR`, `APP_MODE`, `ARTIFACTS_DIR`, `SEED=42`), `AI_USAGE_LOG.md`, `src/data/{env,loader,manifest}.py`, `tools/{build_index,make_gallery,make_colab_subset,build_notebook}.py` (kerangka).
Test: `test_core_purity.py`; `test_manifest.py` (split 80/20 per kelas, deterministik, ID identik lintas modalitas, jumlah `in_gallery`=25/kelas, `in_colab_subset`=200/kelas); `test_loader.py` (tif dinormalkan ke `(64,64,13)` `uint16`, jpg ke `(64,64,3)` `uint8`, memakai file fixture kecil).
Selesai bila: `pytest` hijau, `manifest.csv` terbentuk dari dataset lokal, laporan ID tak sinkron tercetak.
Langkah manual Anda: unggah `eurosat_subset_v1.zip` setelah `make_colab_subset.py` dijalankan.

## M1 - `stats.py` dan `probability.py`
Test (vektor dari slide, toleransi 1e-9 kecuali disebut):
- Histogram 4x4: piksel `[0,0,1,1,0,1,1,2,1,2,2,3,2,2,3,3]` dengan 4 level memberi counts `(3,5,5,3)`, mean 1.5, variansi 1.0, E[X^2]=3.25.
- Citra Q counts `(4,5,4,3)`: mean 1.375, variansi 1.109375, skewness 0.1706 (toleransi 1e-3). A `(3,5,5,3)`: 1.5, 1.0, 0. B `(6,2,2,6)`: 1.5, 1.75, 0.
- Binning: untuk semua `x` 0..255 dan `bins` dalam {8..256}, `histogram_counts` sama dengan `np.histogram` (di test) dan `coarsen_counts(h256,bins)` sama dengan `histogram_counts` langsung.
- MGF: `Binomial(10,0.8)` `M(t)=(0.2+0.8e^t)^10`, `M'(0)=8`, `M''(0)=65.6`; `mgf_check` selisih hingga mendekati momen (toleransi 1e-4 dan 1e-2).
- MLE: Gaussian `[100,120,110,130]` memberi `(115,125)`; Poisson `[5,7,4,6,8]` memberi 6; eksponensial `[2,3,1,4]` memberi 2.5; Bernoulli 8 dari 10 memberi 0.8; geometrik `n/sum x`.
- Bayes: `P(R)=0.018`, `P(Y|R)=0.5556`; Transjakarta `P(TL)=0.08`, `P(T|TL)=0.75`; Gateway `P(E)=0.038`, `P(Y|E)=0.6316`.
- Probabilitas bersyarat: `16/100 / (40/100) = 0.40`.
- `chi2_sf` vs `scipy.stats.chi2.sf` untuk `df` 30..255 (selisih < 0.01); `shannon_entropy` seragam 256 = 8 bit; `pearson_r` vs `np.corrcoef`.
- `binom_pmf` vs `scipy.stats.binom`; `geometric_mean(0.2)=5`; `chebyshev_bound`.
- Gaussian NB pada data sintetis dua klaster terpisah memberi akurasi 1.0; hasil dibandingkan `sklearn.GaussianNB` dengan `var_smoothing` setara.
Selesai bila: semua hijau, tidak ada warning numerik.

## M2 - `color.py` dan `spectral.py`
Test: `rgb_to_gray` vs Pillow `convert("L")` (selisih maks 1); `rgb_to_hsv` vs `colorsys` (selisih maks 1 pada skala 0..255); `grid_cells` menutup citra tanpa tumpang tindih untuk ukuran tidak habis dibagi; NDVI/NDWI nilai tangan (misal B08=3000, B04=1000 memberi 0.5); penyebut nol memberi 0; `ndi_to_level(-1)=0`, `(0)=128`, `(1)=255`; `fit_percentile_scale` vs `np.percentile` (selisih 1 level); `scale_to_8bit` clip dan band konstan; `synth_rgb` urutan kanal.

## M3 - `cbir.py`
Test: dimensi tiap mode sesuai tabel Design Spec; fitur multi-kanal berjumlah 1; vektor uji slide: `d_E(Q,A)=0.0884`, `d_E(Q,B)=0.3187`, `d_chi2(Q,A)=0.01587`, `d_chi2(Q,B)=0.2095`, `I(Q,A)=0.9375`, `I(Q,B)=0.6875`; Latihan 12: `d_E(Q,C1)=0.125`, `I=0.875`, `d_E(Q,C2)=0.75`, `I=0.25`; mean ketiganya 1.5, variansi `0.75, 1.0, 2.25`; urutan hasil A sebelum B; tie-break deterministik; query dikeluarkan dari hasil; `distance_batch` vs implementasi loop; `precision_at_k`, confusion matrix; z-score memakai statistik train; grid moments pada citra seragam memberi std 0 dan skewness 0; mode multispektral pada input tanpa `bands` memberi `ValueError`.
Selesai bila: semua hijau dan benchmark kecil (`27000 x 96` chi2) di bawah 0.3 detik.

## M4 - `secret_sharing.py`, `security_demos.py`
Test: `S=150,R=100` memberi `S2=242`; skema (2,2) `S=173,R=60` memberi `S2=145`; skema (3,3) `S=100,R1=25,R2=77` memberi `S3=48`; rekonstruksi bit-exact untuk `uint8` dan `uint16`, `n` 2..8, bentuk `(H,W)`, `(H,W,3)`, `(H,W,13)`; bukti tabel kebenaran `R xor (S xor R) = S`; share acak lolos uji chi-square (p > 0.001 pada 20 seed); `n-1` share bukan rahasia (MSE besar, Pearson mendekati 0); `flip_bits` dengan `p=0` tidak mengubah, `p=1` membalik semua; frekuensi empiris `1-(1-p)^b` dalam 3 sigma binomial untuk `b=8,16`; `p_eff` untuk `k=2`; reuse key: `01001000 xor 10110101 = 11111101` dan `C1 xor C2 = 00100001 = M1 xor M2`; RAID-5: `D1=1010,D2=0111,D3=1100` memberi `P=0001` dan pemulihan `D2=0111` untuk setiap disk gagal; tamper satu piksel mengubah tepat satu piksel hasil.

## M5 - `boolean_lab.py`
Test: parser (prioritas, juxtaposition, `'`, `^`, kurung, kesalahan sintaks memberi `ExpressionError`); `ab'+a'b` sama dengan `a^b` pada seluruh 4 baris; `a+a'b=a+b` ekuivalen; De Morgan; dual dari `a+a'b=a+b` adalah `a(a'+b)=ab` dan ekuivalen; K-Map: `Σm(0,2)` (2 var) memberi `b'`, `Σm(0,2,4,6)` memberi `c'`, `Σm(1,3,4,5)` memberi `a'c+ab'`, `Σm(1,3,5,7)` memberi `c`, `Σm(3,5,6,7)` memberi `xy+xz+yz` (majority), 4 variabel dengan lipatan tepi (misal `Σm(0,2,8,10)=b'd'`); semua hasil dicek ulang dengan `equivalent` terhadap fungsi asal; tata letak Gray `00,01,11,10`; katalog `LAW_PROOFS` setiap langkah ekuivalen secara tabel.

## M6 - Indeks dan percobaan
Berkas: `tools/build_index.py` (multiprocess 4 proses), `src/experiments/{c1_bins,c2_metrics,c3_bitflip,c4a_modalities,c4b_partial_shares,c4c_complexity,run_all,common}.py`.
Test: `test_build_index.py` pada fixture 30 citra sintetis (skema key, dtype, shape, `coarsen` konsisten); `test_experiments_smoke.py` menjalankan tiap percobaan pada fixture kecil dan memvalidasi skema `ExperimentResult`; determinisme (dua kali jalan, hasil identik).
Selesai bila: `python -m src.experiments.run_all --config smoke` hijau; `python tools/build_index.py` dan `run_all --config full` menghasilkan `artifacts/index.npz` dan `results/*.json`. Catat waktu dan ukuran file.
Save precomputed EvaluateResponse payloads to results/eval_cache.json for all valid mode–metric pairs at bins=32 and mode=rgb across all bins.

## M7 - API FastAPI
Berkas: `src/api/{main,schemas,state,inspector,errors}.py`, `routers/{images,cbir,sharing,boolean,experiments,live,inspector}.py`.
Test (`httpx`/`TestClient`, indeks fixture kecil): setiap endpoint di `docs/api-contract.md` mengembalikan JSON yang lolos model pydantic; setiap kode galat yang didaftarkan dapat dipicu; Inspector setiap endpoint punya minimal langkah yang dijanjikan kontrak (jumlah dan `id`); sesi kedaluwarsa memberi `SESSION_NOT_FOUND`; batas upload; `psnr_is_infinite` bukan `Infinity`/`NaN` di JSON; static mount `frontend/dist` di `/` dan `/api/*` tetap jalan; contoh JSON di kontrak lulus uji kontrak (`tests/test_api_contract.py` memuat contoh dari `docs/api-contract.md`).
Selesai bila: `pytest` hijau dan `/docs` OpenAPI tampil.

## M8 - Frontend (React + Figma)
Ikuti `docs/frontend-handoff.md` dan desain Figma di `docs/design/` (atau frame Figma terhubung).
Kerjakan secara bertahap agar fidelitas Figma terjaga:
- **M8.1 (Setup & Design Tokens):** Inisialisasi Vite + React + TS + Tailwind + `shadcn/ui` + `sonner` + `[Magic UI / Aceternity UI]`. Override styling default `shadcn/ui` dengan token desain Figma (Font, Border Radius, Brand Colors di `index.css` / `tailwind.config`). Bangun App Shell, navigasi 6 rute, dan halaman Beranda.
- **M8.2 (Core Interactive Pages):** Bangun `/cbir` dan `/sharing` per section mengikuti tangkapan layar Figma dan endpoint di `docs/api-contract.md`.
- **M8.3 (Lab, Percobaan & Inspector):** Bangun `/boolean`, `/percobaan`, dan `/inspector` (termasuk drawer `InspectorView` dengan KaTeX).
- **M8.4 (Audit & Verifikasi):** Pastikan seluruh toast galat/sukses memakai `sonner`, animasi `[Magic UI / Aceternity UI]` hanya di area yang ditentukan, responsif (1280px & 768px), dan kontras terbaca jelas di proyektor.

Test & Selesai bila: `vitest` hijau untuk util dan komponen Inspector; `tsc --noEmit` bersih tanpa `any`; `npm run build` menghasilkan `frontend/dist`; semua panggilan API lewat `frontend/src/lib/api.ts` bertipe dari `frontend/src/types/api.ts`.

## M9 - Notebook Colab
`tools/build_notebook.py` merakit sel dari `src/core/*.py` dan kerangka narasi. Test: `test_notebook_build.py` (JSON valid via `nbformat`, tidak ada impor terlarang pada sel kode inti, kedua nilai `DATASET_MODE` tersedia). Uji manual: Run All di Colab pada mode `colab_instant` tanpa error, waktu total di bawah 15 menit.

## M10 - Docker dan Hugging Face
`Dockerfile`, `.dockerignore`, `README.md` Space, uji `docker build` dan jalan lokal di `localhost:7860`, uji performa di Design Spec bagian 10, pengecekan ukuran repo dan LFS. Daftar periksa akhir: semua test hijau, `AI_USAGE_LOG.md` terisi, tautan Space dan notebook di laporan.

## Prompt siap tempel untuk Codex (per milestone)
```
Baca docs/plans/00-design-spec.md dan docs/plans/01-implementation-plan.md. Kerjakan milestone <Mx> saja.
Tulis test dulu, tunjukkan merah, lalu implementasi sampai hijau. Jangan mengubah kontrak.
Jika ada ambiguitas, tulis di docs/open-questions.md dan berhenti pada bagian itu.
Akhiri dengan ringkasan: file dibuat, hasil pytest, hal yang perlu keputusan saya.
```