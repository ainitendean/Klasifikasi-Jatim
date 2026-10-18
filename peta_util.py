"""Pembuat peta Folium dengan layer hasil klasifikasi terpisah per kelas."""
import json
from pathlib import Path
import folium

GOOGLE_SAT = "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"
ESRI_SAT = ("https://server.arcgisonline.com/ArcGIS/rest/services/"
            "World_Imagery/MapServer/tile/{z}/{y}/{x}")


def baca_meta(folder):
    return json.loads((Path(folder) / "meta.json").read_text(encoding="utf-8"))


def buat_peta(folder):
    folder = Path(folder)
    meta = baca_meta(folder)
    kelas, aoi = meta["kelas"], meta["aoi"]
    peta = folium.Map(location=meta.get("pusat", [-7.6, 112.2]),
                      zoom_start=meta.get("zoom", 9), tiles=None, control_scale=True)
    folium.TileLayer(tiles=GOOGLE_SAT, attr="Google", name="Google Satellite",
                     max_zoom=20).add_to(peta)
    folium.TileLayer(tiles=ESRI_SAT, attr="Esri World Imagery",
                     name="Esri World Imagery", show=False, max_zoom=19).add_to(peta)

    batas = []
    for nama_aoi, a in aoi.items():
        bounds = a["bounds"]
        batas += bounds
        # Satu checkbox untuk setiap HASIL PREDIKSI kelas. Jika kelas dimatikan,
        # hanya warna/piksel prediksi kelas itu yang hilang dari peta.
        if a.get("layers"):
            for kid, nama_file in a["layers"].items():
                info = kelas.get(str(kid), {})
                nama_kelas = info.get("nama", f"Kelas {kid}")
                folium.raster_layers.ImageOverlay(
                    image=str(folder / nama_file), bounds=bounds, opacity=0.75,
                    name=f"Hasil klasifikasi: {nama_kelas}", show=True
                ).add_to(peta)
        else:
            folium.raster_layers.ImageOverlay(
                image=str(folder / a["png"]), bounds=bounds, opacity=0.75,
                name=f"Hasil klasifikasi {nama_aoi}"
            ).add_to(peta)

    f_batas = folder / "batas_jawa_timur.geojson"
    if f_batas.exists():
        folium.GeoJson(
            str(f_batas), name="Batas Provinsi Jawa Timur",
            style_function=lambda _f: {"fill": False, "color": "#ffffff", "weight": 2.5}
        ).add_to(peta)

    # Sampel tidak ditampilkan sebagai checkbox default; peta fokus pada hasil klasifikasi.
    baris = "".join(
        f'<div><span style="background:{v["warna"]};width:14px;height:14px;'
        f'display:inline-block;margin-right:6px;"></span>{v["nama"]}</div>'
        for v in kelas.values()
    )
    legenda = ('<div style="position:fixed;bottom:30px;left:30px;z-index:9999;'
               'background:white;padding:10px 14px;border:1px solid #888;'
               'border-radius:6px;font-size:13px;"><b>Hasil klasifikasi</b>'
               f'{baris}<div style="font-size:11px;color:#555;margin-top:4px;">'
               'Area transparan = tanpa data</div></div>')
    peta.get_root().html.add_child(folium.Element(legenda))
    peta.get_root().header.add_child(folium.Element(
        "<style>.leaflet-image-layer {image-rendering: pixelated;}</style>"))
    if batas:
        lat = [p[0] for p in batas]
        lon = [p[1] for p in batas]
        peta.fit_bounds([[min(lat), min(lon)], [max(lat), max(lon)]])
    folium.LayerControl(collapsed=False).add_to(peta)
    return peta
