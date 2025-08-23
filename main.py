import json
import shutil
import sys
import datetime
from pathlib import Path
from modules.capture import capture_fswebcam
from modules.upload import upload
from modules import openweathermap
from modules import classify
from modules.stormwarning import tick
from modules.rainintensity import generate, DEFAULT_TILES

def main():
    base = Path(__file__).parent

    # Konfiguration laden
    cfg_path = base / "config.local.json"
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    # Pfade
    scripts_dir = base / "modules"
    script_00_path = scripts_dir / "00_daylight_gate.sh"
    script_02_path = scripts_dir / "02_take_webcam_picture.sh"
    script_03_path = scripts_dir / "03_upload_picture.sh"

    current_dir = base / "jpg" / "current"
    old_dir = base / "jpg" / "old"
    cache_dir = base / "jpg" / "cache"
    json_dir = base / "json"
    classified_base_dir = base / "jpg" / "classified"

    fixed_path = current_dir / "IMG_4903.jpg"  # "aktuelles" Bild mit festem Namen
    radar_out_path = current_dir / "radar_Nuremberg_zoom6.jpg"
    radar_cache_path = cache_dir / "radar_last.png"
    basemap_cache_path = cache_dir / "basemap.png"

    # Ordner sicherstellen
    current_dir.mkdir(parents=True, exist_ok=True)
    old_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)
    classified_base_dir.mkdir(parents=True, exist_ok=True)

    # Bild aufnehmen
    img_path = capture_fswebcam(script_02_path)

    # === Nacht / kein Bild ===
    if img_path is None or not img_path.exists():
        print("🌙 Kein Bild aufgenommen (Nacht oder Skip) – keine Verarbeitung.")
        sys.exit(0)

    print("➡️ img_path:", img_path)

    # Aufgenommenes Bild nach jpg/old/ verschieben (Archiv)
    old_path = old_dir / img_path.name
    shutil.move(str(img_path), str(old_path))
    print("📸 Bild verschoben nach:", old_path)

    # Kopie als aktuelles Bild mit festem Namen für das Overlay bereitstellen
    shutil.copy2(old_path, fixed_path)

    # Regenintensität-Overlay erzeugen
    generate(
        cfg,
        output_image_path=radar_out_path,
        bg_image_path=fixed_path,
        radar_image_cache_path=radar_cache_path,
        basemap_image_cache_path=basemap_cache_path,
        tiles=DEFAULT_TILES,
        zoom=6,
        legend=True,
        legend_width=54,
        overlay_size=(400, 322),
        margin_right=90,
        margin_bottom=135,
        crop_bottom=100,
        opacity=0.85,
        border=True,
        border_width=4,
        border_color="#808080",
    )

    # Upload
    upload(cfg, fixed_path)
    print("➡️ Upload:", fixed_path)

    # ==== Pure Pipeline ====
    owm = openweathermap.get_openweathermap(cfg)
    classification, classification_detail = classify.classify_weather(owm)
    storm = tick(cfg, owm)

    weather_data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "old_path": str(old_path),
        "openweathermap": owm,
        "classification": classification,
        "classification_detail": classification_detail,
        "stormwarning": storm,
    }

    json_path = json_dir / (old_path.stem + ".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(weather_data, f, indent=4, ensure_ascii=False)

    print(f"✅ JSON gespeichert: {json_path}")
    print(json.dumps(weather_data, indent=4, ensure_ascii=False))

    classify.copy_to_classified(weather_data, old_path, json_path, classified_base_dir)

if __name__ == "__main__":
    main()

