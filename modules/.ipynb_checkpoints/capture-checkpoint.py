from pathlib import Path
import subprocess

def capture_fswebcam(script_path: Path = Path("./02_take_webcam_picture.sh")) -> Path:
    """
    Führt das Shellskript zum Aufnehmen eines Webcam-Bildes aus.
    Erwartet, dass das Skript den absoluten Bildpfad auf stdout ausgibt.
    Gibt diesen Pfad als pathlib.Path zurück.
    """
    try:
        # Skript ausführen, stdout einlesen
        result = subprocess.run(
            [str(script_path)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Fehler beim Ausführen von {script_path}: {e.stderr.strip()}") from e

    # Pfad aus stdout holen
    image_path_str = result.stdout.strip()
    if not image_path_str:
        raise ValueError(f"{script_path} hat keinen Pfad ausgegeben")

    image_path = Path(image_path_str)

    if not image_path.exists():
        raise FileNotFoundError(f"Ausgegebenes Bild existiert nicht: {image_path}")

    return image_path

