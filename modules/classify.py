import shutil
from pathlib import Path
from typing import Tuple, Dict, Any

def classify_weather(owm: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """
    Nimmt OWM-Objekt (Roh-JSON) und gibt (classification, classification_detail) zurück.
    Mutiert NICHT das übergebene Objekt.
    """
    clouds = owm.get("clouds", {}).get("all", None)
    try:
        clouds = int(clouds) if clouds is not None else None
    except Exception:
        clouds = None

    w0list = owm.get("weather") or [{}]
    w0 = w0list[0] if isinstance(w0list, list) and w0list else {}
    wid = w0.get("id")
    try:
        wid = int(wid) if wid is not None else None
    except Exception:
        wid = None
    wmain = (w0.get("main") or "").strip()

    wind_speed = owm.get("wind", {}).get("speed", None)
    try:
        wind_speed = float(wind_speed) if wind_speed is not None else None
    except Exception:
        wind_speed = None

    # coverage
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
        coverage = "overcast clouds" if wmain == "Clouds" else "clear"

    # phenomenon
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
            phenomenon = (wmain or "atmosphere").lower()
    else:
        if wmain and wmain not in ("Clouds", "Clear"):
            phenomenon = wmain.lower()

    # storm flag
    storm = bool(wind_speed is not None and wind_speed >= 17.0)

    parts = [coverage]
    if phenomenon:
        parts.append(f"with {phenomenon}")
    if storm:
        parts.append("(storm)")
    classification = " ".join(parts)

    detail = {
        "coverage": coverage,
        "phenomenon": phenomenon,
        "storm": storm,
        "wind_speed_ms": wind_speed,
        "clouds_percent": clouds,
        "weather_id": wid,
    }
    return classification, detail


def copy_to_classified(weather_json: dict, old_path: Path, json_path: Path, classified_base_dir: Path) -> Path:
    """Unverändert: nutzt classification auf Top-Level für Zielordner."""
    classification_label = weather_json.get("classification", "unclassified")
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
