"""Entry point for PyInstaller builds."""
import sys
import os

# Ensure the package is importable when frozen
if getattr(sys, "frozen", False):
    base = sys._MEIPASS
    if base not in sys.path:
        sys.path.insert(0, base)

from lmupi.app import run

if __name__ == "__main__":
    run()
