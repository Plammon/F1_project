"""Build a Windows executable with PyInstaller."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import PyInstaller.__main__

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
ENTRYPOINT = SRC / "f1_predictor" / "__main__.py"
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"
RELEASE_DIR = DIST_DIR / "F1Predictor"
ICON_PATH = ROOT / "assets" / "f1_predictor.ico"
VERSION_FILE = BUILD_DIR / "windows_version_info.txt"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from f1_predictor import __version__


def write_version_file() -> None:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    VERSION_FILE.write_text(
        "\n".join(
            [
                "VSVersionInfo(",
                "  ffi=FixedFileInfo(",
                "    filevers=(0, 2, 0, 0),",
                "    prodvers=(0, 2, 0, 0),",
                "    mask=0x3f,",
                "    flags=0x0,",
                "    OS=0x40004,",
                "    fileType=0x1,",
                "    subtype=0x0,",
                "    date=(0, 0)",
                "  ),",
                "  kids=[",
                "    StringFileInfo([",
                "      StringTable(",
                "        '040904B0',",
                "        [",
                "          StringStruct('CompanyName', 'DNF Squad'),",
                "          StringStruct('FileDescription', 'F1 Predictor Desktop App'),",
                "          StringStruct('FileVersion', '0.2.0'),",
                "          StringStruct('InternalName', 'F1Predictor'),",
                "          StringStruct('OriginalFilename', 'F1Predictor.exe'),",
                "          StringStruct('ProductName', 'F1 Predictor'),",
                "          StringStruct('ProductVersion', '0.2.0')",
                "        ]",
                "      )",
                "    ]),",
                "    VarFileInfo([VarStruct('Translation', [1033, 1200])])",
                "  ]",
                ")",
            ]
        ),
        encoding="utf-8",
    )


def main() -> None:
    shutil.rmtree(RELEASE_DIR, ignore_errors=True)
    write_version_file()

    args = [
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        "F1Predictor",
        "--paths",
        str(SRC),
        "--version-file",
        str(VERSION_FILE),
        "--exclude-module",
        "torch",
        "--exclude-module",
        "torchvision",
        "--exclude-module",
        "tensorflow",
        "--exclude-module",
        "tensorboard",
        "--distpath",
        str(DIST_DIR),
        "--workpath",
        str(BUILD_DIR),
    ]
    if ICON_PATH.exists():
        args.extend(["--icon", str(ICON_PATH)])
    args.append(str(ENTRYPOINT))
    PyInstaller.__main__.run(args)

    exe_path = RELEASE_DIR / "F1Predictor.exe"
    print(f"Built executable at: {exe_path}")
    if not exe_path.exists():
        raise SystemExit("Expected executable was not created.")

    readme_path = RELEASE_DIR / "README-Run.txt"
    readme_path.write_text(
        "F1 Predictor\n"
        "===========\n\n"
        "1. Double-click F1Predictor.exe to launch the desktop app.\n"
        f"2. This release is built from app version {__version__}.\n"
        "3. The app uses live FastF1 data, so internet access may be required.\n"
        "4. If Windows SmartScreen appears, choose More info -> Run anyway.\n"
        "5. Runtime logs are written to the logs folder next to the app when available.\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
