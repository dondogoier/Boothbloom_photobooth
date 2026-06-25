"""
main_window.py — Korean-aesthetic photobooth UI
Built with PyQt6. Designed for Pop!_OS / Linux.
"""

import os
import sys
import time
import datetime
import cv2
import numpy as np
import math

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QPushButton,
    QHBoxLayout, QVBoxLayout, QGridLayout,
    QScrollArea, QFrame, QSizePolicy,
    QGraphicsOpacityEffect, QFileDialog,
    QMessageBox, QStackedWidget, QSlider, QComboBox,
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QPropertyAnimation,
    QEasingCurve, QSize, QRect, pyqtProperty, QObject,
)
from PyQt6.QtGui import (
    QImage, QPixmap, QPainter, QPainterPath, QColor,
    QFont, QLinearGradient, QBrush, QPen, QFontDatabase,
    QIcon, QKeySequence, QShortcut,
)

from filters.photo_filters import apply_filter, FILTER_NAMES, FILTER_ICONS
from printer.print_handler import print_photo


# ── constants ─────────────────────────────────────────────────────────────────

PHOTOS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "photos")
FRAMES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "frames")
BG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "backgrounds")
os.makedirs(PHOTOS_DIR, exist_ok=True)

PALETTE = {
    "bg":          "#0D0D14",
    "surface":     "#13131E",
    "card":        "#1A1A2E",
    "border":      "#2A2A45",
    "accent1":     "#E8A0BF",   # Blush rose
    "accent2":     "#BAD7E9",   # Mist blue
    "accent3":     "#FFDDD2",   # Peach
    "accent4":     "#C9B8FF",   # Lavender
    "text":        "#F0EEF8",
    "text_muted":  "#8882AA",
    "success":     "#A8D5BA",
    "danger":      "#FF8FAB",
}

# Background gambar diambil otomatis dari folder assets/backgrounds/
# Tinggal taruh file JPG/PNG ke folder itu, langsung muncul di UI
def _scan_backgrounds() -> list[str]:
    """Return list of image filenames found in assets/backgrounds/."""
    exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    if not os.path.isdir(BG_DIR):
        return []
    return sorted(
        f for f in os.listdir(BG_DIR)
        if os.path.splitext(f)[1].lower() in exts
    )

BUILT_IN_FRAMES = [
    "None",
    "Simple White",
    "Film Strip",
    "Polaroid",
    "Heart Deco",
    "Star Deco",
    "Double Thin",
]



# ── Camera thread ──────────────────────────────────────────────────────────────

class CameraThread(QThread):
    frame_ready = pyqtSignal(np.ndarray)
    error = pyqtSignal(str)

    def __init__(self, camera_index: int = 0): # 1 untuk kamera eksternal, 0 untuk internal
        super().__init__()
        self._running = False
        self._camera_index = camera_index

    def run(self):
        cap = cv2.VideoCapture(self._camera_index)
        if not cap.isOpened():
            self.error.emit("Kamera tidak ditemukan. Pastikan kamera terhubung.")
            return
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self._running = True
        while self._running:
            ok, frame = cap.read()
            if ok:
                self.frame_ready.emit(cv2.flip(frame, 1))
            else:
                time.sleep(0.01)
        cap.release()

    def stop(self):
        self._running = False
        self.wait()


# ── Styled widgets ─────────────────────────────────────────────────────────────

class GlowButton(QPushButton):
    """Pill-shaped button with subtle glow on hover."""

    def __init__(self, text: str, accent: str = PALETTE["accent1"],
                 parent=None, icon_text: str = ""):
        super().__init__(parent)
        self._accent = accent
        self._base_text = text
        self.setText(f"{icon_text}  {text}" if icon_text else text)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_style(False)
        self.setFixedHeight(44)
        self.setMinimumWidth(120)

    def _apply_style(self, hover: bool):
        alpha = "33" if not hover else "55"
        border_alpha = "AA" if hover else "66"
        self.setStyleSheet(f"""
            QPushButton {{
                background: {self._accent}{alpha};
                border: 1.5px solid {self._accent}{border_alpha};
                border-radius: 22px;
                color: {PALETTE['text']};
                font-size: 13px;
                font-weight: 600;
                padding: 0 20px;
                letter-spacing: 0.5px;
            }}
            QPushButton:pressed {{
                background: {self._accent}77;
            }}
        """)

    def enterEvent(self, e):
        self._apply_style(True)

    def leaveEvent(self, e):
        self._apply_style(False)


