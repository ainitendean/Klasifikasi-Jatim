"""Pembuat peta Folium untuk SIG penggunaan lahan Jawa Timur."""
import json
from pathlib import Path

import folium

GOOGLE_SAT = "https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"
ESRI_SAT = ("https://server.arcgisonline.com/ArcGIS/rest/services/"
            "World_Imagery/MapServer/tile/{z}/{y}/{x}")


def baca_meta(folder):
    """Membaca meta.json hasil ekspor notebook."""
    return json.loads((Path(folder) / "meta.json").read_text(encoding="utf-8"))


def buat_peta(folder):
    """Peta: satelit Google di bawah, hasil klasifikasi per AOI di atasnya."""
    folder = Path(folder)
    meta = baca_meta(folder)
    kelas, aoi = meta["kelas"], meta["aoi"]

    peta = folium.Map(location=meta.get("pusat", [-7.6, 112.2]),
                      zoom_start=meta.get("zoom", 9), tiles=None, control_scale=True)

    # Layer dasar
    folium.TileLayer(tiles=GOOGLE_SAT, attr="Google", name="Google Satellite",
                     max_zoom=20).add_to(peta)
    folium.TileLayer(tiles=ESRI_SAT, attr="Esri World Imagery",
                     name="Esri World Imagery", show=False, max_zoom=19).add_to(peta)

    # Layer hasil klasifikasi (satu per AOI)
    batas = []
    for nama, a in aoi.items():
        folium.raster_layers.ImageOverlay(
            image=str(folder / a["png"]), bounds=a["bounds"], opacity=0.7,
            name=f"Klasifikasi {nama}").add_to(peta)
        batas += a["bounds"]

    # Batas Provinsi Jawa Timur
    f_batas = folder / "batas_jawa_timur.geojson"
    if f_batas.exists():
        folium.GeoJson(
            str(f_batas), name="Batas Provinsi Jawa Timur",
            style_function=lambda _f: {"fill": False, "color": "#ffffff", "weight": 2.5}
        ).add_to(peta)

    # Outline poligon sampel per kelas (default mati)
    f_sampel = folder / "sampel.geojson"
    if f_sampel.exists():
        fitur = json.loads(f_sampel.read_text(encoding="utf-8"))["features"]
        for kid, info in kelas.items():
            sub = [f for f in fitur if str(f["properties"].get("kelas_id")) == str(kid)]
            if sub:
                folium.GeoJson(
                    {"type": "FeatureCollection", "features": sub},
                    name=f"Sampel {info['nama']}", show=False,
                    style_function=lambda _f, w=info["warna"]: {
                        "fill": False, "color": w, "weight": 2},
                ).add_to(peta)

    # Legenda
    baris = "".join(
        f'<div><span style="background:{v["warna"]};width:14px;height:14px;'
        f'display:inline-block;margin-right:6px;"></span>{v["nama"]}</div>'
        for v in kelas.values())
    legenda = ('<div style="position:fixed;bottom:30px;left:30px;z-index:9999;'
               'background:white;padding:10px 14px;border:1px solid #888;'
               'border-radius:6px;font-size:13px;"><b>Kelas lahan</b>'
               f'{baris}<div style="font-size:11px;color:#555;margin-top:4px;">'
               'Transparan = tanpa data (awan)</div></div>')
    peta.get_root().html.add_child(folium.Element(legenda))
    peta.get_root().header.add_child(folium.Element(
        "<style>.leaflet-image-layer {image-rendering: pixelated;}</style>"))

    if batas:
        lat = [p[0] for p in batas]
        lon = [p[1] for p in batas]
        peta.fit_bounds([[min(lat), min(lon)], [max(lat), max(lon)]])
    folium.LayerControl(collapsed=False).add_to(peta)
    return peta
