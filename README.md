# Peta Kesiapan Ekosistem Pendidikan Tinggi 2025

Proyek portofolio Data Analyst berbasis dataset publik Pusdatin Kemdiktisaintek. Proyek ini menjawab pertanyaan eksploratif:

> **Wilayah mana yang layak menjadi prioritas diagnosis kualitas dan kapasitas pendidikan tinggi, dan indikator apa yang membentuk gap-nya?**

Hasil akhir adalah dashboard statis yang dapat dibuka tanpa server di [`index.html`](index.html), pipeline reproducible di [`scripts/analyze.py`](scripts/analyze.py), dan ringkasan angka di [`reports/analysis_summary.md`](reports/analysis_summary.md).

Konteks lengkap pekerjaan, keputusan analisis, riwayat perubahan, dan status terakhir disimpan di [`PERSISTENT_MEMORY.md`](PERSISTENT_MEMORY.md) untuk handoff antar-sesi.

Deck presentasi interview tersedia di [`presentation/Pusdatin_Data_Analyst_Brief.pptx`](presentation/Pusdatin_Data_Analyst_Brief.pptx). Presentasi berisi konteks Pusdatin, pertanyaan analisis, sumber data, quality gate, temuan, profil wilayah, rekomendasi, batasan, dan contoh *30-second pitch*.

## Isi repositori

```text
data/raw/                 Empat file unduhan resmi dari portal
data/processed/           CSV + JSON hasil pembersihan/agregasi
index.html                Dashboard offline
app.js / styles.css       Interaksi dan styling dashboard
reports/                  Riset Pusdatin dan ringkasan analisis
scripts/analyze.py        Pipeline pembersihan, agregasi, dan quality gate
```

## Menjalankan ulang

Pastikan Python 3.10+ tersedia dan dependensi di `requirements.txt` terpasang. Lalu:

```powershell
python scripts/analyze.py
```

Buka `index.html` di browser. Tidak ada dependensi JavaScript atau server eksternal.

## Dataset yang digunakan

Keempat file di `data/raw/` diunduh dari halaman dataset publik pada 13 September 2026 dan tidak diubah. Pipeline membersihkan salinan kerja, bukan berkas mentah.

- Perguruan Tinggi & Status Akreditasi 2025 — 3.568 institusi.
- Mahasiswa Lulus menurut Kelompok Bidang Ilmu dan Wilayah 2025 — 17.198 baris agregat.
- Dosen menurut Jabatan Akademik 2025 — 2.636 baris agregat.
- Dosen menurut Status Sertifikasi 2025 — 1.505 baris agregat.

Semua dataset memakai Pusdatin sebagai walidata/portal publik dan bersumber dari Pangkalan Data Pendidikan Tinggi (PDDikti). Tautan detail dan inventaris 16 dataset tersedia di [`reports/research_pusdatin.md`](reports/research_pusdatin.md).

## Metode singkat

1. Menyeragamkan nama provinsi dan tipe data.
2. Mengubah `Unnamed: 7` pada berkas lulusan menjadi `jumlah`.
3. Membuang baris lulusan tanpa jumlah serta tiga baris gender `*`; nilai kosong pada jabatan dosen dipertahankan sebagai `Tanpa Jabatan` dan ditandai sebagai isu kualitas.
4. Mengagregasikan empat sumber ke tingkat provinsi.
5. Membuat empat indikator: proporsi akreditasi puncak (Unggul/A), proporsi lulusan STEM, proporsi dosen senior (Lektor Kepala/Profesor), dan proporsi dosen bersertifikasi.
6. Menghitung `skor_kesiapan` sebagai rata-rata percentile rank empat indikator berbobot sama. Skor ini **bukan indeks resmi**; ia hanya alat untuk menemukan pertanyaan prioritas.

## Temuan awal

- Akreditasi puncak (Unggul/A) hanya 6,19% dari institusi pada basis data.
- Lulusan STEM mencapai 27,63%; dosen senior 14,82%; dosen bersertifikasi 52,66%.
- 20,52% jumlah dosen pada basis jabatan berada di bucket `Tanpa Jabatan`—perlu konfirmasi definisi dan kelengkapan pelaporan.
- Skor peringkat terendah: Papua, Kalimantan Utara, Sulawesi Barat, Banten, dan Kalimantan Tengah.
- Skor peringkat tertinggi: D.I. Yogyakarta, Sumatera Barat, Bali, Jawa Tengah, dan Sulawesi Selatan.

Temuan tersebut tidak menyatakan daerah “baik” atau “buruk”. Perbedaan ukuran basis, kelengkapan pelaporan, dan struktur institusi dapat memengaruhi persentase. Gunakan dashboard untuk mengarahkan validasi berikutnya, bukan sebagai keputusan otomatis.

## Cara membawakan saat interview

Jelaskan bahwa proyek ini mencoba mempraktikkan mandat Pusdatin: mengubah data publik lintas domain menjadi informasi yang bisa ditindaklanjuti, sekaligus menguji kualitas data sebelum membuat klaim. Tekankan tiga pertanyaan lanjutan:

- Apakah definisi dan cakupan empat dataset sudah sebanding, terutama total dosen 42.978 yang jauh lebih kecil daripada statistik dosen nasional?
- Bagaimana Pusdatin memetakan empat provinsi Papua yang tidak tampil sebagai kategori terpisah pada snapshot ini?
- Apakah bucket `Tanpa Jabatan` adalah status substantif atau data belum lengkap, dan bagaimana aturan metadata/validasinya?

## Rujukan utama

Lihat [laporan riset Pusdatin](reports/research_pusdatin.md) untuk sumber resmi, capaian kinerja, daftar layanan, inventaris dataset, dan pemetaan kontribusi proyek.
