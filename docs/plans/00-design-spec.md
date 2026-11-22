# 00 - Design Spec: Mini-CBIR & XOR Secret Sharing pada EuroSAT

Status: APPROVED
Versi: 1.0 | Seed global: 42 | Bahasa UI: Indonesia | Identifier kode: Inggris

## 0. Pemetaan ke rubrik

| Rubrik | Bobot | Dipenuhi oleh |
|---|---|---|
| Program berjalan dan benar | 25% | `src/core` murni NumPy, TDD dengan vektor uji dari slide dosen, Colab Run All, web app live |
| Percobaan dan analisis | 20% | C1, C2, C3, C4a, C4b, C4c (6 percobaan, minimal 3), analisis otomatis di `results/*.json` |
| Laporan, presentasi, tanya jawab, kontribusi | 55% | Math & Proof Inspector, Lampiran A (tanya jawab), Lampiran B (skrip demo), `AI_USAGE_LOG.md` |

## 1. Keputusan final

| ID | Keputusan |
|---|---|
| D1 | EuroSAT RGB (`.jpg`) dan EuroSATallBands (`.tif`) sama-sama lengkap 10 kelas. `synth_rgb_fallback()` tetap ada sebagai fallback dan fitur komparasi. |
| D2 | Indeks CBIR utama, C2, C4a, C4c memakai seluruh sekitar 27.000 citra. Mode `colab_instant` memakai subset 2.000 citra (200 per kelas, seed 42). |
| D3 | Split stratified 80/20, seed 42, dikunci per ID citra lewat satu `manifest.csv` sehingga identik untuk RGB dan multispektral. |
| D4 | Bayes: diskret dengan Laplace (demo Inspector) dan Gaussian NB berbasis MLE (C2). |
| D5 | Multispektral `uint16`: secret sharing XOR native `uint16`; fitur CBIR diskala ke 0..255 dengan skala persentil 2 dan 98 dari data train. |
| D6 | Web app: galeri, upload (`.jpg/.png` maks 2 MB, `.tif` maks 5 MB), live mini-experiment, download dan upload ulang share, simulasi tamper. |
| D7 | `np.bincount` boleh dipakai setelah binning integer manual `idx = (x*bins)//levels`. |
| D8 | 6 halaman: Beranda, CBIR, Secret Sharing, Boolean Lab, Percobaan, Math Inspector. Figma yang sudah ada dipetakan ke 6 halaman ini. |
| D9 | Percobaan berat dihitung offline lewat `src/experiments/run_all.py`, hasil disimpan di `results/*.json`, API hanya menyajikan. |
| D10 | Notebook Colab dibangkitkan otomatis dari `src/core/*.py` oleh `tools/build_notebook.py` (satu sumber kebenaran, tidak ada salinan manual). |

## 2. Data dan manifest

- Citra EuroSAT berukuran 64x64. Path: `RGB_DIR/<Kelas>/<Kelas>_<n>.jpg` dan `ALLBANDS_DIR/<Kelas>/<Kelas>_<n>.tif`. ID citra = `<Kelas>_<n>`, contoh `Forest_123`.
- Urutan kelas (indeks 0..9, alfabetis): AnnualCrop, Forest, HerbaceousVegetation, Highway, Industrial, Pasture, PermanentCrop, Residential, River, SeaLake.
- Urutan band `.tif`: `B01,B02,B03,B04,B05,B06,B07,B08,B8A,B09,B10,B11,B12` (indeks 0..12). Loader mendeteksi sumbu berukuran 13 lalu menormalkan ke bentuk `(H, W, 13)` `uint16`.
- Indeks spektral: `NDVI = (B08-B04)/(B08+B04)`, `NDWI = (B03-B08)/(B03+B08)`. Penyebut 0 menghasilkan 0.0. Konversi ke level: `level = clip(floor((v+1)*127.5 + 0.5), 0, 255)`.
- Sintesis RGB: kanal R=B04 (idx 3), G=B03 (idx 2), B=B02 (idx 1), masing-masing dikonversi ke 8 bit dengan skala band terkait.

`artifacts/manifest.csv` (dibuat `src/data/manifest.py`):

