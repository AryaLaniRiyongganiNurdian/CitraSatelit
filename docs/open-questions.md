# Pertanyaan terbuka

## M0 (ditutup 2026-11-22)

- Manifest melewati file yang namanya di luar pola ID EuroSAT dan melaporkan jumlah serta contoh nama file. Dataset lokal memiliki 597 TIFF tambahan di folder `SeaLake` (85 `Bombay_` dan 512 `Jakarta_`).
- `tools/make_colab_subset.py` tetap berupa kerangka pada M0. Implementasi pembuat arsip dijadwalkan sebelum M9.

## M1 (terbuka) - Input vektor Bayes dari slide

Rencana M1 hanya mencantumkan keluaran untuk dua contoh berikut.

- Transjakarta memberi `P(TL)=0.08` dan `P(T|TL)=0.75`.
- Gateway memberi `P(E)=0.038` dan `P(Y|E)=0.6316`.

Mohon berikan prior, likelihood, dan kategori hipotesis yang digunakan dari kedua slide, atau cuplikan slide terkait. Kedua kasus uji ditandai `skip` sampai input tersedia karena lebih dari satu pasangan prior dan likelihood dapat menghasilkan keluaran tersebut.
