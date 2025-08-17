import json
import shutil
from pathlib import Path
from modules.capture import capture_fswebcam
from modules.upload import upload
from modules import openweathermap
from modules import classify

def main():
    base = Path(__file__).parent

    # Konfiguration laden
    cfg_path = base / "config.local.json"
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    # Leeres JSON Objekt
    weather_data = {}

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

    # Bild aufnehmen (Skript legt es in jpg/current/IMG_4903.jpg ab)
    img_path = capture_fswebcam(script_path)
    print("➡️ img_path:", img_path)

    # Nach jpg/old/ verschieben (dauerhaftes Archiv mit Timestamp)
    old_path = old_dir / img_path.name
    shutil.move(str(img_path), str(old_path))
    print("📸 Bild verschoben nach:", old_path)

    # old_path in JSON speichern
    weather_data["old_path"] = str(old_path)

    # Upload aus dem current-Verzeichnis (das Shellskript kümmert sich darum)
    upload(cfg, fixed_path)
    print("➡️ Upload:", fixed_path)

    # OpenWeatherMap-Daten abrufen und ins JSON mergen
    openweathermap.getOpenweathermapData(weather_data, cfg)

    # Klassifikation hinzufügen
    classify.classify_weather(weather_data)

    # JSON-Dateiname passend zum Bildnamen (gleicher Stem)
    json_path = json_dir / (old_path.stem + ".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(weather_data, f, indent=4, ensure_ascii=False)

    print(f"✅ JSON gespeichert: {json_path}")
    print(json.dumps(weather_data, indent=4, ensure_ascii=False))

    # === Kopie in classified/<classification>/ ablegen ===
    classified_base_dir = base / "jpg" / "classified"
    classify.copy_to_classified(weather_data, old_path, json_path, classified_base_dir)


if __name__ == "__main__":
    main()