| kolom | isi |
|---|---|
| id, cls, cls_idx | ID, nama kelas, indeks kelas |
| split | `train` atau `test` (per kelas: urutkan ID, permutasi `default_rng(42)`, 80% pertama train) |
| rgb_path, tif_path | path relatif ke direktori dari `.env` (kosong jika file tidak ada) |
| in_gallery | 25 per kelas (15 test, 10 train, seed 42) |
| in_colab_subset | 200 per kelas, stratified, seed 42 |

Skrip wajib melaporkan ID yang hanya ada di salah satu modalitas. Split resmi EuroSAT tidak dipakai agar 80/20 tetap konsisten, dan hal ini dicatat di laporan.

## 3. Artefak

| File | Isi | Dibuat oleh |
|---|---|---|
| `artifacts/manifest.csv` | lihat di atas | `manifest.py` |
| `artifacts/scale.json` | `{"lo":[13 angka],"hi":[13 angka]}` persentil 2 dan 98 per band, dari sampel train (maks 2.000 citra) | `fit_percentile_scale` |
| `artifacts/index.npz` | lihat di bawah | `tools/build_index.py` |
| `artifacts/thumbs.pack` + `thumbs_offsets` di `index.npz` | byte JPEG asli 27.000 citra RGB (sekitar 95 MB), dipakai untuk thumbnail hasil pencarian | `build_index.py` |
| `app_assets/gallery/` | 250 citra galeri: `.jpg` dan `.tif` (sekitar 26 MB) | `tools/make_gallery.py` |
| `results/*.json` | hasil C1..C4c dalam skema `ExperimentResult` | `run_all.py` |

Isi `index.npz` (`np.savez_compressed`, N = 27.000, dimuat penuh ke RAM saat startup, sekitar 300 MB tak terkompresi):

| key | dtype | shape |
|---|---|---|
| `ids` (U32), `cls_idx` (int8), `split` (int8: 0 train, 1 test), `thumb_off` (int64, N+1) | - | N |
| `counts_gray` | uint16 | (N,256) |
| `counts_rgb`, `counts_hsv` | uint16 | (N,3,256) |
| `counts_ms` | uint16 | (N,13,256) |
| `counts_ndvi`, `counts_ndwi` | uint16 | (N,256) |
| `feat_grid2`, `feat_grid4`, `feat_mle`, `feat_ms_mle` | float32 | (N,36), (N,144), (N,6), (N,26) |
| `z_*` (mean dan std per mode momen, dari train) | float32 | sesuai |

Histogram disimpan dengan 256 bin penuh. Bin yang lebih kasar diturunkan dengan menjumlahkan `256//bins` bin berdekatan (`coarsen_counts`), hasilnya identik dengan binning langsung karena `idx=(x*bins)//256 = x//(256//bins)`.

## 4. Kontrak fungsi `src/core` (NumPy murni)

Aturan: semua RNG lewat `np.random.default_rng(seed)`. Tidak ada I/O. Impor terlarang: `scipy`, `sklearn`, `cv2`, `PIL`, `tifffile`, `skimage`. Atribut terlarang: `np.histogram*`, `np.corrcoef`, `np.cov`, `np.var`, `np.std`, `np.percentile`, `np.quantile`. Diperiksa otomatis oleh `tests/test_core_purity.py` (analisis AST). Boleh: `np.sum`, `np.mean`, `np.sqrt`, `np.exp`, `np.log`, `np.sort`, `np.bincount`, `np.bitwise_xor`, aritmetika dan indexing.

