"""Sistem Informasi Penggunaan dan Tutupan Lahan Jawa Timur (Streamlit).

Membaca folder `data_app/` hasil notebook (meta.json, berkas CSV, GeoJSON, PNG hasil klasifikasi)
dan `peta_util.py` (pembuat peta Folium). Jalankan lokal dengan: streamlit run app.py
"""
import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

DATA = Path(__file__).parent / "data_app"
st.set_page_config(page_title="SIG Penggunaan Lahan Jawa Timur", page_icon="🗺️", layout="wide")

if not (DATA / "meta.json").exists():
    st.error("Folder `data_app/` (berisi `meta.json` dan berkas hasil lainnya) tidak ditemukan. "
             "Letakkan folder itu di samping `app.py`.")
    st.stop()


# ------------------------------------------------------------ pemuatan data
@st.cache_data
def baca_meta():
    return json.loads((DATA / "meta.json").read_text(encoding="utf-8"))


@st.cache_data
def baca_csv(nama):
    p = DATA / nama
    return pd.read_csv(p) if p.exists() else None


@st.cache_resource(show_spinner="Menyusun peta...")
def html_peta():
    """Peta Folium dirender sekali menjadi HTML, lalu dipakai ulang."""
    from peta_util import buat_peta
    return buat_peta(DATA).get_root().render()


def tampil_tabel(nama, judul=None):
    d = baca_csv(nama)
    if d is None:
        return
    if judul:
        st.subheader(judul)
    st.dataframe(d, use_container_width=True, hide_index=True)


meta = baca_meta()
warna = {v["nama"]: v["warna"] for v in meta["kelas"].values()}
periode = next(iter(meta["aoi"].values())).get("tanggal", "")

st.title("Sistem Informasi Penggunaan Lahan Jawa Timur")
st.caption(f"Klasifikasi tutupan lahan dari citra Sentinel-2 ({periode}): "
           "sawah, bangunan, mangrove, lahan hijau, laut, dan danau.")

tab_peta, tab_luas, tab_data, tab_model, tab_proses, tab_unduh = st.tabs(
    ["Peta", "Statistik luas", "Data sampel", "Model", "Proses", "Unduhan"])

# ---- Peta
with tab_peta:
    st.write("Layer dasar dan layer hasil klasifikasi dapat diganti lewat kontrol di kanan atas peta. "
             "Garis putih adalah batas Provinsi Jawa Timur.")
    components.html(html_peta(), height=650, scrolling=False)
    st.caption("Peta dasar Google hanya sebagai latar visual. Hasil klasifikasi adalah perkiraan model, "
               "bukan penetapan resmi penggunaan lahan.")

# ---- Statistik luas
with tab_luas:
    luas = baca_csv("luas_aoi.csv")
    if luas is not None:
        st.subheader("Luas per kelas (hektare)")
        kiri, kanan = st.columns(2)
        kiri.dataframe(luas[["kelas", "luas_ha", "persen"]], use_container_width=True, hide_index=True)
        fig, ax = plt.subplots(figsize=(6, 3.6))
        ax.bar(luas["kelas"], luas["luas_ha"], color=[warna.get(k, "#1a9641") for k in luas["kelas"]],
               edgecolor="k")
        ax.set_ylabel("Luas (ha)")
        plt.xticks(rotation=25, ha="right")
        fig.tight_layout()
        kanan.pyplot(fig)
        st.info("Luas dihitung dari raster beresolusi 120 m pada area di dalam batas Jawa Timur. "
                "Objek sempit (permukiman kecil, mangrove tipis) cenderung kurang terwakili.")

# ---- Data sampel
with tab_data:
    rk = baca_csv("ringkasan_kelas.csv")
    if rk is not None:
        st.subheader("Jumlah sampel per kelas")
        kiri, kanan = st.columns(2)
        kiri.dataframe(rk, use_container_width=True, hide_index=True)
        kanan.bar_chart(rk.set_index("Kelas")[["Training", "Testing"]])
        st.write(f"Total {int(rk['Total'].sum())} poligon sampel dari {len(rk)} kelas "
                 f"({int(rk['Training'].sum())} data training, {int(rk['Testing'].sum())} data testing).")

