"""Версия приложения. Читается из version.txt."""

from pathlib import Path

_VERSION_FILE = Path(__file__).parent.parent / "version.txt"

def _read_version() -> str:
    try:
        return _VERSION_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        return "0.0.0"

VERSION = _read_version()