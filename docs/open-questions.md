# Pertanyaan terbuka

## M0 (ditutup 2026-11-22)

- Manifest melewati file yang namanya di luar pola ID EuroSAT dan melaporkan jumlah serta contoh nama file. Dataset lokal memiliki 597 TIFF tambahan di folder `SeaLake` (85 `Bombay_` dan 512 `Jakarta_`).
- `tools/make_colab_subset.py` selesai pada M9 (2026-11-23). Arsip memuat 2.000 pasangan, manifest subset, indeks, skala dari split latih, dan paket thumbnail. ZIP dan berkas `.sha256` tersedia di [GitHub Releases v1.0](https://github.com/AryaLaniRiyongganiNurdian/CitraSatelit/releases/tag/v1.0).

## M1 (ditutup 2026-11-22) - Input vektor Bayes dari slide

- Transjakarta vs KRL memakai prior `(0.60, 0.40)` dan likelihood `(0.10, 0.05)`. Evidence `P(TL)=0.08` dan posterior `P(T|TL)=0.75`.
- API Gateway X vs Y memakai prior `(0.70, 0.30)` dan likelihood `(0.02, 0.08)`. Evidence `P(E)=0.038` dan posterior `P(Y|E)=0.024/0.038`.

Kedua vektor dari slide sudah diaktifkan di `tests/test_probability.py`.

## M3 (ditutup 2026-11-22)

- Histogram Latihan 12 terkonfirmasi sesuai slide dosen, dengan `Q=(2,6,6,2)`, `C1=(3,5,5,3)`, dan `C2=(8,0,0,8)`. Tes Latihan 12 sudah aktif.
- kNN memilih jumlah suara terbesar, lalu total jarak terkecil. Jika masih seri, kNN memilih jarak tetangga terdekat terkecil, lalu `cls_idx` terkecil.

## M4 (ditutup 2026-11-22)

- Tamper piksel memakai MSB saat `bit=None`. Koordinat `x` menunjuk kolom dan `y` menunjuk baris. Pada RGB dan MS13, `channel=None` membalik bit di semua kanal piksel, sedangkan indeks kanal yang valid membatasi perubahan ke kanal itu.
- Tamper blok memakai `(x,y)` sebagai sudut kiri atas dan memotong blok di tepi kanan serta bawah. Setiap elemen pada blok di-XOR dengan mask acak tak nol dari RNG yang diberikan. Koordinat di luar citra dan ukuran kurang dari satu menghasilkan `ValueError`.

## M6 (ditutup 2026-11-22)

- Nama offset thumbnail pada indeks adalah `thumb_off` sesuai tabel skema.
- C4a membandingkan semua mode termasuk `mle`. Mode PMF memakai chi-square dan Euclidean, sedangkan mode momen memakai Euclidean.
- C4b memakai histogram RGB 32 bin dengan chi-square untuk P@5 share parsial.

## M7 (ditutup 2026-11-22) - Akses TIFF mentah pada deployment

Citra indeks tanpa TIFF galeri tetap dapat dicari dan memakai fitur yang sudah dihitung. Endpoint yang memerlukan piksel TIFF mentah mengembalikan `MODE_REQUIRES_MULTISPECTRAL` saat piksel tersebut tidak tersedia.

## M7 (ditutup 2026-11-22) - Band referensi untuk rekonstruksi dari unggahan

Formulir `reconstruct-upload` tidak memiliki `band_index`. Untuk share satu band, `metrics` bernilai `null` meskipun `original_image_id` diberikan. Rekonstruksi XOR dan pratinjau tetap tersedia.
