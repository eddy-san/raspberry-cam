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

def main():
    base = Path(__file__).parent

    # Konfiguration laden
    cfg_path = base / "config.local.json"
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    # Pfade
    scripts_dir = base / "modules"
    script_path = scripts_dir / "02_take_webcam_picture.sh"
    current_dir = base / "jpg" / "current"
    old_dir = base / "jpg" / "old"
    json_dir = base / "json"
    fixed_path = current_dir / "IMG_4903.jpg"

    # Ordner sicherstellen
    current_dir.mkdir(parents=True, exist_ok=True)
    old_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)

    # Bild aufnehmen
    img_path = capture_fswebcam(script_path)

    # === Nacht / kein Bild ===
    if img_path is None or not img_path.exists():
        print("🌙 Kein Bild aufgenommen (Nacht oder Skip) – keine Verarbeitung.")
        sys.exit(0)

    print("➡️ img_path:", img_path)

    # Ab hier nur wenn ein Bild existiert
    # Nach jpg/old/ verschieben
    old_path = old_dir / img_path.name
    shutil.move(str(img_path), str(old_path))
    print("📸 Bild verschoben nach:", old_path)

    # Upload (z. B. für Webseite o.ä.)
    upload(cfg, fixed_path)
    print("➡️ Upload:", fixed_path)

    # ==== Pure Pipeline ====
    owm = openweathermap.get_openweathermap(cfg)               # dict
    classification, classification_detail = classify.classify_weather(owm)  # tuple
    storm = tick(cfg, owm)                                     # dict

    # Alles zusammenführen
    weather_data = {
        "timestamp": datetime.datetime.now().isoformat(),  # Zeitpunkt der Speicherung
        "old_path": str(old_path),
        "openweathermap": owm,
        "classification": classification,
        "classification_detail": classification_detail,
        "stormwarning": storm,
    }

    # JSON speichern
    json_path = json_dir / (old_path.stem + ".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(weather_data, f, indent=4, ensure_ascii=False)

    print(f"✅ JSON gespeichert: {json_path}")
    print(json.dumps(weather_data, indent=4, ensure_ascii=False))

    # In classified ablegen (benötigt classification auf Top-Ebene)
    classified_base_dir = base / "jpg" / "classified"
    classify.copy_to_classified(weather_data, old_path, json_path, classified_base_dir)

if __name__ == "__main__":
    main()
