"""
Printer module — wraps Qt's QPrinter for photobooth printing.
"""

from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
from PyQt6.QtGui import QPixmap, QPainter
from PyQt6.QtCore import QRectF
from PyQt6.QtWidgets import QApplication


def print_photo(pixmap: QPixmap, parent=None) -> bool:
    """Open a print dialog and print the given pixmap. Returns True on success."""
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setPageOrientation(__import__("PyQt6.QtGui", fromlist=["QPageLayout"]).QPageLayout.Orientation.Portrait)

    dialog = QPrintDialog(printer, parent)
    dialog.setWindowTitle("Cetak Foto")

    if dialog.exec() != QPrintDialog.DialogCode.Accepted:
        return False

    painter = QPainter(printer)
    rect = painter.viewport()
    scaled = pixmap.scaled(rect.width(), rect.height(),
                           __import__("PyQt6.QtCore", fromlist=["Qt"]).Qt.AspectRatioMode.KeepAspectRatio,
                           __import__("PyQt6.QtCore", fromlist=["Qt"]).Qt.TransformationMode.SmoothTransformation)
    x = (rect.width() - scaled.width()) // 2
    y = (rect.height() - scaled.height()) // 2
    painter.drawPixmap(x, y, scaled)
    painter.end()
    return True
