"""Sistem informasi penggunaan lahan Jawa Timur (Streamlit)."""
import json
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

DATA = Path(__file__).parent / "data_app"

st.set_page_config(page_title="SIG Penggunaan Lahan Jawa Timur", layout="wide")
st.title("Sistem Informasi Penggunaan Lahan Jawa Timur")
st.caption("Klasifikasi tutupan lahan Sentinel-2A: sawah, bangunan, mangrove, "
           "lahan hijau, laut, dan danau.")

if not (DATA / "meta.json").exists() or not (DATA / "peta.html").exists():
    st.error("Folder data_app belum lengkap (meta.json atau peta.html tidak ditemukan). "
             "Jalankan notebook proses klasifikasi sampai bagian ekspor hasil dan peta.")
    st.stop()

meta = json.loads((DATA / "meta.json").read_text(encoding="utf-8"))


@st.cache_data
def muat_csv(nama):
    return pd.read_csv(DATA / nama)


@st.cache_data
def muat_peta():
    return (DATA / "peta.html").read_text(encoding="utf-8")


tab_peta, tab_data, tab_model, tab_proses = st.tabs(["Peta", "Data sampel", "Model", "Proses"])

# ---------- Peta ----------
with tab_peta:
    st.write("Layer dasar dapat diganti lewat kontrol di kanan atas peta. Layer klasifikasi "
             "dapat dimatikan untuk membandingkannya dengan citra satelit. Garis putih adalah "
             "batas Provinsi Jawa Timur; hasil klasifikasi mencakup seluruh kotak area studi.")
    components.html(muat_peta(), height=650)

    luas = muat_csv("luas_aoi.csv")
    pilih = st.selectbox("Ringkasan luas per area", sorted(luas["aoi"].unique()))
    sub = luas[luas["aoi"] == pilih]
    c1, c2 = st.columns([1, 1])
    c1.dataframe(sub[["kelas", "luas_ha", "persen"]], hide_index=True)
    c2.bar_chart(sub.set_index("kelas")["luas_ha"])
    st.caption(f"Citra: {sub['tanggal'].iloc[0]} | awan maksimum per scene: {sub['awan'].iloc[0]}%")

# ---------- Data ----------
with tab_data:
    ringkas = muat_csv("ringkasan_kelas.csv")
    st.metric("Jumlah kelas", len(ringkas))
    st.dataframe(ringkas, hide_index=True)
    st.bar_chart(ringkas.set_index("Kelas")["Total"])
    if (DATA / "sampel.geojson").exists():
        st.download_button("Unduh sampel (GeoJSON)",
                           (DATA / "sampel.geojson").read_bytes(), "sampel.geojson")
    if (DATA / "hasil_klasifikasi.tif").exists():
        st.download_button("Unduh hasil klasifikasi (GeoTIFF)",
                           (DATA / "hasil_klasifikasi.tif").read_bytes(), "hasil_klasifikasi.tif")

# ---------- Model ----------
with tab_model:
    st.subheader("Perbandingan model")
    st.dataframe(muat_csv("perbandingan_model.csv"), hide_index=True)
    st.write(f"Model terpilih: **{meta['model_terbaik']}** | akurasi uji "
             f"{meta['akurasi_uji']:.3f} | kappa {meta['kappa_uji']:.3f}")
    if (DATA / "laporan_kelas.csv").exists():
        st.subheader("Metrik per kelas (data uji)")
        st.dataframe(muat_csv("laporan_kelas.csv"), hide_index=True)
    st.subheader("Confusion matrix (data uji)")
    st.dataframe(muat_csv("confusion_matrix.csv"), hide_index=True)
    st.subheader("Kepentingan fitur")
    fi = muat_csv("fitur_penting.csv")
    st.bar_chart(fi.set_index("fitur")["kepentingan"])
    for judul, berkas in [("Eksperimen rasio data", "eksp_rasio.csv"),
                          ("Eksperimen kombinasi fitur", "eksp_fitur.csv"),
                          ("Eksperimen hyperparameter", "eksp_hyperparameter.csv")]:
        st.subheader(judul)
        st.dataframe(muat_csv(berkas), hide_index=True)

# ---------- Proses ----------
with tab_proses:
    st.markdown(
        "**Alur pengolahan data**\n\n"
        "1. Poligon sampel dibaca dari shapefile, lalu tiap poligon diwakili satu titik.\n"
        "2. Citra Sentinel-2A L2A: data latih dari Copernicus Data Space, citra peta dari Google Earth Engine "
        "(awan dan bayangan di-mask dengan band SCL, lalu dibuat komposit median).\n"
        "3. Nilai median area 3 x 3 piksel dipakai untuk 10 band, lalu 8 indeks dihitung.\n"
        "4. Data dibagi per poligon menjadi data latih dan data uji.\n"
        "5. Decision Tree, Random Forest, dan KNN dibandingkan dengan validasi silang; model terbaik "
        "diuji dengan eksperimen rasio data, kombinasi fitur, dan hyperparameter.\n"
        "6. Model dipakai mengklasifikasikan seluruh kotak area studi, lalu hasilnya ditampilkan "
        "di atas citra satelit dengan garis batas Jawa Timur.")
    st.markdown("**Rumus indeks**")
    st.latex(r"NDVI=\frac{B08-B04}{B08+B04}")
    st.latex(r"NDWI=\frac{B03-B08}{B03+B08}")
    st.latex(r"MNDWI=\frac{B03-B11}{B03+B11}")
    st.latex(r"NDBI=\frac{B11-B08}{B11+B08}")
    st.latex(r"EVI=2.5\times\frac{B08-B04}{B08+6\,B04-7.5\,B02+1}")
    st.latex(r"NDRE=\frac{B8A-B05}{B8A+B05}")
    st.latex(r"SAVI=1.5\times\frac{B08-B04}{B08+B04+0.5}")
    st.latex(r"BSI=\frac{(B11+B04)-(B08+B02)}{(B11+B04)+(B08+B02)}")
