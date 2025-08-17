from pathlib import Path
import subprocess

def capture_fswebcam(script_path: Path = Path("./02_take_webcam_picture.sh")) -> Path | None:
    result = subprocess.run(
        [str(script_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode == 3:
        # Nacht/Skip
        return None
    elif result.returncode != 0:
        raise RuntimeError(
            f"Fehler beim Ausführen von {script_path}: {result.stderr.strip()}"
        )

    image_path_str = result.stdout.strip()
    if not image_path_str:
        return None

    # Pfad normalisieren!
    image_path = Path(image_path_str).resolve()

    if not image_path.exists():
        raise FileNotFoundError(f"Ausgegebenes Bild existiert nicht: {image_path}")

    return image_path