# ---- Model
with tab_model:
    c1, c2, c3 = st.columns(3)
    c1.metric("Model terpilih", meta.get("model_terbaik", "-"))
    c2.metric("Akurasi data uji", f"{meta.get('akurasi_uji', 0):.3f}")
    c3.metric("Kappa", f"{meta.get('kappa_uji', 0):.3f}")
    tampil_tabel("perbandingan_model.csv", "Perbandingan model")
    tampil_tabel("laporan_kelas.csv", "Metrik per kelas (data uji)")

    cm = baca_csv("confusion_matrix.csv")
    if cm is not None:
        st.subheader("Confusion matrix (data uji)")
        m = cm.set_index("Kelas")
        fig, ax = plt.subplots(figsize=(6.5, 5))
        ax.imshow(m.values, cmap="Greens")
        ax.set_xticks(range(m.shape[1]), [c.replace("Prediksi: ", "") for c in m.columns], rotation=40, ha="right")
        ax.set_yticks(range(m.shape[0]), [i.replace("Aktual: ", "") for i in m.index])
        for i in range(m.shape[0]):
            for j in range(m.shape[1]):
                v = int(m.values[i, j])
                ax.text(j, i, v, ha="center", va="center",
                        color="white" if v > m.values.max() / 2 else "black")
        ax.set_xlabel("Prediksi")
        ax.set_ylabel("Aktual")
        fig.tight_layout()
        st.pyplot(fig)

    fi = baca_csv("fitur_penting.csv")
    if fi is not None:
        st.subheader("Kepentingan fitur")
        f = fi.sort_values("kepentingan")
        fig, ax = plt.subplots(figsize=(6.5, 5))
        ax.barh(f["fitur"], f["kepentingan"], color="#1a9641")
        ax.set_xlabel("Penurunan akurasi saat fitur diacak")
        fig.tight_layout()
        st.pyplot(fig)

    tampil_tabel("eksp_rasio.csv", "Eksperimen rasio data")
    tampil_tabel("eksp_fitur.csv", "Eksperimen kombinasi fitur")
    tampil_tabel("eksp_hyperparameter.csv", "Eksperimen hyperparameter")

# ---- Proses
with tab_proses:
    st.subheader("Alur pengolahan data")
    st.markdown(
        "1. Poligon sampel (60 per kelas) dibaca dari shapefile, tiap poligon diwakili satu titik.\n"
        "2. Nilai band Sentinel-2 L2A diambil pada titik tersebut (komposit median bebas awan).\n"
        "3. Fitur dihitung: 10 band dan 8 indeks spektral.\n"
        "4. Data dibagi menjadi data training (80%) dan testing (20%).\n"
        "5. Decision Tree, Random Forest, dan KNN dibandingkan dengan validasi silang; model terbaik dipilih.\n"
        "6. Eksperimen rasio data, kombinasi fitur, dan hyperparameter dijalankan.\n"
        "7. Model dipakai mengklasifikasikan seluruh area Jawa Timur per ubin, lalu ditampilkan pada peta."
    )
    st.subheader("Rumus indeks spektral")
    for rumus in (
        r"NDVI=\frac{B08-B04}{B08+B04}",
        r"NDWI=\frac{B03-B08}{B03+B08}",
        r"MNDWI=\frac{B03-B11}{B03+B11}",
        r"NDBI=\frac{B11-B08}{B11+B08}",
        r"NDRE=\frac{B8A-B05}{B8A+B05}",
        r"EVI=2.5\times\frac{B08-B04}{B08+6\,B04-7.5\,B02+1}",
        r"SAVI=1.5\times\frac{B08-B04}{B08+B04+0.5}",
        r"BSI=\frac{(B11+B04)-(B08+B02)}{(B11+B04)+(B08+B02)}",
    ):
        st.latex(rumus)

# ---- Unduhan
with tab_unduh:
    st.write("Berkas hasil yang dapat diunduh:")
    for nama, label, mime in [
        ("hasil_klasifikasi.tif", "Hasil klasifikasi (GeoTIFF, dapat dibuka di QGIS)", "image/tiff"),
        ("sampel.geojson", "Titik/poligon sampel (GeoJSON)", "application/geo+json"),
        ("batas_jawa_timur.geojson", "Batas Provinsi Jawa Timur (GeoJSON)", "application/geo+json"),
        ("luas_aoi.csv", "Luas per kelas (CSV)", "text/csv"),
        ("perbandingan_model.csv", "Perbandingan model (CSV)", "text/csv"),
    ]:
        p = DATA / nama
        if p.exists():
            st.download_button(label, p.read_bytes(), file_name=nama, mime=mime)
