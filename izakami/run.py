"""Launcher: python run.py"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
if (ROOT / "libs").is_dir():  # fallback install mode (no virtual environment)
    sys.path.insert(0, str(ROOT / "libs"))

from izakami.app import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