class FilterChip(QPushButton):
    """Compact chip for filter selection."""

    def __init__(self, name: str, icon: str, parent=None):
        super().__init__(parent)
        self._name = name
        self.setText(f"{icon}\n{name}")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(76, 68)
        self._update_style()
        self.toggled.connect(lambda _: self._update_style())

    def _update_style(self):
        checked = self.isChecked()
        if checked:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {PALETTE['accent4']}44;
                    border: 1.5px solid {PALETTE['accent4']};
                    border-radius: 14px;
                    color: {PALETTE['accent4']};
                    font-size: 11px;
                    font-weight: 700;
                    padding: 4px 2px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {PALETTE['card']};
                    border: 1px solid {PALETTE['border']};
                    border-radius: 14px;
                    color: {PALETTE['text_muted']};
                    font-size: 11px;
                    padding: 4px 2px;
                }}
                QPushButton:hover {{
                    border: 1px solid {PALETTE['accent4']}88;
                    color: {PALETTE['text']};
                }}
            """)


class BGChip(QPushButton):
    """Square chip for background image selection — shows a thumbnail."""

    def __init__(self, name: str, image_path: str, parent=None):
        super().__init__(parent)
        self._name = name
        self._image_path = image_path
        self.setCheckable(True)
        self.setToolTip(name)
        self.setFixedSize(64, 52)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Build thumbnail pixmap
        self._thumb: QPixmap | None = None
        if os.path.exists(image_path):
            pix = QPixmap(image_path)
            if not pix.isNull():
                self._thumb = pix.scaled(
                    60, 48,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )

        self._update_style()
        self.toggled.connect(lambda _: self._update_style())

    def _update_style(self):
        checked = self.isChecked()
        border = f"2.5px solid {PALETTE['accent1']}" if checked else f"1px solid {PALETTE['border']}"
        self.setStyleSheet(f"""
            QPushButton {{
                border: {border};
                border-radius: 10px;
                background: {PALETTE['card']};
            }}
            QPushButton:hover {{
                border: 1.5px solid {PALETTE['accent1']}88;
            }}
        """)
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._thumb:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            # Clip to rounded rect
            path = QPainterPath()
            path.addRoundedRect(2, 2, self.width() - 4, self.height() - 4, 8, 8)
            painter.setClipPath(path)
            # Center the thumbnail
            x = (self.width() - self._thumb.width()) // 2
            y = (self.height() - self._thumb.height()) // 2
            painter.drawPixmap(x, y, self._thumb)
            # Checked overlay
            if self.isChecked():
                painter.fillRect(self.rect(), QColor(232, 160, 191, 60))
            painter.end()
        else:
            # No image — show filename text
            painter = QPainter(self)
            painter.setPen(QColor(PALETTE["text_muted"]))
            painter.setFont(QFont("", 8))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                             os.path.splitext(self._name)[0][:8])
            painter.end()


class FrameChip(QPushButton):
    """Button chip for frame template selection."""

    def __init__(self, name: str, parent=None):
        super().__init__(parent)
        self.setText(name)
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(36)
        self._update_style()
        self.toggled.connect(lambda _: self._update_style())

    def _update_style(self):
        checked = self.isChecked()
        if checked:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {PALETTE['accent2']}44;
                    border: 1.5px solid {PALETTE['accent2']};
                    border-radius: 18px;
                    color: {PALETTE['accent2']};
                    font-size: 11px;
                    font-weight: 700;
                    padding: 0 14px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {PALETTE['card']};
                    border: 1px solid {PALETTE['border']};
                    border-radius: 18px;
                    color: {PALETTE['text_muted']};
                    font-size: 11px;
                    padding: 0 14px;
                }}
                QPushButton:hover {{
                    border-color: {PALETTE['accent2']}88;
                    color: {PALETTE['text']};
                }}
            """)


# ── Viewfinder ─────────────────────────────────────────────────────────────────

