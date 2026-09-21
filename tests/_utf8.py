"""Forca UTF-8 no stdout/stderr (Windows cp1252 quebra simbolos de naipe)."""
import sys


def setup():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass
