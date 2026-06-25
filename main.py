#!/usr/bin/env python3
"""
BoothBloom — Korean Aesthetic Photobooth
Entry point for Pop!_OS / Linux (PyQt6)

Usage:
    python main.py
"""

import sys
import os

# Make sure local packages resolve correctly
sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ui.main_window import MainWindow


def main():
    # HiDPI support
    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")

    app = QApplication(sys.argv)
    app.setApplicationName("BoothBloom")
    app.setApplicationDisplayName("✦ BoothBloom — Korean Photobooth")

    # Default font
    font = QFont("Noto Sans", 10)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