### 4.1 `stats.py`
```python
def histogram_counts(x, bins: int, levels: int = 256) -> np.ndarray   # int64 (bins,), idx=(x*bins)//levels lalu np.bincount
def coarsen_counts(counts256, bins: int) -> np.ndarray                # jumlahkan grup 256//bins
def counts_to_pmf(counts) -> np.ndarray                               # float64, jumlah=1, ValueError jika total 0
def moments_from_counts(counts, values=None) -> dict                  # mean, variance, std, skewness, kurtosis, degenerate
def mgf_empirical(values, pmf, t) -> float | np.ndarray               # sum e^{t x} p(x)
def mgf_check(counts256, h=1e-3) -> dict                              # x diskala x/255 agar tidak overflow; selisih hingga pusat vs momen eksak
def mle_gaussian(x) -> tuple[float, float]                            # (mu_hat, sigma2_hat), bagi n
def mle_bernoulli(x), mle_poisson(x), mle_exponential(x), mle_geometric(x)
```
- `mean = sum x p`, `variance = E[x^2]-mean^2`, `skewness = E[(x-mu)^3]/sigma^3`, `kurtosis = E[(x-mu)^4]/sigma^4` (normal bernilai 3).
- Jika `variance < 1e-12`: `skewness=0.0`, `kurtosis=0.0`, `degenerate=True`.
- Momen selalu dihitung dari 256 level penuh, tidak bergantung pada `bins` fitur.
- `mgf_check`: `m1_fd=(M(h)-M(-h))/(2h)` harus mendekati `E[X]` (x diskala 0..1), `m2_fd=(M(h)-2M(0)+M(-h))/h^2` mendekati `E[X^2]`.

### 4.2 `probability.py`
```python
def cond_prob(p_a_and_b, p_b) -> float                         # P(B)>0 wajib
def total_prob(priors, likelihoods) -> float
def bayes_posterior(priors, likelihoods) -> tuple[np.ndarray, float]   # (posterior, evidence)
def discrete_bayes_fit(evidence_bins, y, n_classes, levels, alpha=1.0) -> dict   # prior, likelihood (C,T), joint counts
def gaussian_nb_fit(X, y, n_classes, var_floor=1e-6) -> dict
def gaussian_nb_log_posterior(model, X) -> np.ndarray          # (N,C), normalisasi log-sum-exp manual
def chi2_uniform_stat(counts) -> float                         # sum (O-E)^2/E
def chi2_sf(x, df) -> float                                    # Wilson-Hilferty, normal CDF dari math.erf
def shannon_entropy(counts) -> float                           # bit
def pearson_r(x, y) -> float
def binom_pmf(n, k, p), geometric_pmf(k, p), geometric_mean(p), chebyshev_bound(var, r)
```
Evidence diskret: `mean_gray`, `mean_ndvi`, `mean_ndwi` dikuantisasi menjadi `levels` bin (default 8) dengan rumus bin integer. Likelihood: `(count(c,t)+alpha)/(n_c+alpha*levels)`.

### 4.3 `color.py`, `spectral.py`
```python
def rgb_to_gray(rgb_u8) -> u8         # (299R+587G+114B+500)//1000
def rgb_to_hsv(rgb_u8) -> u8 (H,W,3) # H=floor(H_deg/360*256) di-clip 255; S,V = floor(x*255+0.5)
def grid_cells(h, w, g) -> list[(r0,r1,c0,c1)]  # tepi i*H//g
def ndvi(bands_u16), ndwi(bands_u16) -> float64 (H,W)
def ndi_to_level(v) -> u8
def fit_percentile_scale(samples_u16, lo_q=2, hi_q=98) -> dict   # np.sort lalu indeks floor(q/100*(n-1))
def scale_to_8bit(bands_u16, scale) -> u8   # clip((x-lo)*255//(hi-lo), 0, 255); hi==lo -> 0
def synth_rgb(bands_u16, scale) -> u8       # (B04,B03,B02)
```

### 4.4 `cbir.py` - mode fitur

| mode | jenis | dimensi | metrik |
|---|---|---|---|
| `gray` | pmf | `bins` | euclid, chi2, intersection |
| `rgb`, `hsv` | pmf | `3*bins` | idem |
| `ms13` | pmf | `13*bins` | idem |
| `ndvi_ndwi` | pmf | `2*bins` | idem |
| `ms13_idx` | pmf | `15*bins` | idem |
| `grid2`, `grid4` | momen | 36, 144 | euclid (z-score) |
| `mle` | momen | 6 | euclid (z-score) |
| `ms_mle` | momen | 26 | euclid (z-score) |

