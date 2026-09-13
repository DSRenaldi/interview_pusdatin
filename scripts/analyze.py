"""Build interview-ready analytical outputs from four public Pusdatin datasets.

The script is deliberately deterministic: raw files are never modified and every
cleaning decision is recorded in the generated quality report.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports"


def clean_province(series: pd.Series) -> pd.Series:
    return series.astype("string").str.replace(r"^Prov\.\s*", "", regex=True).str.strip()


def safe_rate(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return (numerator / denominator.where(denominator.ne(0)) * 100).fillna(0)


def weighted_rate(frame: pd.DataFrame, flag: pd.Series) -> float:
    return float(frame.loc[flag, "jumlah"].sum() / frame["jumlah"].sum() * 100)


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)

    pt_raw = pd.read_excel(RAW / "pt_akreditasi.xlsx")
    graduate_raw = pd.read_excel(RAW / "lulusan_bidang_wilayah.xlsx")
    rank_raw = pd.read_excel(RAW / "dosen_jabatan.xls")
    cert_raw = pd.read_excel(RAW / "dosen_sertifikasi.xls")

    # Institution data: keep every institution, but report missing geography.
    pt = pt_raw.copy()
    pt["provinsi"] = clean_province(pt["provinsi_pt"])
    pt["akreditasi_puncak"] = pt["akred_pt"].isin(["Unggul", "A"])

    # Graduate file contains an unnamed measure column and empty expansion rows.
    graduate = graduate_raw.rename(columns={"Unnamed: 7": "jumlah"}).copy()
    graduate["provinsi"] = clean_province(graduate["provinsi_pt"])
    graduate_empty = graduate["jk"].isna() & graduate["jumlah"].isna()
    graduate_bad_gender = ~graduate["jk"].isin(["L", "P"]) & ~graduate_empty
    graduate_clean = graduate.loc[~graduate_empty & ~graduate_bad_gender].copy()
    graduate_clean["jumlah"] = pd.to_numeric(graduate_clean["jumlah"], errors="coerce")
    graduate_clean = graduate_clean.loc[graduate_clean["jumlah"].notna() & graduate_clean["jumlah"].ge(0)]

    # A blank academic rank is retained as a substantive "Tanpa Jabatan" bucket,
    # while still being surfaced as an ambiguity in the data-quality report.
    rank = rank_raw.copy()
    rank["provinsi"] = clean_province(rank["provinsi_pt"])
    rank["jabatan"] = rank["jabatan_akademik"].fillna("Tanpa Jabatan")
    rank["senior"] = rank["jabatan"].isin(["Lektor Kepala", "Profesor"])

    cert = cert_raw.copy()
    cert["provinsi"] = clean_province(cert["provinsi_pt"])
    cert["bersertifikasi"] = cert["status_sertifikasi"].eq("Sertifikasi")

    pt_prov = pt.groupby("provinsi", as_index=True).agg(
        jumlah_pt=("npsn", "nunique"),
        pt_akreditasi_puncak=("akreditasi_puncak", "sum"),
    )
    pt_prov["persen_akreditasi_puncak"] = safe_rate(
        pt_prov["pt_akreditasi_puncak"], pt_prov["jumlah_pt"]
    )

    grad_prov = graduate_clean.groupby("provinsi", as_index=True).agg(
        jumlah_lulusan=("jumlah", "sum"),
        lulusan_stem=("jumlah", lambda x: x[graduate_clean.loc[x.index, "a_stem"].eq("STEM")].sum()),
        lulusan_perempuan=("jumlah", lambda x: x[graduate_clean.loc[x.index, "jk"].eq("P")].sum()),
    )
    grad_prov["persen_lulusan_stem"] = safe_rate(grad_prov["lulusan_stem"], grad_prov["jumlah_lulusan"])
    grad_prov["persen_lulusan_perempuan"] = safe_rate(
        grad_prov["lulusan_perempuan"], grad_prov["jumlah_lulusan"]
    )

    rank_prov = rank.groupby("provinsi", as_index=True).agg(
        jumlah_dosen=("jumlah", "sum"),
        dosen_senior=("jumlah", lambda x: x[rank.loc[x.index, "senior"]].sum()),
        dosen_tanpa_jabatan=("jumlah", lambda x: x[rank.loc[x.index, "jabatan"].eq("Tanpa Jabatan")].sum()),
    )
    rank_prov["persen_dosen_senior"] = safe_rate(rank_prov["dosen_senior"], rank_prov["jumlah_dosen"])
    rank_prov["persen_tanpa_jabatan"] = safe_rate(
        rank_prov["dosen_tanpa_jabatan"], rank_prov["jumlah_dosen"]
    )

    cert_prov = cert.groupby("provinsi", as_index=True).agg(
        dosen_basis_sertifikasi=("jumlah", "sum"),
        dosen_bersertifikasi=("jumlah", lambda x: x[cert.loc[x.index, "bersertifikasi"]].sum()),
    )
    cert_prov["persen_dosen_bersertifikasi"] = safe_rate(
        cert_prov["dosen_bersertifikasi"], cert_prov["dosen_basis_sertifikasi"]
    )

    province = pt_prov.join([grad_prov, rank_prov, cert_prov], how="outer").reset_index()

    metrics = [
        "persen_akreditasi_puncak",
        "persen_lulusan_stem",
        "persen_dosen_senior",
        "persen_dosen_bersertifikasi",
    ]
    national_rates = {
        "persen_akreditasi_puncak": float(pt["akreditasi_puncak"].mean() * 100),
        "persen_lulusan_stem": weighted_rate(graduate_clean, graduate_clean["a_stem"].eq("STEM")),
        "persen_dosen_senior": weighted_rate(rank, rank["senior"]),
        "persen_dosen_bersertifikasi": weighted_rate(cert, cert["bersertifikasi"]),
    }

    # The score is an exploratory prioritisation aid, not an official index.
    # Equal-weight percentile ranks provide the exploratory relative position
    # across the 34 provinces. This is not an official index or target.
    percentile_components = province[metrics].rank(pct=True, method="average") * 100
    province["skor_kesiapan"] = percentile_components.mean(axis=1)

    # Absolute-volume ranks are separate from the percentage-based indicators:
    # rank 1 means the largest count among the provinces in this snapshot.
    rank_specs = [
        ("lulusan_stem", "rank_lulusan_stem"),
        ("pt_akreditasi_puncak", "rank_pt_akreditasi_puncak"),
        ("dosen_senior", "rank_dosen_senior"),
        ("dosen_bersertifikasi", "rank_dosen_bersertifikasi"),
    ]
    for value_col, rank_col in rank_specs:
        province[rank_col] = province[value_col].rank(ascending=False, method="min").astype(int)
    province["jumlah_gap"] = sum(province[m].lt(national_rates[m]).astype(int) for m in metrics)
    province["prioritas"] = pd.cut(
        province["jumlah_gap"], bins=[-1, 1, 2, 4], labels=["Relatif kuat", "Perlu perhatian", "Prioritas"]
    ).astype(str)
    province = province.sort_values(["jumlah_gap", "skor_kesiapan"], ascending=[False, True])

    numeric_int = [
        "jumlah_pt", "pt_akreditasi_puncak", "jumlah_lulusan", "lulusan_stem",
        "lulusan_perempuan", "jumlah_dosen", "dosen_senior", "dosen_tanpa_jabatan",
        "dosen_basis_sertifikasi", "dosen_bersertifikasi", "jumlah_gap",
        "rank_lulusan_stem", "rank_pt_akreditasi_puncak", "rank_dosen_senior", "rank_dosen_bersertifikasi",
    ]
    for col in numeric_int:
        province[col] = province[col].fillna(0).astype(int)
    for col in metrics + ["persen_lulusan_perempuan", "persen_tanpa_jabatan", "skor_kesiapan"]:
        province[col] = province[col].fillna(0).round(2)

    accreditation = (
        pt.groupby("akred_pt", as_index=False).size().rename(columns={"akred_pt": "kategori", "size": "jumlah"})
        .sort_values("jumlah", ascending=False)
    )
    graduate_field = (
        graduate_clean.groupby(["nm_kel_bidang", "a_stem"], as_index=False)["jumlah"].sum()
        .rename(columns={"nm_kel_bidang": "bidang", "a_stem": "kategori"})
        .sort_values("jumlah", ascending=False)
    )
    academic_rank = (
        rank.groupby("jabatan", as_index=False)["jumlah"].sum().sort_values("jumlah", ascending=False)
    )
    certification = (
        cert.groupby("status_sertifikasi", as_index=False)["jumlah"].sum().sort_values("jumlah", ascending=False)
    )

    quality = [
        {
            "dataset": "Perguruan tinggi & akreditasi",
            "rows_raw": int(len(pt_raw)),
            "rows_used": int(len(pt)),
            "issues": int(pt_raw["kab_kota_pt"].isna().sum()),
            "note": "Kabupaten/kota kosong; tidak memengaruhi agregasi provinsi.",
        },
        {
            "dataset": "Lulusan menurut bidang & wilayah",
            "rows_raw": int(len(graduate_raw)),
            "rows_used": int(len(graduate_clean)),
            "issues": int(graduate_empty.sum() + graduate_bad_gender.sum()),
            "note": "Baris tanpa jumlah dibuang; kategori gender '*' dikeluarkan; kolom jumlah dinamai ulang.",
        },
        {
            "dataset": "Dosen menurut jabatan akademik",
            "rows_raw": int(len(rank_raw)),
            "rows_used": int(len(rank)),
            "issues": int(rank_raw["jabatan_akademik"].isna().sum()),
            "note": "Jabatan kosong dipertahankan sebagai 'Tanpa Jabatan' karena memiliki nilai jumlah.",
        },
        {
            "dataset": "Dosen menurut sertifikasi",
            "rows_raw": int(len(cert_raw)),
            "rows_used": int(len(cert)),
            "issues": 0,
            "note": "Tidak ditemukan nilai wajib kosong atau kategori di luar kamus.",
        },
    ]

    dashboard = {
        "metadata": {
            "title": "Peta Kesiapan Ekosistem Pendidikan Tinggi 2025",
            "scope": "34 provinsi sebagaimana tersedia pada empat dataset publik",
            "generated_from": "Portal Data Kemdiktisaintek",
            "method_note": "Skor kesiapan = rata-rata percentile rank dari empat indikator, bobot sama. Bukan indeks resmi.",
        },
        "national": {
            "jumlah_pt": int(pt["npsn"].nunique()),
            "jumlah_lulusan": int(graduate_clean["jumlah"].sum()),
            "jumlah_dosen": int(rank["jumlah"].sum()),
            "province_count": int(province["provinsi"].nunique()),
            **{key: round(value, 2) for key, value in national_rates.items()},
            "persen_lulusan_perempuan": round(weighted_rate(graduate_clean, graduate_clean["jk"].eq("P")), 2),
            "persen_tanpa_jabatan": round(weighted_rate(rank, rank["jabatan"].eq("Tanpa Jabatan")), 2),
        },
        "provinces": province.to_dict(orient="records"),
        "accreditation": accreditation.to_dict(orient="records"),
        "graduate_fields": graduate_field.to_dict(orient="records"),
        "academic_rank": academic_rank.to_dict(orient="records"),
        "certification": certification.to_dict(orient="records"),
        "quality": quality,
    }

    province.to_csv(PROCESSED / "province_readiness.csv", index=False)
    graduate_clean.to_csv(PROCESSED / "graduates_clean.csv", index=False)
    with (PROCESSED / "dashboard_data.json").open("w", encoding="utf-8") as handle:
        json.dump(dashboard, handle, ensure_ascii=False, indent=2)

    # JavaScript assignment keeps the dashboard fully usable from file://.
    # The current workspace serves the dashboard from its root index.html.
    # Keep compatibility with a dashboard/ folder if it is restored later.
    dashboard_data_js = ROOT / "data.js" if (ROOT / "index.html").exists() else ROOT / "dashboard" / "data.js"
    with dashboard_data_js.open("w", encoding="utf-8") as handle:
        handle.write("window.DASHBOARD_DATA = ")
        json.dump(dashboard, handle, ensure_ascii=False, separators=(",", ":"))
        handle.write(";\n")

    lowest = province.nsmallest(5, "skor_kesiapan")[["provinsi", "skor_kesiapan", "jumlah_gap"]]
    highest = province.nlargest(5, "skor_kesiapan")[["provinsi", "skor_kesiapan", "jumlah_gap"]]
    summary = [
        "# Ringkasan Hasil Analisis\n",
        f"- Cakupan: {len(province)} provinsi, {len(pt):,} perguruan tinggi, "
        f"{int(graduate_clean['jumlah'].sum()):,} lulusan, dan {int(rank['jumlah'].sum()):,} dosen dalam basis dataset.\n",
        f"- Akreditasi puncak (Unggul/A): {national_rates['persen_akreditasi_puncak']:.2f}%.\n",
        f"- Lulusan STEM: {national_rates['persen_lulusan_stem']:.2f}%.\n",
        f"- Dosen Lektor Kepala/Profesor: {national_rates['persen_dosen_senior']:.2f}%.\n",
        f"- Dosen bersertifikasi: {national_rates['persen_dosen_bersertifikasi']:.2f}%.\n",
        f"- Dosen tanpa jabatan akademik terisi: {dashboard['national']['persen_tanpa_jabatan']:.2f}%.\n",
        "\n## Lima skor peringkat terendah\n\n",
        lowest.to_string(index=False),
        "\n\n## Lima skor peringkat tertinggi\n\n",
        highest.to_string(index=False),
        "\n\n> Skor adalah alat eksplorasi dengan bobot sama, bukan indeks resmi atau evaluasi kinerja daerah.\n",
    ]
    (REPORTS / "analysis_summary.md").write_text("".join(summary), encoding="utf-8")

    print(f"Generated {len(province)} province profiles")
    print(f"Clean graduate rows: {len(graduate_clean):,}/{len(graduate_raw):,}")
    print(f"Outputs: {PROCESSED.relative_to(ROOT)}, {dashboard_data_js.relative_to(ROOT)}, reports/analysis_summary.md")


if __name__ == "__main__":
    main()
