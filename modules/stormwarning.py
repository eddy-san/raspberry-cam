import smtplib
from email.message import EmailMessage
import json
import time
from pathlib import Path
import argparse
from typing import Dict, Any, Tuple, Optional

def _send_mail(cfg, subject, body):
    with smtplib.SMTP(cfg["smtp_server"], cfg["smtp_port"]) as server:
        server.starttls()
        server.login(cfg["smtp_user"], cfg["smtp_pass"])
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = cfg["from"]
        msg["To"] = cfg["to"]
        msg.set_content(body)
        server.send_message(msg)

def send_test_mail(cfg):
    _send_mail(cfg, "Stormwarning Test-Mail", "Dies ist eine Test-Mail aus stormwarning.py")

def _get_defaults(cfg):
    s = cfg.get("storm", {})
    base_dir = Path(__file__).resolve().parent.parent
    state_dir = (base_dir / "json" / "stormwarning")
    state_dir.mkdir(parents=True, exist_ok=True)
    return {
        "watch_wind": float(s.get("watch_wind", 13.0)),
        "storm_wind": float(s.get("storm_wind", 17.0)),
        "state_file": state_dir / "storm_state.json",
        "units": s.get("units", "m/s"),
        "location": s.get("location", "N/A"),
    }

def _load_state(path: Path):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"state": "OK", "last_update": 0.0}

def _save_state(path: Path, state):
    path.write_text(json.dumps(state), encoding="utf-8")

def _level(speed, gust, watch_wind, storm_wind):
    m = speed if gust is None else max(speed, gust)
    if m >= storm_wind:
        return "STORM"
    if m >= watch_wind:
        return "WATCH"
    return "OK"

def _extract_wind(owm: Dict[str, Any]) -> Tuple[float, Optional[float], str]:
    wind = owm.get("wind", {}) or {}
    speed = wind.get("speed")
    gust = wind.get("gust", None)
    try:
        speed = float(speed) if speed is not None else 0.0
    except Exception:
        speed = 0.0
    if gust is not None:
        try:
            gust = float(gust)
        except Exception:
            gust = None
    location = owm.get("name", "N/A")
    return speed, gust, location

def tick(cfg: Dict[str, Any], owm: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pure: nimmt OWM-Daten und gibt nur das Stormwarning-Resultat zurück.
    """
    d = _get_defaults(cfg)
    speed, gust, location = _extract_wind(owm)

    state = _load_state(d["state_file"])
    prev = state.get("state", "OK")
    new = _level(speed, gust, d["watch_wind"], d["storm_wind"])

    mailed = False
    if new != prev:
        gust_txt = "" if gust is None else f", Böe: {gust:.1f} {d['units']}"
        subject = f"[Stormwarning] {location}: {new}"
        body = (
            f"Ort: {location}\n"
            f"Zustand: {prev} → {new}\n"
            f"Aktueller Wind: {speed:.1f} {d['units']}{gust_txt}\n"
            f"Schwellen: WATCH ≥ {d['watch_wind']:.1f} {d['units']}, "
            f"STORM ≥ {d['storm_wind']:.1f} {d['units']}\n"
        )
        _send_mail(cfg, subject, body)
        mailed = True

    state["state"] = new
    state["last_update"] = time.time()
    _save_state(d["state_file"], state)

    result = {
        "prev_state": prev,
        "new_state": new,
        "mailed": mailed,
        "wind_speed": speed,
        "wind_gust": gust,
        "location": location,
        "state_file": str(d["state_file"]),
    }

    # keine Mutation des Aufruf-JSONs
    print(f"[Stormwarning] {location}: {prev} → {new} (Mail: {mailed})")
    return result

# CLI (nur Testmail)
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stormwarning")
    parser.add_argument("--sendtestmail", action="store_true", help="Nur eine Test-Mail verschicken")
    args = parser.parse_args()

    cfg_path = Path(__file__).resolve().parent.parent / "config.local.json"
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config-Datei nicht gefunden: {cfg_path}")
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))

    if args.sendtestmail:
        send_test_mail(cfg)
        print("Testmail verschickt.")
    else:
        print("Kein OWM-Objekt übergeben. Importiere dieses Modul und rufe tick(cfg, owm) aus main.py auf.")