- Fitur pmf multi-kanal: `concat(pmf_kanal) / jumlah_kanal`, sehingga total massa 1 dan irisan histogram maksimum 1.
- `grid`: per sel dan kanal RGB, urutan `[mean, std, skewness]`, sel row-major, kanal R,G,B. Std populasi.
- `mle`: per kanal RGB `(mu_hat, sqrt(sigma2_hat))`. `ms_mle`: sama untuk 13 band hasil `scale_to_8bit`.
- Mode `ms13`, `ndvi_ndwi`, `ms13_idx`, `ms_mle` wajib `needs_multispectral=true`.
- Metrik: `d_E = sqrt(sum (p-q)^2)`; `d_chi2 = sum_{p+q>0} (p-q)^2/(p+q)` (tanpa faktor 1/2, sesuai slide); `I = sum min(p,q)` dengan jarak peringkat `1-I`.
- `search_topk`: urut jarak naik, seri diputus oleh indeks naik, query sendiri dikeluarkan jika ada di database.
- `precision_at_k` = proporsi hasil sekelas query. `knn_predict`: voting top-k, seri diputus jumlah jarak terkecil.
- Fungsi lain: `extract_counts`, `counts_to_feature`, `extract_moment_feature`, `zscore_fit/apply` (std dilantai 1e-8), `distance_batch`, `confusion_matrix`.

### 4.5 `secret_sharing.py`
```python
def split_xor(arr, n, rng) -> list[np.ndarray]   # arr uint8/uint16 (bentuk bebas); n-1 share acak seragam [0,2^bits); share ke-n = arr XOR semua share acak
def reconstruct_xor(shares) -> np.ndarray
def mse(a, b) -> float ; def psnr(a, b, max_val) -> float | inf
def flip_bits(arr, p, rng, bits) -> np.ndarray   # tiap bit dibalik independen peluang p
def tamper_pixel(arr, x, y, bit=None) ; def tamper_block(arr, x, y, size, rng)
```
- Rekonstruksi wajib identik bit-exact: `MSE=0`, `PSNR=inf`.
- `security_demos.py`: `reuse_key_attack(i1, i2, rng)`, `raid5_parity(list)`, `raid5_recover(list, parity, failed)`.
- Galat bit-flip pada `k` share yang dirusak masing-masing peluang `p`: peluang efektif tiap bit `p_eff = (1-(1-2p)^k)/2`; `P(piksel salah) = 1-(1-p_eff)^b`. Untuk `k=1`: `1-(1-p)^b`.

### 4.6 `boolean_lab.py`
- Parser ekspresi: variabel satu huruf; `'` komplemen (postfix) atau `!`/`~` (prefix); AND = `.`, `*`, atau juxtaposition (`ab'`); XOR = `^` atau `⊕`; OR = `+`. Prioritas: NOT > AND > XOR > OR. Konstanta `0`, `1`. Maksimum 6 variabel untuk tabel kebenaran, 4 untuk K-Map.
- Fungsi: `parse_expr`, `eval_expr`, `truth_table`, `minterms`, `sop_canonical`, `to_circuit`, `equivalent`, `dual_expr`, `kmap` (Quine-McCluskey: implikan prima, esensial, cover greedy; tata letak K-Map urutan Gray), `XOR_DEFINITION = "ab'+a'b"`.
- Katalog bukti aljabar tertulis tangan (`LAW_PROOFS`, minimal 8): `a+a'b=a+b`, `a(a'+b)=ab`, De Morgan (2 bentuk), penyerapan (2 bentuk), `a⊕b=(a+b)(ab)'`, `a⊕b=ab'+a'b`. Identitas di luar katalog diverifikasi lewat tabel kebenaran saja.

## 5. Protokol evaluasi

- Database evaluasi: seluruh split train. Query: 50 citra test per kelas (500 query, seed 42), karena menghitung 5.400 query x 21.600 database x dimensi besar tidak praktis di NumPy. Opsi `--all-queries` tersedia di runner.
- Precision@5 per kelas = rata-rata proporsi hit sekelas pada 5 teratas. Makro = rata-rata 10 kelas. Confusion matrix 10x10 dari kNN voting (baris = kelas sebenarnya).
- Pencarian web: `database="all"` (27.000) dengan query dikeluarkan dari hasil bila ada di indeks.
- Mode `colab_instant`: database train 1.600, query test 400 (semua).

## 6. Percobaan

