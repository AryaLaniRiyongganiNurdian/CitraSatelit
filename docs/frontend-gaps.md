# Catatan frontend

## Masih terbuka

- **Google Colab (M9).** CTA membuka beranda Google Colab sampai URL notebook proyek tersedia. Isi `VITE_COLAB_NOTEBOOK_URL` setelah notebook dipublikasikan.
- **Metrik unggah ulang satu band.** `/api/sharing/reconstruct-upload` dapat menggabungkan share satu band dan mengembalikan pratinjau. Form API belum mempunyai `band_index` untuk menentukan citra pembanding. Workbench menampilkan metrik pembanding sebagai belum tersedia.
- **Galat unduhan langsung.** Tautan PNG dan NPY membuka respons biner di browser. Operasi JSON yang mengembalikan `SESSION_NOT_FOUND` menampilkan tombol **Buat ulang sesi** dan memakai parameter pembagian terakhir.
- **Artefak C4b.** API menyediakan tabel pengukuran dan temuan untuk C4b. Daftar grafik pada artefak C4b kosong.

## Diselesaikan selama M8

- **Visual dan navigasi.** Workbench memakai token tinta `#101110` dari frame Figma. Enam rute memakai skeleton ORBITAL saat modul dimuat. Tombol ikon memiliki nama aksesibel, fokus kembali ke pemicu setelah drawer ditutup, dan cincin fokus kartu Beranda berada di dalam tepi kartu.
- **Peta dan aset Beranda.** Koordinat, tanggal akuisisi, dan filter misi Landsat diadaptasi menjadi pencarian ID atau kelas EuroSAT dan pilihan RGB, NDVI, serta NDWI. Foto orbital dan komposit Delta Sungai Lena tersedia secara lokal dengan thumbnail EuroSAT untuk citra galeri. `get_variable_defs` pada frame `5:2` kosong, sehingga token diambil dari layer dan tangkapan layar Figma.
- **Inspektor Matematika.** Drawer dan halaman penuh memakai `latex_template` dan `latex_substituted` dari API. Halaman penuh menampilkan hasil terakhir per sumber selama sesi aplikasi, termasuk hasil demo `POST /api/inspector/pixel-xor`.
- **Kontrak Boolean.** `truth-table` menyajikan evaluasi dan rangkaian, `prove` menyajikan ekuivalensi dan dualitas, dan `GET /api/boolean/laws` menyajikan delapan identitas dari `LAW_PROOFS`. Tes kontrak membandingkan ekspor OpenAPI dengan skema FastAPI.
