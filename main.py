import json
import shutil
import sys
import datetime
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from modules.capture import capture_fswebcam
from modules import openweathermap
from modules import classify
from modules.stormwarning import tick
from modules.rainintensity import generate, DEFAULT_TILES
from modules.upload import upload


# ---------- Daylight-Gate ----------

def daylight_ok(cfg: dict, script_00_path: Path) -> bool:
    """
    True  -> Tageslicht: Kamera erlaubt
    False -> Nacht      : Kamera gesperrt (aber JSON soll trotzdem erzeugt werden)
    """
    if not cfg.get("daylight_gate", True):
        return True

    if script_00_path.exists():
        try:
            res = subprocess.run(
                ["bash", str(script_00_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            if res.returncode == 0:
                return True
            print(f"🌙 Daylight-Gate: Nacht/Block (exit={res.returncode})")
            return False
        except Exception as e:
            print(f"⚠️ Daylight-Gate Fehler: {e} – lasse Kamera zu.")
            return True
    else:
        return True


# ---------- Bildverarbeitung (nur tagsüber) ----------

def run_camera_pipeline(
    base: Path,
    cfg: dict,
    script_02_path: Path,
) -> Tuple[Optional[Path], Optional[Path]]:
    """
    Kamera-/Bild-Workflow (nur tagsüber aufgerufen).
    Returns:
        (old_path, fixed_path) bei Erfolg
        (None, None) wenn keine Aufnahme
    """
    current_dir = base / "jpg" / "current"
    old_dir     = base / "jpg" / "old"
    cache_dir   = base / "jpg" / "cache"

    current_dir.mkdir(parents=True, exist_ok=True)
    old_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    fixed_path          = current_dir / "IMG_4903.jpg"
    radar_out_path      = current_dir / "radar_Nuremberg_zoom6.jpg"
    radar_cache_path    = cache_dir / "radar_last.png"
    basemap_cache_path  = cache_dir / "basemap.png"

    # 1) Bild aufnehmen
    img_path = capture_fswebcam(script_02_path)

    if img_path is None or not img_path.exists():
        print("⚠️ Keine Bildaufnahme – überspringe Kamera-Workflow.")
        return None, None

    print("➡️ img_path:", img_path)

    # 2) Original nach jpg/old/ verschieben
    old_path = old_dir / img_path.name
    shutil.move(str(img_path), str(old_path))
    print("📸 Bild verschoben nach:", old_path)

    # 3) Kopie als IMG_4903.jpg
    shutil.copy2(old_path, fixed_path)

    # 4) Radar EINMAL rendern & Overlay auf IMG_4903.jpg
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

    # 5) Overlay in die Originaldatei übernehmen
    shutil.copy2(fixed_path, old_path)

    return old_path, fixed_path


# ---------- main ----------

def main():
    base = Path(__file__).parent

    # Konfiguration laden
    cfg_path = base / "config.local.json"
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    # Skriptpfade
    scripts_dir    = base / "modules"
    script_00_path = scripts_dir / "00_daylight_gate.sh"  # optional
    script_02_path = scripts_dir / "02_take_webcam_picture.sh"

    # Verzeichnisse
    json_dir = base / "json"
    classified_base_dir = base / "jpg" / "classified"
    json_dir.mkdir(parents=True, exist_ok=True)
    classified_base_dir.mkdir(parents=True, exist_ok=True)

    # Tag/Nacht prüfen
    is_daylight = daylight_ok(cfg, script_00_path)

    old_path: Optional[Path] = None
    fixed_path: Optional[Path] = None
    classification = None
    classification_detail = None

    if is_daylight:
        # --- Tagsüber: Kamera & Klassifizierung ---
        old_path, fixed_path = run_camera_pipeline(base, cfg, script_02_path)

        if fixed_path and fixed_path.exists():
            upload(cfg, fixed_path)
            print("➡️ Upload:", fixed_path)

        # Klassifizierung nur tagsüber
        owm = openweathermap.get_openweathermap(cfg)
        classification, classification_detail = classify.classify_weather(owm)
        storm = tick(cfg, owm)
    else:
        # --- Nacht: nur Wetterdaten, keine Bilder, keine Klassifizierung ---
        print("🌙 Nachtmodus: kein Bild, keine Klassifizierung – nur Wetterdaten.")
        owm = openweathermap.get_openweathermap(cfg)
        storm = tick(cfg, owm)

    # ==== JSON immer speichern ====
    weather_data = {
        "timestamp": datetime.datetime.now().isoformat(),
        "is_daylight": is_daylight,
        "old_path": str(old_path) if old_path else None,
        "current_img_path": str(fixed_path) if fixed_path else None,
        "openweathermap": owm,
        "classification": classification,
        "classification_detail": classification_detail,
        "stormwarning": storm,
    }

    if old_path:
        json_path = json_dir / (Path(old_path).stem + ".json")
    else:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = json_dir / f"{ts}.json"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(weather_data, f, indent=4, ensure_ascii=False)

    print(f"✅ JSON gespeichert: {json_path}")

    # copy_to_classified nur tagsüber (wenn ein Bild da ist)
    if is_daylight and old_path:
        classify.copy_to_classified(weather_data, old_path, json_path, classified_base_dir)


if __name__ == "__main__":
    main()

