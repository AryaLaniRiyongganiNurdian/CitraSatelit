---
title: CitraSatelit ORBITAL
emoji: 🛰️
colorFrom: gray
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# CitraSatelit ORBITAL

Laboratorium interaktif berbahasa Indonesia untuk mencari citra satelit berdasarkan isi (CBIR) dan mempelajari pembagian rahasia XOR. Lab Boolean memperlihatkan hubungan ekspresi, tabel kebenaran, peta Karnaugh, dan rangkaian. Inspektor Matematika menampilkan rumus dan substitusi angka dari komputasi yang sedang ditinjau.

## Arsitektur

- `src/core/` mengimplementasikan statistik, probabilitas, fitur spektral, CBIR, XOR, dan aljabar Boolean dengan Python dan NumPy.
- FastAPI menyajikan API, indeks 27.000 citra EuroSAT dalam 10 kelas, hasil percobaan, dan build statis.
- React, TypeScript, dan Vite menyusun antarmuka ORBITAL dengan enam halaman.

## Hasil percobaan EuroSAT

| ID | Temuan |
| --- | --- |
| C1 | Histogram 32 bin mencapai P@5 tertinggi, yaitu 0,7432 pada 500 kueri. |
| C2 | RGB dengan jarak chi-square mencapai akurasi tertinggi, yaitu 79,60% pada 500 kueri. |
| C3 | Selisih maksimum antara peluang empiris dan teori adalah 0,0005 pada citra 16 bit dengan peluang bit terbalik 0,1. |
| C4a | Mode `ms13` dengan chi-square mencapai P@5 0,9510 pada 200 kueri dari empat kelas. Acuan tebak acak adalah 0,2500. |
| C4b | P@5 tertinggi dari share parsial adalah 0,1000, sama dengan acuan tebak acak. Proporsi rata-rata uji share parsial dengan p-value > 0,05 adalah 0,9423. |
| C4c | Pada 27.000 citra, pencarian sekuensial membutuhkan rata-rata 13.292,4 perbandingan dibanding teori 13.500,5. Regresi waktu menghasilkan 0,000355 ms/citra dan R² 0,9999. |

Data, konfigurasi, dan ukuran sampel tersedia di [results/](results/).

## Menjalankan secara lokal

Gunakan Python 3.12 dan Node.js 24. Dari akar repositori, buat dan aktifkan lingkungan virtual Python (`source .venv/bin/activate` pada shell POSIX atau `.venv\Scripts\Activate.ps1` di PowerShell). Untuk membuat artefak dari data mentah, salin `.env.example` ke `.env` dan isi `EUROSAT_RGB_DIR` serta `EUROSAT_ALLBANDS_DIR` dengan lokasi masing-masing varian EuroSAT yang telah diekstrak.

```sh
python -m venv .venv
```

Setelah lingkungan virtual aktif, siapkan artefak dan build frontend.

```sh
pip install -r requirements.txt
python -m src.data.manifest
python -m tools.build_index
python -m tools.make_gallery
python -m src.experiments.run_all --config full
npm --prefix frontend ci
npm --prefix frontend run build
```

Jalankan perintah berikut dari akar repositori, lalu buka [localhost:7860](http://localhost:7860/). Gunakan `APP_MODE=dev` di `.env` untuk akses dataset lokal penuh atau tetapkan `APP_MODE=space` di lingkungan proses untuk menyimulasikan deployment.

```sh
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 7860
```

## Hugging Face Spaces

Buat Space dengan SDK Docker. Kemas `artifacts/index.npz`, `artifacts/thumbs.pack`, `artifacts/scale.json`, `app_assets/gallery/`, dan JSON produksi di `results/`. Jalankan `git lfs install` sebelum menambahkan berkas biner, lalu periksa bahwa `git lfs ls-files` mencantumkan indeks, pack thumbnail, serta pasangan JPG/TIFF galeri sebelum mendorong commit ke Space. Checkout yang sudah memiliki pointer LFS dapat mengambil isinya dengan `git lfs pull`. Build Docker memerlukan berkas hasil unduhan LFS. Ikuti langkah konfigurasi Space di [dokumentasi Hugging Face](https://huggingface.co/docs/hub/spaces-sdks-docker).

Uji image secara lokal dari akar repositori.

```sh
docker build -t citrasatelit .
docker run --rm -p 7860:7860 citrasatelit
```

Untuk mengatur CTA Colab, tambahkan variabel build `VITE_COLAB_NOTEBOOK_URL` pada Space atau berikan `--build-arg VITE_COLAB_NOTEBOOK_URL="$VITE_COLAB_NOTEBOOK_URL"` saat build lokal. Jika nilai kosong, CTA membuka beranda Colab. Container berjalan sebagai UID 1000 dan melayani seluruh indeks serta fitur prahitung. Operasi yang memerlukan piksel TIFF tersedia untuk 250 citra galeri dan unggahan multispektral.

## Google Colab

Buka [notebook CitraSatelit](notebooks/citrasatelit.ipynb) di Colab, pilih profil `colab_instant`, lalu jalankan seluruh sel. Buat subset lokal dengan `python -m tools.make_colab_subset`. Unggah ZIP dan berkas `.sha256` ke `/content`, atau atur `COLAB_SUBSET_URL` ke arsip rilis dengan berkas checksum di sampingnya. Notebook membawa salinan kode sumber untuk bootstrap mandiri dan juga menerima `CITRASATELIT_REPO_URL` bila ingin memakai repositori yang sudah dipublikasikan.

## Reproduksibilitas

Seed bawaan adalah 42. Gunakan manifest dan pembagian data yang dihasilkan oleh pipeline di atas. Profil Colab memakai subset, sehingga metriknya dapat berbeda dari percobaan penuh. Pengukuran waktu bergantung pada perangkat. Rincian rancangan dan pemakaian AI tersedia di [spesifikasi proyek](docs/plans/00-design-spec.md) dan [AI_USAGE_LOG.md](AI_USAGE_LOG.md).