| ID | Tujuan | Konfigurasi | Keluaran |
|---|---|---|---|
| C1 | Pengaruh bin | mode `rgb`, metrik `chi2`, bins 8,16,32,64,128,256 | tabel P@5 makro, dimensi, waktu ekstraksi per citra (rata-rata 200 citra), waktu cari per query (rata-rata 50); grafik garis |
| C2 | Metode | `rgb` bins 32 x {euclid, chi2, intersection}; `mle` euclid; GNB (mode `mle` dan `grid2`); Bayes diskret `mean_gray` | tabel P@5/akurasi per metode, P@5 per kelas, 2 heatmap confusion (chi2 kNN dan GNB) |
| C3 | Galat bit-flip | 20 citra test (2 per kelas); `p` in {0.0005,0.001,0.005,0.01,0.02,0.05,0.1}; 30 percobaan; `b=8` (gray uint8) dan `b=16` (band B04 uint16); `k` share rusak 1 dan 2 | tabel empiris vs `1-(1-p)^b`; kurva b=8 vs 16; PMF geometrik posisi piksel salah pertama vs `(1-q)^{k-1}q`; tabel Chebyshev `P(\|X-Nq\|>=k*sigma)` vs batas `1/k^2` (k=1..5, p=0.01) |
| C4a | Modalitas pada kelas mirip | kelas Forest, Pasture, HerbaceousVegetation, AnnualCrop; semua mode kecuali `ms*` bagian dari perbandingan: gray, rgb, hsv, grid2, grid4, ms13, ndvi_ndwi, ms13_idx, ms_mle; bins 32; chi2 untuk pmf, euclid untuk momen (juga euclid untuk pmf sebagai pembanding) | tabel P@5 (acak = 0.25), confusion kNN 4x4 terbaik, temuan otomatis |
| C4b | Share parsial | `n` in {2,3,4,8}; `k=1..n`; himpunan awal-k dan akhir-k; 20 citra | tabel entropi, p-value chi2, Pearson dengan asli, MSE, P@5 CBIR (acak = 0.1); uji tamper: satu piksel diubah pada satu share mengubah tepat satu piksel hasil, selisih `2^bit` |
| C4c | Kompleksitas | ukuran database 100, 300, 1000, 3000, 10000, 27000 (mode `rgb` bins 32 chi2) | waktu per query, regresi linear manual (kemiringan, `R^2`); scan linear untuk pencocokan eksak: rata-rata perbandingan empiris vs `(n+1)/2` dari 1000 percobaan |

Setiap percobaan menulis `ExperimentResult` (lihat `api-contract.md`) dengan `findings` terhitung otomatis (misal bin terbaik, mode terbaik, apakah `p_value` share > 0.05).

## 7. Secret sharing di web dan keamanan

- `band_mode`: `gray` (uint8), `rgb` (uint8; untuk `.tif` memakai RGB sintesis ber-skala, sehingga yang dibagi adalah data uint8 hasil skala), `band` (satu band uint16 mentah), `ms13` (13 band uint16 mentah).
- Pratinjau share uint16: byte tinggi `x>>8`, ditandai di `note`.
- Uji keamanan per himpunan share: entropi Shannon (uint16 diukur pada byte tinggi), uji chi-square keseragaman 256 bin (`df=255`, alpha 0.05), Pearson dengan asli, MSE dengan asli, dan CBIR-on-share (top-5 terhadap indeks, bandingkan dengan peluang acak 0.1).
- Download share: PNG (8 atau 16 bit, mode Pillow `I;16`) atau `.npy` (wajib untuk `ms13`). Upload ulang menerima keduanya.
- Sesi in-memory: TTL 30 menit, maksimum 20 sesi (LRU). Upload citra: maksimum 64 (LRU, TTL 30 menit).

## 8. Colab

`DATASET_MODE="colab_instant"`: unduh `eurosat_subset_v1.zip` (2.000 JPG + 2.000 TIF, sekitar 170 MB) dari rilis publik tanpa API key. URL utama Hugging Face dataset repo milik Anda (`https://huggingface.co/datasets/<USER>/<REPO>/resolve/main/eurosat_subset_v1.zip`), cermin GitHub Release. Verifikasi `SHA256SUMS`, cache di `/content/data`. Dibuat sekali oleh `tools/make_colab_subset.py` (manual: Anda mengunggahnya, langkah M0).
`DATASET_MODE="full_local"`: baca `EUROSAT_RGB_DIR` dan `EUROSAT_ALLBANDS_DIR` dari `.env`.

