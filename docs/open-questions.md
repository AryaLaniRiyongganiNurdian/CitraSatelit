# Pertanyaan terbuka

## M0 (ditutup 2026-11-22)

- Manifest melewati file yang namanya di luar pola ID EuroSAT dan melaporkan jumlah serta contoh nama file. Dataset lokal memiliki 597 TIFF tambahan di folder `SeaLake` (85 `Bombay_` dan 512 `Jakarta_`).
- `tools/make_colab_subset.py` tetap berupa kerangka pada M0. Implementasi pembuat arsip dijadwalkan sebelum M9.

## M1 (ditutup 2026-11-22) - Input vektor Bayes dari slide

- Transjakarta vs KRL memakai prior `(0.60, 0.40)` dan likelihood `(0.10, 0.05)`. Evidence `P(TL)=0.08` dan posterior `P(T|TL)=0.75`.
- API Gateway X vs Y memakai prior `(0.70, 0.30)` dan likelihood `(0.02, 0.08)`. Evidence `P(E)=0.038` dan posterior `P(Y|E)=0.024/0.038`.

Kedua vektor dari slide sudah diaktifkan di `tests/test_probability.py`.

## M3 (ditutup 2026-11-22)

- Histogram Latihan 12 terkonfirmasi sesuai slide dosen, dengan `Q=(2,6,6,2)`, `C1=(3,5,5,3)`, dan `C2=(8,0,0,8)`. Tes Latihan 12 sudah aktif.
- kNN memilih jumlah suara terbesar, lalu total jarak terkecil. Jika masih seri, kNN memilih jarak tetangga terdekat terkecil, lalu `cls_idx` terkecil.
