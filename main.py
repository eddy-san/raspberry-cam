import json
import shutil
from pathlib import Path
from modules.capture import capture_fswebcam
from modules.upload import upload


def main():
    with open("config.local.json", "r", encoding="utf-8") as f:
        cfg = json.load(f)

    base = Path(__file__).parent
    script_path = base / "modules" / "02_take_webcam_picture.sh"

    # Bild aufnehmen → jpg/current/...
    img_path = capture_fswebcam(script_path)
    print("➡️ img_path:", img_path);

    # Nach jpg/old/ verschieben
    old_dir = base / "jpg" / "old"
    old_dir.mkdir(parents=True, exist_ok=True)
    old_path = old_dir / img_path.name
    shutil.move(str(img_path), str(old_path))
    print("📸 Bild verschoben nach:", old_path)

    # Feste Upload-Quelle erzeugen (jpg/IMG_4903.jpg)
    fixed_path = base / "jpg" / "current"/ "IMG_4903.jpg"
    upload(cfg, fixed_path)
    print("➡️ Upload:", fixed_path)




if __name__ == "__main__":
    main()
