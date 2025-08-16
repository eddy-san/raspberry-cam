import os
import subprocess
from pathlib import Path

def upload(cfg: dict, target_path: Path):
    """
    Führt den Upload via 03_upload.sh (liegt im modules/ Ordner) aus.
    """
    # Korrekt: Skript liegt in modules/
    script_path = Path(__file__).parent / "03_upload_picture.sh"

    env = os.environ.copy()
    env["REMOTE_USER"] = cfg["remote_user"]
    env["REMOTE_HOST"] = cfg["remote_host"]
    env["PASSWORD"]    = cfg["password"]

    subprocess.run(
        [str(script_path),
         cfg["remote_path"],
         cfg["remote_file"],
         str(target_path)],
        check=True,
        env=env
    )
    print(f"✅ Upload erfolgreich: {target_path} -> {cfg['remote_path']}{cfg['remote_file']}")
