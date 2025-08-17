import shutil
from pathlib import Path

def classify_weather(weather_json: dict) -> None:
    """
    Erstellt eine einfache englische Klassifikation und speichert sie
    direkt ins übergebene JSON-Objekt:

    - weather_json["classification"] = "<coverage> [with <phenomenon>][ (storm)]"
    - weather_json["classification_detail"] = {
          "coverage": "clear|few clouds|scattered clouds|broken clouds|overcast clouds",
          "phenomenon": "rain|snow|thunderstorm|drizzle|fog|...|None",
          "storm": true|false,
          "wind_speed_ms": <float or None>,
          "clouds_percent": <int or None>,
          "weather_id": <int or None>,
      }

    Regeln:
      clouds.all -> coverage
      weather[0].id/main -> phenomenon
      wind.speed >= 17.0 m/s -> storm
    """
    # ---- Eingaben robust lesen
    clouds = weather_json.get("clouds", {}).get("all", None)
    try:
        clouds = int(clouds) if clouds is not None else None
    except Exception:
        clouds = None

    w0 = (weather_json.get("weather") or [{}])[0]
    wid = w0.get("id")
    try:
        wid = int(wid) if wid is not None else None
    except Exception:
        wid = None
    wmain = (w0.get("main") or "").strip()

    wind_speed = weather_json.get("wind", {}).get("speed", None)
    try:
        wind_speed = float(wind_speed) if wind_speed is not None else None
    except Exception:
        wind_speed = None

    # ---- 1) Base coverage nach clouds.all
    if isinstance(clouds, int):
        if clouds <= 10:
            coverage = "clear"
        elif clouds <= 25:
            coverage = "few clouds"
        elif clouds <= 50:
            coverage = "scattered clouds"
        elif clouds <= 84:
            coverage = "broken clouds"
        else:
            coverage = "overcast clouds"
    else:
        # Fallback: wenn Prozent fehlt, am "main" grob orientieren
        coverage = "overcast clouds" if wmain == "Clouds" else "clear"

    # ---- 2) Phenomenon aus id/main (sehr einfach gehalten)
    phenomenon = None
    if isinstance(wid, int):
        if 200 <= wid <= 232:
            phenomenon = "thunderstorm"
        elif 300 <= wid <= 321:
            phenomenon = "drizzle"
        elif 500 <= wid <= 531:
            phenomenon = "rain"
        elif 600 <= wid <= 622:
            phenomenon = "snow"
        elif 700 <= wid <= 781:
            # Atmosphere (mist, fog, haze, dust, etc.)
            phenomenon = (wmain or "atmosphere").lower()
        # 800–804: clear/clouds → kein separates phenomenon nötig
    else:
        # Kein id vorhanden: falls main etwas anderes als Clouds/Clear ist, nutzen
        if wmain and wmain not in ("Clouds", "Clear"):
            phenomenon = wmain.lower()

    # ---- 3) Sturm-Kennzeichnung aus Wind (>= 17 m/s ~ 61 km/h)
    storm = bool(wind_speed is not None and wind_speed >= 17.0)

    # ---- 4) zusammengesetztes Label
    parts = [coverage]
    if phenomenon:
        parts.append(f"with {phenomenon}")
    if storm:
        parts.append("(storm)")
    classification = " ".join(parts)

    # ---- 5) ins JSON schreiben
    weather_json["classification"] = classification
    weather_json["classification_detail"] = {
        "coverage": coverage,
        "phenomenon": phenomenon,
        "storm": storm,
        "wind_speed_ms": wind_speed,
        "clouds_percent": clouds,
        "weather_id": wid,
    }


def copy_to_classified(weather_json: dict, old_path: Path, json_path: Path, classified_base_dir: Path) -> Path:
    """
    Kopiert JPG + JSON in einen Unterordner von `classified_base_dir`,
    benannt nach weather_json["classification"] (auto-angelegt).

    Params
    ------
    weather_json : dict        # enthält "classification"
    old_path     : Path        # Pfad zum Quellbild (jpg/old/<timestamp>.jpg)
    json_path    : Path        # Pfad zur JSON-Datei (json/<timestamp>.json)
    classified_base_dir : Path # z.B. base / "jpg" / "classified"

    Returns
    -------
    Path : Ziel-Unterordner (classified/<safe_label>)
    """
    classification_label = weather_json.get("classification", "unclassified")

    # minimal sanitisieren → ordnerfreundlich
    safe_label = "".join(c for c in classification_label if c.isalnum() or c in (" ", "_", "-")).strip()
    safe_label = safe_label.replace(" ", "_").lower() or "unclassified"

    target_dir = classified_base_dir / safe_label
    target_dir.mkdir(parents=True, exist_ok=True)

    dst_img = target_dir / old_path.name
    dst_json = target_dir / json_path.name

    shutil.copy2(old_path, dst_img)
    shutil.copy2(json_path, dst_json)

    print(f"📁 Kopiert nach: {target_dir}")
    print(f"   - {dst_img.name}")
    print(f"   - {dst_json.name}")

    return target_dir