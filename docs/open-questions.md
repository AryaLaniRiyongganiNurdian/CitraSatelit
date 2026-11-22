# Pertanyaan terbuka

## M0 (ditutup 2026-11-22)

- Manifest melewati file yang namanya di luar pola ID EuroSAT dan melaporkan jumlah serta contoh nama file. Dataset lokal memiliki 597 TIFF tambahan di folder `SeaLake` (85 `Bombay_` dan 512 `Jakarta_`).
- `tools/make_colab_subset.py` tetap berupa kerangka pada M0. Implementasi pembuat arsip dijadwalkan sebelum M9.

## M1 (ditutup 2026-11-22) - Input vektor Bayes dari slide

- Transjakarta vs KRL memakai prior `(0.60, 0.40)` dan likelihood `(0.10, 0.05)`. Evidence `P(TL)=0.08` dan posterior `P(T|TL)=0.75`.
- API Gateway X vs Y memakai prior `(0.70, 0.30)` dan likelihood `(0.02, 0.08)`. Evidence `P(E)=0.038` dan posterior `P(Y|E)=0.024/0.038`.

Kedua vektor dari slide sudah diaktifkan di `tests/test_probability.py`.

## M3 (terbuka) - Histogram asli Latihan 12

Rencana M3 mencantumkan jarak, irisan, serta momen untuk Q, C1, dan C2, tetapi tidak menyertakan histogram masukan. Jika setiap histogram memiliki empat level dan 16 piksel, kandidat yang memenuhi semua target adalah Q=(2,6,6,2), C1=(3,5,5,3), dan C2=(8,0,0,8).

Apakah ketiga histogram itu persis sama dengan slide? Tes Latihan 12 menunggu konfirmasi input.

## M3 (terbuka) - Seri penuh pada voting kNN

Kontrak memecah seri jumlah suara dengan total jarak terkecil. Jika total jarak juga identik, kelas mana yang harus dipilih? Implementasi menghentikan prediksi untuk kasus itu sambil menunggu aturan lanjutan.