class ViewfinderLabel(QLabel):
    """Live camera preview with overlaid frame decoration and background."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._frame_name = "None"
        self._bg_pixmap: QPixmap | None = None   # image background
        self._current_pixmap: QPixmap | None = None
        self.setMinimumSize(640, 480)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(f"background: {PALETTE['bg']}; border-radius: 18px;")
        self._strip_count = 4  # default number of frames in a strip

    def set_strip_count(self, count: int): 
        self._strip_count = count
        self.update()

    def set_frame(self, name: str):
        self._frame_name = name
        self.update()

    def set_background_image(self, path: str | None):
        """Set a background image from file path. Pass None to clear."""
        if path and os.path.exists(path):
            self._bg_pixmap = QPixmap(path)
        else:
            self._bg_pixmap = None
        self.update()

    def update_pixmap(self, pix: QPixmap):
        self._current_pixmap = pix
        self.update()

    def paintEvent(self, event):

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()

        # Rounded clip
        path = QPainterPath()
        path.addRoundedRect(
            rect.x(),
            rect.y(),
            rect.width(),
            rect.height(),
            18,
            18
        )

        painter.setClipPath(path)

        # =========================
        # Background
        # =========================

        if self._bg_pixmap and not self._bg_pixmap.isNull():

            scaled_bg = self._bg_pixmap.scaled(
                rect.width(),
                rect.height(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )

            bx = (rect.width() - scaled_bg.width()) // 2
            by = (rect.height() - scaled_bg.height()) // 2

            painter.drawPixmap(
                bx,
                by,
                scaled_bg
            )

        else:

            painter.fillRect(
                rect,
                QColor(PALETTE["bg"])
            )

        # =========================
        # ── Layer 2: camera feed ──
        if self._current_pixmap:

            count = getattr(
                self,
                "_strip_count",
                4
            )

            margin = 16
            spacing = 12

            # Tentukan jumlah kolom
            if count == 1:
                cols = 1
            else:
                cols = 2

            rows = math.ceil(count / cols)

            grid_width = rect.width() - (margin * 2)
            grid_height = rect.height() - (margin * 2)

            cell_width = (
                grid_width - ((cols - 1) * spacing)
            ) // cols

            cell_height = (
                grid_height - ((rows - 1) * spacing)
            ) // rows

            for i in range(count):

                row = i // cols
                col = i % cols

                x = margin + (
                    col * (cell_width + spacing)
                )

                y = margin + (
                    row * (cell_height + spacing)
                )

                slot_rect = QRect(
                    x,
                    y,
                    cell_width,
                    cell_height
                )

                scaled = self._current_pixmap.scaled(
                    slot_rect.width(),
                    slot_rect.height(),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation
                )

                painter.drawPixmap(
                    slot_rect,
                    scaled,
                    scaled.rect()
                )

                painter.setPen(
                    QPen(
                        QColor(255, 255, 255, 180),
                        2
                    )
                )

                painter.drawRoundedRect(
                    slot_rect,
                    12,
                    12
                )

        # =========================
        # Frame Overlay
        # =========================

        self._draw_frame(
            painter,
            rect
        )

        painter.end()
    

    def _draw_frame(self, painter: QPainter, rect: QRect):
        name = self._frame_name
        w, h = rect.width(), rect.height()

        if name == "None":
            return

        elif name == "Simple White":
            pen = QPen(QColor("#FFFFFF"), 10)
            painter.setPen(pen)
            painter.drawRoundedRect(5, 5, w - 10, h - 10, 14, 14)

        elif name == "Film Strip":
            # Side sprocket holes
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 180))
            painter.drawRect(0, 0, 32, h)
            painter.drawRect(w - 32, 0, 32, h)
            painter.setBrush(QColor(255, 255, 255, 220))
            for i in range(0, h, 36):
                painter.drawRoundedRect(8, i + 4, 16, 22, 4, 4)
                painter.drawRoundedRect(w - 24, i + 4, 16, 22, 4, 4)

        elif name == "Polaroid":
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, 230))
            brd = 18
            btm = 70
            painter.drawRect(0, 0, w, brd)
            painter.drawRect(0, h - btm, w, btm)
            painter.drawRect(0, 0, brd, h)
            painter.drawRect(w - brd, 0, brd, h)

        elif name == "Heart Deco":
            painter.setPen(Qt.PenStyle.NoPen)
            self._draw_hearts_border(painter, w, h)

        elif name == "Star Deco":
            painter.setPen(Qt.PenStyle.NoPen)
            self._draw_stars_border(painter, w, h)

        elif name == "Double Thin":
            for offset, alpha in [(4, 180), (10, 100)]:
                pen = QPen(QColor(255, 255, 255, alpha), 2)
                painter.setPen(pen)
                painter.drawRoundedRect(offset, offset, w - offset * 2, h - offset * 2, 12, 12)

    def _draw_hearts_border(self, painter: QPainter, w: int, h: int):
        painter.setBrush(QColor(PALETTE["accent1"]))
        size = 20
        step = 50
        for x in range(step // 2, w, step):
            self._heart(painter, x, 14, size)
            self._heart(painter, x, h - 14, size)
        for y in range(step, h - step, step):
            self._heart(painter, 14, y, size)
            self._heart(painter, w - 14, y, size)

    def _heart(self, painter: QPainter, cx: int, cy: int, size: int):
        s = size / 2
        path = QPainterPath()
        path.moveTo(cx, cy + s * 0.6)
        path.cubicTo(cx - s, cy - s * 0.2, cx - s * 1.6, cy - s, cx, cy - s * 0.4)
        path.cubicTo(cx + s * 1.6, cy - s, cx + s, cy - s * 0.2, cx, cy + s * 0.6)
        painter.drawPath(path)

    def _draw_stars_border(self, painter: QPainter, w: int, h: int):
        painter.setBrush(QColor(PALETTE["accent4"]))
        size = 12
        step = 48
        for x in range(step // 2, w, step):
            self._star(painter, x, 14, size)
            self._star(painter, x, h - 14, size)
        for y in range(step, h - step, step):
            self._star(painter, 14, y, size)
            self._star(painter, w - 14, y, size)

    def _star(self, painter: QPainter, cx: int, cy: int, r: int):
        import math
        path = QPainterPath()
        for i in range(10):
            angle = math.pi * i / 5 - math.pi / 2
            radius = r if i % 2 == 0 else r * 0.45
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        path.closeSubpath()
        painter.drawPath(path)


# ── Main window ────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("✦ BoothBloom — Korean Photobooth")
        self.setMinimumSize(1200, 760)
        self._is_fullscreen = False

        # State
        self._current_filter = "Normal"
        self._current_bg_path: str | None = None   # path gambar background aktif
        self._current_frame = "None"
        self._last_frame: np.ndarray | None = None
        self._captured_pixmap: QPixmap | None = None
        self._strip_count = 4
        self._captured_frames = []
        self._countdown_value = 0
        self._countdown_steps = 3          # user-selectable: 3, 5, or 10
        self._in_countdown = False         # blocks live frame updates during countdown
        self._countdown_timer = QTimer()
        self._countdown_timer.setInterval(1000)
        self._countdown_timer.timeout.connect(self._countdown_tick)

        self._build_ui()
        self._apply_global_style()
        self._start_camera()
        self._setup_shortcuts()

    # ── UI Build ────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Left sidebar
        sidebar = self._build_sidebar()
        root_layout.addWidget(sidebar, 0)

        # Center stage
        center = self._build_center()
        root_layout.addWidget(center, 1)

        # Right panel
        right = self._build_right_panel()
        root_layout.addWidget(right, 0)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setFixedWidth(240)
        sidebar.setObjectName("sidebar")
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 24, 16, 24)
        layout.setSpacing(20)

        # Logo
        logo = QLabel("✦\nBoothBloom")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setStyleSheet(f"""
            color: {PALETTE['accent1']};
            font-size: 22px;
            font-weight: 800;
            letter-spacing: 2px;
            line-height: 1.4;
        """)
        layout.addWidget(logo)

        div = self._divider()
        layout.addWidget(div)

        # ── Filters ────
        lbl_filter = self._section_label("✦ Filter")
        layout.addWidget(lbl_filter)

        filter_scroll = QScrollArea()
        filter_scroll.setWidgetResizable(True)
        filter_scroll.setFrameShape(QFrame.Shape.NoFrame)
        filter_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        filter_scroll.setStyleSheet("background: transparent;")
        filter_scroll.setFixedHeight(230)

        filter_container = QWidget()
        filter_container.setStyleSheet("background: transparent;")
        filter_grid = QGridLayout(filter_container)
        filter_grid.setSpacing(8)
        filter_grid.setContentsMargins(0, 0, 0, 0)

        self._filter_chips: dict[str, FilterChip] = {}
        from PyQt6.QtWidgets import QButtonGroup
        self._filter_group = QButtonGroup(self)
        self._filter_group.setExclusive(True)
        for i, name in enumerate(FILTER_NAMES):
            chip = FilterChip(name, FILTER_ICONS.get(name, "○"))
            self._filter_group.addButton(chip)
            chip.toggled.connect(lambda checked, n=name: self._on_filter_selected(n) if checked else None)
            self._filter_chips[name] = chip
            filter_grid.addWidget(chip, i // 3, i % 3)

        self._filter_chips["Normal"].setChecked(True)
        filter_scroll.setWidget(filter_container)
        layout.addWidget(filter_scroll)

        div2 = self._divider()
        layout.addWidget(div2)

        # ── Background ────
        lbl_bg = self._section_label("◈ Background")
        layout.addWidget(lbl_bg)

        bg_scroll = QScrollArea()
        bg_scroll.setWidgetResizable(True)
        bg_scroll.setFrameShape(QFrame.Shape.NoFrame)
        bg_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        bg_scroll.setStyleSheet("background: transparent;")
        bg_scroll.setFixedHeight(200)

        bg_container = QWidget()
        bg_container.setStyleSheet("background: transparent;")
        bg_grid = QGridLayout(bg_container)
        bg_grid.setSpacing(8)
        bg_grid.setContentsMargins(0, 0, 0, 0)

        self._bg_chips: dict[str, BGChip] = {}
        bg_files = _scan_backgrounds()

        if bg_files:
            for i, fname in enumerate(bg_files):
                full_path = os.path.join(BG_DIR, fname)
                display_name = os.path.splitext(fname)[0]  # tanpa ekstensi
                chip = BGChip(display_name, full_path)
                chip.toggled.connect(
                    lambda checked, n=display_name, p=full_path:
                    self._on_bg_selected(n, p) if checked else None
                )
                self._bg_chips[display_name] = chip
                bg_grid.addWidget(chip, i // 3, i % 3)
        else:
            # Folder kosong — tampilkan info
            empty_lbl = QLabel("Taruh gambar di\nassets/backgrounds/")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_lbl.setStyleSheet(f"""
                color: {PALETTE['text_muted']};
                font-size: 11px;
                border: 1px dashed {PALETTE['border']};
                border-radius: 10px;
                padding: 10px;
            """)
            bg_grid.addWidget(empty_lbl, 0, 0, 1, 3)

        # Tombol "No BG"
        row_no_bg = (len(bg_files) // 3) + (1 if len(bg_files) % 3 else 0)
        self._bg_none_btn = GlowButton("✕  No BG", PALETTE["border"])
        self._bg_none_btn.setFixedHeight(32)
        self._bg_none_btn.clicked.connect(self._clear_bg)
        bg_grid.addWidget(self._bg_none_btn, max(row_no_bg, 1), 0, 1, 3)

        bg_scroll.setWidget(bg_container)
        layout.addWidget(bg_scroll)

        # Tombol refresh (untuk scan ulang folder tanpa restart)
        btn_refresh = GlowButton("↻  Refresh BG", PALETTE["accent2"])
        btn_refresh.setFixedHeight(30)
        btn_refresh.clicked.connect(self._refresh_backgrounds)
        layout.addWidget(btn_refresh)

        layout.addStretch()

        # Version tag
        ver = QLabel("v1.0  ·  Pop!_OS")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ver.setStyleSheet(f"color: {PALETTE['text_muted']}; font-size: 11px;")
        layout.addWidget(ver)

        return sidebar

    def _build_center(self) -> QWidget:
        center = QWidget()
        center.setObjectName("center")
        layout = QVBoxLayout(center)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Viewfinder
        self.viewfinder = ViewfinderLabel()
        layout.addWidget(self.viewfinder, 1)

        # Status label
        self._status_label = QLabel("카메라 연결 중…  /  Menghubungkan kamera…")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet(f"color: {PALETTE['text_muted']}; font-size: 12px;")
        layout.addWidget(self._status_label)

        # Controls row
        ctrl = self._build_controls()
        layout.addWidget(ctrl)

        return center

    def _build_controls(self) -> QWidget:
        outer = QWidget()
        outer_lay = QVBoxLayout(outer)
        outer_lay.setContentsMargins(0, 0, 0, 0)
        outer_lay.setSpacing(10)

        # ── Countdown duration selector ──────────────────────────────────────
        cd_row = QWidget()
        cd_lay = QHBoxLayout(cd_row)
        cd_lay.setContentsMargins(0, 0, 0, 0)
        cd_lay.setSpacing(8)

        cd_lbl = QLabel("⏱ Countdown :")
        cd_lbl.setStyleSheet(f"color: {PALETTE['text_muted']}; font-size: 12px;")
        cd_lay.addWidget(cd_lbl)

        self._cd_chips: dict[int, QPushButton] = {}
        for secs in (3, 5, 10):
            btn = QPushButton(f"{secs}s")
            btn.setCheckable(True)
            btn.setFixedSize(46, 28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked, s=secs: self._set_countdown_steps(s))
            self._cd_chips[secs] = btn
            cd_lay.addWidget(btn)

        self._cd_chips[3].setChecked(True)   # default
        self._apply_cd_chip_styles()

        cd_lay.addStretch()
        outer_lay.addWidget(cd_row)
        strip_row = QWidget()
        strip_lay = QHBoxLayout(strip_row)

        strip_lay.setContentsMargins(0,0,0,0)

        lbl_strip = QLabel("📸 Strip :")
        strip_lay.addWidget(lbl_strip)

        self._strip_combo = QComboBox()

        self._strip_combo.addItems([
            "2 Foto",
            "3 Foto",
            "4 Foto",
            "6 Foto"
        ])

        self._strip_combo.setCurrentText("4 Foto")

        self._strip_combo.currentTextChanged.connect(
            self._on_strip_changed
        )

        strip_lay.addWidget(self._strip_combo)
        strip_lay.addStretch()

        outer_lay.addWidget(strip_row)


        # ── Main action buttons ──────────────────────────────────────────────
        w = QWidget()
        layout = QHBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._btn_capture = GlowButton("Ambil Foto", PALETTE["accent1"], icon_text="◎")
        self._btn_capture.setFixedHeight(52)
        self._btn_capture.setFont(QFont("", 15, QFont.Weight.Bold))
        self._btn_capture.clicked.connect(self._start_countdown)

        self._btn_save = GlowButton("Simpan", PALETTE["accent2"], icon_text="↓")
        self._btn_save.setEnabled(False)
        self._btn_save.clicked.connect(self._save_photo)

        self._btn_print = GlowButton("Cetak", PALETTE["accent3"], icon_text="⊟")
        self._btn_print.setEnabled(False)
        self._btn_print.clicked.connect(self._print_photo)

        self._btn_fullscreen = GlowButton("Fullscreen", PALETTE["accent4"], icon_text="⤢")
        self._btn_fullscreen.clicked.connect(self._toggle_fullscreen)

        self._btn_retake = GlowButton("Ulangi", PALETTE["danger"], icon_text="↺")
        self._btn_retake.setEnabled(False)
        self._btn_retake.clicked.connect(self._retake)

        layout.addWidget(self._btn_retake)
        layout.addStretch()
        layout.addWidget(self._btn_capture)
        layout.addStretch()
        layout.addWidget(self._btn_save)
        layout.addWidget(self._btn_print)
        layout.addWidget(self._btn_fullscreen)

        outer_lay.addWidget(w)
        return outer

    def _set_countdown_steps(self, secs: int):
        self._countdown_steps = secs
        # Uncheck siblings
        for s, btn in self._cd_chips.items():
            btn.blockSignals(True)
            btn.setChecked(s == secs)
            btn.blockSignals(False)
        self._apply_cd_chip_styles()

    def _apply_cd_chip_styles(self):
        for secs, btn in self._cd_chips.items():
            if btn.isChecked():
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {PALETTE['accent1']}44;
                        border: 1.5px solid {PALETTE['accent1']};
                        border-radius: 14px;
                        color: {PALETTE['accent1']};
                        font-size: 12px;
                        font-weight: 700;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {PALETTE['card']};
                        border: 1px solid {PALETTE['border']};
                        border-radius: 14px;
                        color: {PALETTE['text_muted']};
                        font-size: 12px;
                    }}
                    QPushButton:hover {{
                        border-color: {PALETTE['accent1']}88;
                        color: {PALETTE['text']};
                    }}
                """)

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(220)
        panel.setObjectName("rightpanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 24, 16, 24)
        layout.setSpacing(16)

        lbl = self._section_label("◉ Frame")
        layout.addWidget(lbl)

        frame_container = QWidget()
        frame_container.setStyleSheet("background: transparent;")
        frame_lay = QVBoxLayout(frame_container)
        frame_lay.setContentsMargins(0, 0, 0, 0)
        frame_lay.setSpacing(8)

        self._frame_chips: dict[str, FrameChip] = {}

        from PyQt6.QtWidgets import QButtonGroup
        self._frame_group = QButtonGroup(self)
        self._frame_group.setExclusive(True)

        for name in BUILT_IN_FRAMES:
            chip = FrameChip(name)

            # WAJIB ditambahkan
            self._frame_group.addButton(chip)

            chip.toggled.connect(
                lambda checked, n=name:
                    self._on_frame_selected(n) if checked else None
            )

            self._frame_chips[name] = chip
            frame_lay.addWidget(chip)

        self._frame_chips["None"].setChecked(True)
        frame_lay.addStretch()
        layout.addWidget(frame_container)

        layout.addWidget(self._divider())

        # Preview of captured photo
        lbl_preview = self._section_label("✦ Hasil")
        layout.addWidget(lbl_preview)

        self._preview_label = QLabel()
        self._preview_label.setFixedHeight(180)
        self._preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview_label.setStyleSheet(f"""
            background: {PALETTE['card']};
            border: 1.5px dashed {PALETTE['border']};
            border-radius: 12px;
            color: {PALETTE['text_muted']};
            font-size: 12px;
        """)
        self._preview_label.setText("Belum ada foto")
        layout.addWidget(self._preview_label)

        layout.addStretch()

        # Gallery button
        self._btn_gallery = GlowButton("Buka Galeri", PALETTE["accent4"], icon_text="⊞")
        self._btn_gallery.clicked.connect(self._open_gallery)
        layout.addWidget(self._btn_gallery)

        return panel

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"""
            color: {PALETTE['text_muted']};
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1.5px;
        """)
        return lbl

    def _divider(self) -> QFrame:
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setFixedHeight(1)
        div.setStyleSheet(f"background: {PALETTE['border']}; border: none;")
        return div

    def _apply_global_style(self):
        self.setStyleSheet(f"""
            QMainWindow {{
                background: {PALETTE['bg']};
            }}
            QWidget {{
                background: {PALETTE['bg']};
                color: {PALETTE['text']};
                font-family: 'Noto Sans', 'Segoe UI', sans-serif;
            }}
            #sidebar, #rightpanel {{
                background: {PALETTE['surface']};
                border-right: 1px solid {PALETTE['border']};
            }}
            #rightpanel {{
                border-right: none;
                border-left: 1px solid {PALETTE['border']};
            }}
            QScrollBar:vertical {{
                width: 4px;
                background: transparent;
            }}
            QScrollBar::handle:vertical {{
                background: {PALETTE['border']};
                border-radius: 2px;
                min-height: 24px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Space"), self).activated.connect(self._start_countdown)
        QShortcut(QKeySequence("F11"), self).activated.connect(self._toggle_fullscreen)
        QShortcut(QKeySequence("Escape"), self).activated.connect(self._escape_pressed)

    # ── Camera ──────────────────────────────────────────────────────────────

    def _start_camera(self):
        self._cam_thread = CameraThread(0) #1 untuk kamera eksternal, 0 untuk internal
        self._cam_thread.frame_ready.connect(self._on_frame)
        self._cam_thread.error.connect(self._on_camera_error)
        self._cam_thread.start()

    def _on_frame(self, frame: np.ndarray):
        self._last_frame = frame
        if self._in_countdown:
            return   # let _show_countdown control the display
        filtered = apply_filter(frame, self._current_filter)
        rgb = cv2.cvtColor(filtered, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        img = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pix = QPixmap.fromImage(img)
        self.viewfinder.update_pixmap(pix)
        self._status_label.setText("● Live  ·  Tekan [Space] untuk mengambil foto")

    def _on_camera_error(self, msg: str):
        self._status_label.setText(f"⚠ {msg}")
        self._status_label.setStyleSheet(f"color: {PALETTE['danger']}; font-size: 12px;")

    # ── Countdown & Capture ─────────────────────────────────────────────────

    def _start_countdown(self):
        if self._countdown_timer.isActive():
            return
        self._btn_capture.setEnabled(False)
        self._in_countdown = True
        self._countdown_value = self._countdown_steps
        self._show_countdown(self._countdown_value)
        self._countdown_timer.start()

    def _countdown_tick(self):
        self._countdown_value -= 1
        if self._countdown_value <= 0:
            self._countdown_timer.stop()
            self._in_countdown = False
            self._capture_photo()
        else:
            self._show_countdown(self._countdown_value)

    def _show_countdown(self, n: int):
        """Paint countdown number directly onto a frozen camera frame."""
        if self._last_frame is None:
            self._status_label.setText(f"✦  {n}…")
            return

        # Render filtered frame
        filtered = apply_filter(self._last_frame, self._current_filter)
        rgb = cv2.cvtColor(filtered, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        pix = QPixmap.fromImage(
            QImage(rgb.data.tobytes(), w, h, ch * w, QImage.Format.Format_RGB888)
        )

        # Scale to fit viewfinder widget
        vf_size = self.viewfinder.size()
        pix = pix.scaled(vf_size, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                         Qt.TransformationMode.SmoothTransformation)

        # Paint the countdown number with a dark halo so it's readable on any bg
        painter = QPainter(pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Semi-transparent dark circle behind number
        cx, cy = pix.width() // 2, pix.height() // 2
        radius = min(pix.width(), pix.height()) // 5
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 120))
        painter.drawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)

        # Number text
        font = QFont("", int(radius * 1.1), QFont.Weight.Black)
        painter.setFont(font)

        # Shadow pass
        painter.setPen(QColor(0, 0, 0, 160))
        painter.drawText(pix.rect().adjusted(3, 3, 3, 3),
                         Qt.AlignmentFlag.AlignCenter, str(n))

        # Main pass – blush rose
        painter.setPen(QColor(PALETTE["accent1"]))
        painter.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, str(n))
        painter.end()

        self.viewfinder.update_pixmap(pix)
        self._status_label.setText(f"✦  {n}…  bersiaplah!")

    def _capture_photo(self):

        if self._last_frame is None:
            return

        filtered = apply_filter(
            self._last_frame,
            self._current_filter
        )

        rgb = cv2.cvtColor(
            filtered,
            cv2.COLOR_BGR2RGB
        )

        h, w, ch = rgb.shape

        img = QImage(
            rgb.data,
            w,
            h,
            ch * w,
            QImage.Format.Format_RGB888
        )

        pix = QPixmap.fromImage(img)

        self._captured_frames.append(
            pix
        )

        current = len(self._captured_frames)

        if current < self._strip_count:

            self._status_label.setText(
                f"Foto {current}/{self._strip_count} berhasil. Bersiap untuk foto berikutnya..."
            )

            QTimer.singleShot(
                1000,
                self._start_countdown
            )

            return

        strip = self._build_photo_strip(
            self._captured_frames
        )

        self._captured_frames.clear()

        self._captured_pixmap = strip

        self._preview_label.setPixmap(
            strip.scaled(
                self._preview_label.width() - 8,
                self._preview_label.height() - 8,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        )

        self._preview_label.setText("")

        self._btn_save.setEnabled(True)
        self._btn_print.setEnabled(True)
        self._btn_retake.setEnabled(True)
        self._btn_capture.setEnabled(False)

        self._status_label.setText(
            "✓ Photostrip siap disimpan"
        )

        self._status_label.setStyleSheet(
            f"color: {PALETTE['success']}; font-size: 12px;"
        )

    # ── Actions ─────────────────────────────────────────────────────────────
    def _save_photo(self):

        if self._captured_pixmap is None:
            return

        default_name = os.path.join(
            PHOTOS_DIR,
            f"photostrip_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        )

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Simpan Photostrip",
            default_name,
            "PNG (*.png);;JPEG (*.jpg)"
        )

        if not path:
            return

        self._captured_pixmap.save(path)

        self._status_label.setText(
            f"✓ Disimpan ke: {os.path.basename(path)}"
        )

        self._status_label.setStyleSheet(
            f"color: {PALETTE['success']}; font-size: 12px;"
        )

    def _print_photo(self):
        if not self._captured_pixmap:
            return
        ok = print_photo(self._captured_pixmap, self)
        if ok:
            self._status_label.setText("✓ Foto dikirim ke printer!")

    def _retake(self):
        self._captured_pixmap = None
        self._btn_capture.setEnabled(True)
        self._btn_save.setEnabled(False)
        self._btn_print.setEnabled(False)
        self._btn_retake.setEnabled(False)
        self._preview_label.setPixmap(QPixmap())
        self._preview_label.setText("Belum ada foto")
        self._status_label.setText("● Live  ·  Tekan [Space] untuk mengambil foto")
        self._status_label.setStyleSheet(f"color: {PALETTE['text_muted']}; font-size: 12px;")

    def _open_gallery(self):
        import subprocess
        subprocess.Popen(["xdg-open", PHOTOS_DIR])

    # ── Filter / BG / Frame selection ───────────────────────────────────────

    def _on_filter_selected(self, name: str):
        for n, chip in self._filter_chips.items():
            if n != name and chip.isChecked():
                chip.blockSignals(True)
                chip.setChecked(False)
                chip.blockSignals(False)
        self._current_filter = name

    def _on_bg_selected(self, name: str, path: str):
        # Uncheck semua chip lain
        for n, chip in self._bg_chips.items():
            if n != name and chip.isChecked():
                chip.blockSignals(True)
                chip.setChecked(False)
                chip.blockSignals(False)
        self._current_bg_path = path
        self.viewfinder.set_background_image(path)

    def _clear_bg(self):
        for chip in self._bg_chips.values():
            chip.blockSignals(True)
            chip.setChecked(False)
            chip.blockSignals(False)
        self._current_bg_path = None
        self.viewfinder.set_background_image(None)
    def _on_strip_changed(self, text):

        self._strip_count = int(
            text.split()[0]
        )

        self.viewfinder.set_strip_count(
            self._strip_count
        )

    def _refresh_backgrounds(self):
        bg_files = _scan_backgrounds()

        self._status_label.setText(
            f"✓ Ditemukan {len(bg_files)} background"
        )

        if self._current_bg_path:
            self.viewfinder.set_background_image(
                self._current_bg_path
            )

        # Scan ulang
        bg_files = _scan_backgrounds()
        self._status_label.setText(
            f"✓ Ditemukan {len(bg_files)} background. Restart app untuk muat ulang."
            if bg_files else
            "⚠ Tidak ada gambar di assets/backgrounds/"
        )

    def _on_frame_selected(self, name: str):
        for n, chip in self._frame_chips.items():
            if n != name and chip.isChecked():
                chip.blockSignals(True)
                chip.setChecked(False)
                chip.blockSignals(False)
        self._current_frame = name
        self.viewfinder.set_frame(name)

    # ── Fullscreen ───────────────────────────────────────────────────────────

    def _toggle_fullscreen(self):
        if self._is_fullscreen:
            self.showNormal()
            self._is_fullscreen = False
            self._btn_fullscreen.setText("⤢  Fullscreen")
        else:
            self.showFullScreen()
            self._is_fullscreen = True
            self._btn_fullscreen.setText("⤡  Windowed")

    def _escape_pressed(self):
        if self._is_fullscreen:
            self._toggle_fullscreen()

    # ── Cleanup ──────────────────────────────────────────────────────────────

    def closeEvent(self, event):
        self._cam_thread.stop()
        event.accept()

    def _build_photo_strip(self, pixmaps):

        width = 600
        spacing = 12
        margin = 20
        photo_h = 280

        total_h = (
            margin * 2
            + len(pixmaps) * photo_h
            + (len(pixmaps)-1) * spacing
        )

        result = QPixmap(width, total_h)
        result.fill(QColor("white"))

        painter = QPainter(result)

        y = margin

        # =====================
        # FILM STRIP DECORATION
        # =====================
        if hasattr(self, "_current_bg_path") and self._current_bg_path:

            bg = QPixmap(self._current_bg_path)

            if not bg.isNull():

                bg_scaled = bg.scaled(
                    result.size(),
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation
                )

                painter.drawPixmap(
                    0,
                    0,
                    bg_scaled
                )
        

        for pix in pixmaps:
            frame_name = getattr(
                self,
                "_current_frame",
                "None"
            )

            scaled = pix.scaled(
                width - 40,
                photo_h,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )

            painter.drawPixmap(
                20,
                y,
                scaled
            )

            y += photo_h + spacing
        # Terapkan frame yang dipilih ke hasil akhir
        frame_name = getattr(self, "_current_frame", "None")

        if frame_name == "Simple White":
            pen = QPen(QColor("#FFFFFF"), 10)
            painter.setPen(pen)
            painter.drawRoundedRect(
                5, 5,
                result.width() - 10,
                result.height() - 10,
                14, 14
            )

        elif frame_name == "Film Strip":

            w = result.width()
            h = result.height()

            painter.setPen(Qt.PenStyle.NoPen)

            painter.setBrush(QColor(0, 0, 0, 180))
            painter.drawRect(0, 0, 32, h)
            painter.drawRect(w - 32, 0, 32, h)

            painter.setBrush(QColor(255, 255, 255, 220))

            for i in range(0, h, 36):
                painter.drawRoundedRect(8, i + 4, 16, 22, 4, 4)
                painter.drawRoundedRect(w - 24, i + 4, 16, 22, 4, 4)

        elif frame_name == "Polaroid":

            w = result.width()
            h = result.height()

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(255, 255, 255, 230))

            brd = 18
            btm = 70

            painter.drawRect(0, 0, w, brd)
            painter.drawRect(0, h - btm, w, btm)
            painter.drawRect(0, 0, brd, h)
            painter.drawRect(w - brd, 0, brd, h)

        elif frame_name == "Heart Deco":

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(PALETTE["accent1"]))

            size = 20
            step = 50

            w = result.width()
            h = result.height()

            for x in range(step // 2, w, step):

                self.viewfinder._heart(
                    painter,
                    x,
                    14,
                    size
                )

                self.viewfinder._heart(
                    painter,
                    x,
                    h - 14,
                    size
                )

            for y in range(step, h - step, step):

                self.viewfinder._heart(
                    painter,
                    14,
                    y,
                    size
                )

                self.viewfinder._heart(
                    painter,
                    w - 14,
                    y,
                    size
                )


        elif frame_name == "Star Deco":

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(PALETTE["accent4"]))

            size = 12
            step = 48

            w = result.width()
            h = result.height()

            for x in range(step // 2, w, step):

                self.viewfinder._star(
                    painter,
                    x,
                    14,
                    size
                )

                self.viewfinder._star(
                    painter,
                    x,
                    h - 14,
                    size
                )

            for y in range(step, h - step, step):

                self.viewfinder._star(
                    painter,
                    14,
                    y,
                    size
                )

                self.viewfinder._star(
                    painter,
                    w - 14,
                    y,
                    size
                )


        elif frame_name == "Double Thin":

            w = result.width()
            h = result.height()

            for offset, alpha in [
                (4, 180),
                (10, 100)
            ]:

                pen = QPen(
                    QColor(
                        255,
                        255,
                        255,
                        alpha
                    ),
                    2
                )

                painter.setPen(pen)

                painter.drawRoundedRect(
                    offset,
                    offset,
                    w - offset * 2,
                    h - offset * 2,
                    12,
                    12
                )

        painter.end()

        return result