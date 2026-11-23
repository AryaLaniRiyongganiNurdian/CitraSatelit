# Catatan frontend

## Masih terbuka

- **Publikasi Colab.** `notebooks/citrasatelit.ipynb` dan pengemas subset sudah tersedia. Jalankan `python -m tools.make_colab_subset` untuk menghasilkan ZIP dan `.sha256` di `artifacts/`. Notebook dapat memakai ZIP yang diunggah ke `/content` atau URL rilis melalui `COLAB_SUBSET_URL`, dengan `COLAB_SUBSET_MIRROR` opsional. CTA Beranda membuka beranda Colab hingga `VITE_COLAB_NOTEBOOK_URL` diisi dengan URL notebook yang dipublikasikan. Build Docker M10 menerima nilai ini melalui `--build-arg`.
- **Metrik unggah ulang satu band.** `/api/sharing/reconstruct-upload` dapat menggabungkan share satu band dan mengembalikan pratinjau. Form API belum mempunyai `band_index` untuk menentukan citra pembanding. Workbench menampilkan metrik pembanding sebagai belum tersedia.
- **Galat unduhan langsung.** Tautan PNG dan NPY membuka respons biner di browser. Operasi JSON yang mengembalikan `SESSION_NOT_FOUND` menampilkan tombol **Buat ulang sesi** dan memakai parameter pembagian terakhir.
- **Artefak C4b.** API menyediakan tabel pengukuran dan temuan untuk C4b. Daftar grafik pada artefak C4b kosong.

## Diselesaikan selama M8

- **Visual dan navigasi.** Workbench memakai token tinta `#101110` dari frame Figma. Enam rute memakai skeleton ORBITAL saat modul dimuat. Tombol ikon memiliki nama aksesibel, fokus kembali ke pemicu setelah drawer ditutup, dan cincin fokus kartu Beranda berada di dalam tepi kartu.
- **Peta dan aset Beranda.** Koordinat, tanggal akuisisi, dan filter misi Landsat diadaptasi menjadi pencarian ID atau kelas EuroSAT dan pilihan RGB, NDVI, serta NDWI. Foto orbital dan komposit Delta Sungai Lena tersedia secara lokal dengan thumbnail EuroSAT untuk citra galeri. `get_variable_defs` pada frame `5:2` kosong, sehingga token diambil dari layer dan tangkapan layar Figma.
- **Inspektor Matematika.** Drawer dan halaman penuh memakai `latex_template` dan `latex_substituted` dari API. Halaman penuh menampilkan hasil terakhir per sumber selama sesi aplikasi, termasuk hasil demo `POST /api/inspector/pixel-xor`.
- **Kontrak Boolean.** `truth-table` menyajikan evaluasi dan rangkaian, `prove` menyajikan ekuivalensi dan dualitas, dan `GET /api/boolean/laws` menyajikan delapan identitas dari `LAW_PROOFS`. Tes kontrak membandingkan ekspor OpenAPI dengan skema FastAPI.
