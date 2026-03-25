"""Build a Windows executable with PyInstaller."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import PyInstaller.__main__

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
ENTRYPOINT = SRC / "f1_predictor" / "__main__.py"
DATA_DIR = ROOT / "data"
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"


def main() -> None:
    separator = ";" if os.name == "nt" else ":"
    PyInstaller.__main__.run(
        [
            "--noconfirm",
            "--clean",
            "--windowed",
            "--name",
            "F1Predictor",
            "--paths",
            str(SRC),
            "--exclude-module",
            "torch",
            "--exclude-module",
            "torchvision",
            "--exclude-module",
            "tensorflow",
            "--exclude-module",
            "tensorboard",
            "--add-data",
            f"{DATA_DIR}{separator}data",
            "--distpath",
            str(DIST_DIR),
            "--workpath",
            str(BUILD_DIR),
            str(ENTRYPOINT),
        ]
    )

    exe_path = DIST_DIR / "F1Predictor" / "F1Predictor.exe"
    print(f"Built executable at: {exe_path}")
    if not exe_path.exists():
        raise SystemExit("Expected executable was not created.")

    readme_path = DIST_DIR / "F1Predictor" / "README-Run.txt"
    readme_path.write_text(
        "F1 Predictor\n"
        "===========\n\n"
        "1. Double-click F1Predictor.exe to launch the desktop app.\n"
        "2. Keep the bundled data folder next to the exe.\n"
        "3. If Windows SmartScreen appears, choose More info -> Run anyway.\n",
        encoding="utf-8",
    )

    source_data_file = DATA_DIR / "sample_race_data.json"
    copied_data_dir = DIST_DIR / "F1Predictor" / "data"
    copied_data_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_data_file, copied_data_dir / source_data_file.name)


if __name__ == "__main__":
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    main()