Struktur notebook (dibangkitkan `tools/build_notebook.py` dari `src/core`):
1. Judul dan tujuan; 2. Setup dan sakelar mode; 3. Kode inti (sel hasil bangkitan); 4. Data dan manifest; 5. Demo histogram dan momen satu citra; 6. CBIR dan Precision@5; 7. Teorema Bayes; 8. Secret sharing XOR (n>=3); 9. Aljabar Boolean dan K-Map; 10. Percobaan C1..C4c (ukuran subset); 11. Analisis; 12. Kesimpulan; 13. Catatan transparansi AI.

## 9. Deploy Hugging Face Spaces (Docker)

- Dockerfile multi-stage: tahap Node membangun `frontend/dist`, tahap Python slim menjalankan `uvicorn src.api.main:app --host 0.0.0.0 --port 7860`. `README.md` Space berisi `sdk: docker`, `app_port: 7860`.
- `APP_MODE=space`: membaca `artifacts/` dan `app_assets/`. `APP_MODE=dev`: membaca dataset dari `.env`. CORS hanya untuk `http://localhost:5173` pada mode dev.
- File besar lewat Git LFS.

## 10. Non-fungsional

- Pencarian 27.000 citra: `rgb` bins 32 maksimum 0.3 detik; kasus terburuk `ms13_idx` bins 256 maksimum 2 detik (hitung per batch 2.000 baris).
- Live mini-experiment: database maksimum 600 citra, query maksimum 100, batas waktu 20 detik, kalau lebih ditolak `LIVE_LIMIT_EXCEEDED`.
- Deterministik: parameter `seed` dapat diatur, nilai bawaan 42, dikembalikan di respons.
- Semua teks penjelasan Inspector memakai Bahasa Indonesia; rumus LaTeX kompatibel KaTeX.

## Lampiran A - Latihan tanya jawab (jawaban satu kalimat)

1. Mengapa histogram bisa dianggap pmf? Karena setelah dinormalisasi nilainya tak negatif dan berjumlah 1 di atas ruang sampel intensitas.
2. Mengapa mean saja tidak cukup? Citra berbeda kontras dapat bermean sama (contoh A dan B pada slide: mean 1.5, variansi 1.0 vs 1.75).
3. Mengapa chi-square memberi bobot pada bin kecil? Pembaginya `p+q`, jadi selisih kecil pada bin sepi lebih berarti.
4. Mengapa satu share tidak membuka rahasia? `S xor R` seragam pada `{0..255}` untuk S apa pun karena R seragam dan independen.
5. Mengapa `R xor S2 = S`? `R xor (S xor R) = (R xor R) xor S = 0 xor S = S`.
6. Apa yang terjadi jika R konstan 0? Share kedua sama dengan rahasia, tidak aman.
7. Mengapa `P(piksel salah)=1-(1-p)^8`? Piksel benar hanya jika 8 bit tak ada yang terbalik, peluang tiap bit benar `1-p`, independen.
8. Mengapa `P(Y|R)=55.56%` padahal `P(R|Y)=5%`? Itu posterior, prior Y kecil (20%) tetapi tingkat rusaknya 5 kali X.
9. Mengapa NDVI membantu vegetasi? NIR (B08) dipantulkan kuat oleh klorofil, merah (B04) diserap.
10. Apa keterbatasan CBIR histogram? Tidak menyimpan posisi piksel (grid moments sebagian mengatasi).

## Lampiran B - Skrip demo (5 menit)

1. Beranda: jelaskan dua jalur (CBIR dan XOR). 2. CBIR: pilih citra Forest, mode `rgb` bins 32 chi2, buka Inspector (rumus dengan angka asli). 3. Ganti ke `ms13_idx`, tunjukkan kenaikan P@5 pada C4a. 4. Secret sharing: `n=3`, tampilkan share noise, rekonstruksi identik (MSE=0), unduh share, upload ulang. 5. Tamper satu piksel. 6. Uji keamanan (CBIR-on-share ~ 0.1). 7. Boolean Lab: K-Map majority gate. 8. Percobaan: C3 teori vs simulasi.