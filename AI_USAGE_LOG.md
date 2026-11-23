# AI Usage Log

Proyek: Mini-CBIR & XOR-Based Secret Sharing pada EuroSAT
Kelompok: <nama kelompok> | Mata kuliah: Statistika dan Probabilitas / Matematika Diskrit | Dosen: Tara Afri Melandari, S.Mat., M.Mat.

## Kebijakan
- Semua bantuan AI dicantumkan di sini dan di laporan (bagian Daftar Pustaka dan Lampiran).
- Fungsi inti (`src/core`) ditulis dan dipahami anggota kelompok; AI dipakai untuk rancangan, kerangka, dan tinjauan.
- Setiap anggota mampu menjelaskan seluruh kode dan hasil.

## Ringkasan alat
| Alat | Versi/Model | Dipakai untuk |
|---|---|---|
| Claude (claude.ai) | <model> | Perancangan arsitektur, spesifikasi matematika, rencana TDD, kontrak API |
| OpenAI Codex (VS Code) | <versi> | Implementasi kode mengikuti dokumen rancangan |
| <alat lain> | | |

## Catatan per sesi
| Tanggal | Anggota | Alat | Tujuan | Prompt ringkas / dokumen masukan | Hasil yang dipakai | Apa yang diverifikasi dan bagaimana | Perubahan manual |
|---|---|---|---|---|---|---|---|
| 2026-11-22 | <nama> | Claude | Rancangan proyek | Prompt fase 1 dan 2, slide materi | `00-design-spec.md`, `01-implementation-plan.md`, `api-contract.md`, `frontend-handoff.md` | Dicek terhadap slide dosen dan rubrik | <isi> |
| 2026-11-22 | <nama> | OpenAI Codex (VS Code) | Scaffold dan data tooling M0 | Spesifikasi desain dan rencana TDD | Tes loader, manifest dan kemurnian core, konfigurasi, modul data, kerangka tools | Merah: 2 galat koleksi karena modul belum ada. Hijau: 8 tes lulus. Loader diuji dengan JPG/TIFF lokal. Manifest lokal dihentikan setelah mendeteksi 597 TIFF di luar pola ID. | <isi> |
| 2026-11-22 | <nama> | OpenAI Codex (VS Code) | Penyelesaian M0 | Keputusan penanganan TIFF tambahan dan jadwal arsip Colab | Manifest melewati nama di luar pola, tes regresi, gitignore, dan penutupan pertanyaan M0 | Merah: 1 tes gagal sebelum perubahan. Hijau: 8 tes lulus. CSV lokal diverifikasi berisi 27.000 pasangan, 250 galeri, dan 2.000 subset Colab. Laporan mencatat 597 TIFF dilewati. | <isi> |
| 2026-11-22 | <nama> | OpenAI Codex (VS Code) | M1: statistik dan probabilitas | Spesifikasi bagian 4.1 dan 4.2 serta vektor uji M1 | Tes statistik dan probabilitas, implementasi NumPy, catatan input Bayes yang belum tersedia | Merah: 2 galat koleksi sebelum modul dibuat. Hijau: 43 tes lulus, termasuk pemeriksaan kemurnian core. RuntimeWarning diperlakukan sebagai galat. 2 tes Bayes dilewati karena input dari slide belum tersedia di repositori. SciPy dan scikit-learn hanya digunakan sebagai pembanding di tes. | <isi> |
| 2026-11-22 | <nama> | OpenAI Codex (VS Code) | Penyelesaian uji Bayes M1 | Prior dan likelihood Transjakarta vs KRL serta Gateway X vs Y dari slide dosen | Kedua kasus uji diaktifkan, posterior diuji dengan toleransi 1e-9, dan pertanyaan M1 ditutup | pytest -q -W error: 45 tes lulus tanpa skipped atau warning. | Angka dari slide diberikan oleh pengguna. |
| 2026-11-22 | <nama> | OpenAI Codex (VS Code) | M2: warna dan spektral | Spesifikasi bagian 2 dan 4.3 serta rencana tes M2 | Konversi gray dan HSV, grid, NDVI/NDWI, skala persentil, sintesis RGB, dan tes | Merah: 2 galat koleksi sebelum modul dibuat. Hijau: 59 tes lulus, termasuk pemeriksaan kemurnian core, dengan pytest -q -W error. Pillow, colorsys, dan np.percentile dipakai sebagai pembanding di tes. | <isi> |
| 2026-11-22 | <nama> | OpenAI Codex (VS Code) | M3: CBIR | Spesifikasi bagian 4.4 dan rencana tes M3 | Ekstraksi fitur, metrik, peringkat, evaluasi, tes, dan catatan keputusan terbuka | Merah: 1 galat koleksi sebelum modul dibuat. Hijau: 90 lulus, 1 skip Latihan 12, termasuk pemeriksaan kemurnian core dengan warning sebagai galat. Median chi-square 27000 x 96 dari 20 pengukuran 12,34 ms (float32) dan 14,55 ms (float64). | Histogram asli Latihan 12 dan aturan seri penuh kNN menunggu keputusan. |
| 2026-11-22 | <nama> | OpenAI Codex (VS Code) | Penyelesaian M3 | Histogram Latihan 12 dan aturan seri penuh kNN dari pengguna | Tes Latihan 12 diaktifkan, kNN memecah seri lewat jarak terdekat lalu indeks kelas, dan kedua pertanyaan ditutup | Merah: dua tes seri penuh gagal dengan ValueError. Hijau: pytest -q -W error menghasilkan 93 tes lulus tanpa skipped atau warning. | Pengguna mengonfirmasi histogram dan urutan pemecah seri. |
| 2026-11-22 | <nama> | OpenAI Codex (VS Code) | M4: XOR secret sharing | Spesifikasi bagian 4.5, kontrak API, dan vektor uji M4 | Tes dan implementasi NumPy untuk split, rekonstruksi, metrik, bit-flip, tamper piksel satu kanal, reuse key, dan RAID-5 | Merah: 2 galat koleksi sebelum modul dibuat. Hijau: pytest -q -W error menghasilkan 206 tes lulus, termasuk pemeriksaan kemurnian core. | Bit default, kebijakan kanal piksel, dan operasi serta batas blok menunggu keputusan. |
| 2026-11-22 | <nama> | OpenAI Codex (VS Code) | Penyelesaian tamper M4 | Keputusan pengguna untuk bit default, kanal, dan blok | Tamper piksel MSB dan kanal, validasi batas, XOR blok terpotong dengan mask tak nol, tes, serta penutupan pertanyaan M4 | Merah: 33 tes tamper gagal sebelum perbaikan. Hijau: pytest -q -W error menghasilkan 243 tes lulus tanpa skipped atau warning. | Aturan tamper ditetapkan oleh pengguna. |
| 2026-11-22 | <nama> | OpenAI Codex (VS Code) | M5: Boolean Lab | Spesifikasi bagian 4.6, vektor uji M5, kontrak API, dan frontend handoff | Parser dan evaluasi, tabel kebenaran, dualitas, Circuit, K-Map, katalog bukti, serta tes | Merah: 1 galat koleksi sebelum modul dibuat. Hijau: pytest -q -W error menghasilkan 285 tes lulus tanpa skip atau warning. Pemeriksaan tambahan memverifikasi 789 penyederhanaan K-Map terhadap minterm asal. | <isi> |
| 2026-11-22 | <nama> | OpenAI Codex (VS Code) | M6: indeks, galeri, dan percobaan | Bagian 3, 5, dan 6 spesifikasi serta kontrak API dan keputusan pengguna | Indeks empat proses, 250 pasangan galeri, runner C1–C4c, 37 payload evaluasi dan dua tes M6 | Merah: 2 galat koleksi. Regresi C2 direproduksi dengan histogram uint16 dan diperbaiki menggunakan aritmetika integer. Hijau: 287 tes lulus tanpa warning atau skip. Smoke dua kali memberi JSON identik dengan jam dan cap waktu tetap. Full: indeks 125,147 s, galeri 0,663 s, percobaan dan cache 226,319 s. | Pengguna menetapkan thumb_off, semua mode C4a, dan RGB 32 bin chi-square untuk C4b. |
| 2026-11-22 | <nama> | OpenAI Codex (VS Code) | M7: API FastAPI | Spesifikasi, kontrak API, handoff frontend, dan dua keputusan pengguna | Endpoint, model, Inspector, OpenAPI, tipe dan klien TypeScript, serta tes | Merah: dua galat koleksi sebelum implementasi. Hijau: 298 tes lulus dengan pytest -q -W error. Smoke Uvicorn memuat 27.000 citra, membaca 6 hasil percobaan, mencari 5 hit, merekonstruksi 3 share dengan MSE 0, lalu menampilkan Swagger dan OpenAPI. | Aturan TIFF non-galeri dan metrik unggahan satu band dikonfirmasi pengguna. |
| 2026-11-23 | <nama> | OpenAI Codex (VS Code) + Figma MCP | M8.1 — Beranda dan design system | Spesifikasi, kontrak API, handoff, dan frame Figma 5:2 | App Shell enam rute, tema shadcn/ui, workbench Beranda, aset lokal, serta tes frontend dan penyajian SPA | Tes awal gagal pada nama aksesibel judul. Setelah koreksi, 7 tes Vitest lulus, TypeScript bersih, build tersedia, dan 298 tes pytest lulus dengan warning sebagai galat. Smoke browser pada 1280 dan 768 px memakai data asli untuk 27.000 citra, 10 kelas, akurasi C2 79,6%, serta uji navigasi, pratinjau NDVI, dan fallback. | CTA Colab menunggu URL notebook M9. |
| 2026-11-23 | <nama> | OpenAI Codex (VS Code) | M8.2 — CBIR dan Berbagi Rahasia | Spesifikasi, rencana TDD, kontrak API, handoff frontend, dan token ORBITAL M8.1 | Dua workbench, ImagePicker, ChartRenderer, integrasi API bertipe, pemulihan sesi, dan penyimpanan payload Inspektor | Tes awal gagal karena komponen belum tersedia. Setelah implementasi, 18 tes Vitest lulus, TypeScript bersih, build Vite terbentuk, dan 298 tes pytest lulus dengan warning sebagai galat. Uji browser pada 1280 dan 768 px memakai galeri EuroSAT dan memverifikasi pencarian lima hit, heatmap 10×10, rekonstruksi tiga share, unggah ulang PNG identik, tamper satu piksel, serta percobaan langsung. | Rincian Inspektor mengikuti M8.3. API unggah ulang share satu band belum menyertakan indeks band untuk pembanding. |

## Verifikasi kebenaran
- [ ] Semua test `pytest` hijau (lampirkan keluaran).
- [ ] Vektor uji slide (histogram, jarak, Bayes, XOR) cocok.
- [ ] Hasil percobaan diperiksa ulang pada subset kecil secara manual.
- [ ] Referensi di `tests/` (scipy, sklearn) tidak dipakai di `src/core`.

## Pernyataan
Kami menyatakan bahwa penggunaan AI telah dicatat sesuai kenyataan.
Tanda tangan/nama anggota: <...>