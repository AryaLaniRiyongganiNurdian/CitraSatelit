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

## Verifikasi kebenaran
- [ ] Semua test `pytest` hijau (lampirkan keluaran).
- [ ] Vektor uji slide (histogram, jarak, Bayes, XOR) cocok.
- [ ] Hasil percobaan diperiksa ulang pada subset kecil secara manual.
- [ ] Referensi di `tests/` (scipy, sklearn) tidak dipakai di `src/core`.

## Pernyataan
Kami menyatakan bahwa penggunaan AI telah dicatat sesuai kenyataan.
Tanda tangan/nama anggota: <...>