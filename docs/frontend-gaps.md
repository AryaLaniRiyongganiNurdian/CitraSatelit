# Gap frontend M8.1

- **Google Colab.** URL notebook proyek belum tersedia. CTA membuka beranda Google Colab. Setelah notebook M9 dipublikasikan, isi `VITE_COLAB_NOTEBOOK_URL` di konfigurasi frontend.
- **Peta dalam frame Figma.** API menyediakan ID, kelas, split, dan tampilan spektral EuroSAT. Field koordinat, tanggal akuisisi, dan filter misi Landsat tidak tercantum dalam kontrak. Workbench Beranda mencari berdasarkan ID atau kelas dan menawarkan RGB, NDVI, serta NDWI untuk citra galeri.
- **Citra referensi.** Foto orbital dan komposit Delta Sungai Lena disimpan secara lokal dari frame Figma. Komposit tersedia saat galeri kosong atau gagal dimuat. Citra pilihan pengguna dan latar kartu Lab Boolean dapat memakai thumbnail dari galeri EuroSAT.
- **Variabel Figma.** `get_variable_defs` mengembalikan objek kosong pada node `5:2`. Token diambil dari nilai langsung pada layer dalam `get_design_context` dan dicocokkan dengan tangkapan layar.
- **Warna workbench.** Frame memakai `#101110`. Implementasi memakai `#111` untuk latar workbench sesuai brief dan memakai `#101110` untuk tinta utama.

## Gap frontend M8.2

- **Metrik unggah ulang satu band.** Endpoint `/api/sharing/reconstruct-upload` bisa menggabungkan share satu band dan mengembalikan pratinjau. Form API belum mempunyai `band_index` untuk menentukan citra pembanding. Workbench menampilkan metrik pembanding sebagai belum tersedia untuk skenario ini.
- **Unduhan dan sesi kedaluwarsa.** Tautan PNG dan NPY membuka respons biner secara langsung. Galat dari unduhan dibuka oleh browser. Operasi JSON yang mengembalikan `SESSION_NOT_FOUND` menampilkan tombol **Buat ulang sesi** dan memakai parameter pembagian terakhir.
- **Math Inspector.** CBIR dan Berbagi Rahasia menyimpan payload komputasi terakhir dan menautkan ke `/inspector`. Perender rumus dan langkah hitung mengikuti M8.3.
