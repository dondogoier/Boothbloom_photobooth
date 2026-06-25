"""
Photo filters using OpenCV and NumPy.
Korean aesthetic + classic photobooth filters.
"""

import cv2
import numpy as np


def apply_filter(frame: np.ndarray, filter_name: str) -> np.ndarray:
    filters = {
        "Normal":       _normal,
        "Soft Bloom":   _soft_bloom,
        "Vintage":      _vintage,
        "B&W Film":     _bw_film,
        "Lomo":         _lomo,
        "Warm Honey":   _warm_honey,
        "Cool Breeze":  _cool_breeze,
        "Glam":         _glam,
        "Pastel":       _pastel,
        "Neon Noir":    _neon_noir,
        "Fade":         _fade,
        "Sepia":        _sepia,
    }
    fn = filters.get(filter_name, _normal)
    return fn(frame.copy())


FILTER_NAMES = [
    "Normal", "Soft Bloom", "Vintage", "B&W Film",
    "Lomo", "Warm Honey", "Cool Breeze", "Glam",
    "Pastel", "Neon Noir", "Fade", "Sepia",
]

FILTER_ICONS = {
    "Normal":       "✦",
    "Soft Bloom":   "✿",
    "Vintage":      "◈",
    "B&W Film":     "◐",
    "Lomo":         "◉",
    "Warm Honey":   "◆",
    "Cool Breeze":  "◇",
    "Glam":         "★",
    "Pastel":       "♡",
    "Neon Noir":    "◼",
    "Fade":         "◻",
    "Sepia":        "⬡",
}


# ── Individual filter implementations ──────────────────────────────────────

def _normal(f): return f

def _soft_bloom(f):
    blur = cv2.GaussianBlur(f, (21, 21), 0)
    return cv2.addWeighted(f, 0.7, blur, 0.3, 20)

def _vintage(f):
    f = f.astype(np.float32)
    f[:, :, 0] *= 0.85   # B
    f[:, :, 2] *= 1.15   # R
    f = np.clip(f, 0, 255).astype(np.uint8)
    lut = np.array([int(i * 0.9 + 20) for i in range(256)], dtype=np.uint8)
    return cv2.LUT(f, lut)

def _bw_film(f):
    gray = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
    f = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    lut = np.array([int(i * 0.88 + 10) for i in range(256)], dtype=np.uint8)
    return cv2.LUT(f, lut)

def _lomo(f):
    rows, cols = f.shape[:2]
    # Build vignette mask with correct (rows, cols) shape
    ky = cv2.getGaussianKernel(rows, rows * 0.6)   # (rows, 1)
    kx = cv2.getGaussianKernel(cols, cols * 0.6)   # (cols, 1)
    kernel = ky * kx.T                              # (rows, cols)
    mask = kernel / kernel.max()                    # normalise to [0, 1]
    vign = np.zeros_like(f, dtype=np.float32)
    for i in range(3):
        vign[:, :, i] = f[:, :, i] * mask
    f = np.clip(vign, 0, 255).astype(np.uint8)
    f[:, :, 0] = np.clip(f[:, :, 0].astype(np.int32) - 15, 0, 255)
    f[:, :, 2] = np.clip(f[:, :, 2].astype(np.int32) + 20, 0, 255)
    return f

def _warm_honey(f):
    f = f.astype(np.float32)
    f[:, :, 2] = np.clip(f[:, :, 2] * 1.2 + 15, 0, 255)   # R
    f[:, :, 1] = np.clip(f[:, :, 1] * 1.05 + 5, 0, 255)   # G
    f[:, :, 0] = np.clip(f[:, :, 0] * 0.85, 0, 255)        # B
    return f.astype(np.uint8)

def _cool_breeze(f):
    f = f.astype(np.float32)
    f[:, :, 0] = np.clip(f[:, :, 0] * 1.2 + 10, 0, 255)   # B
    f[:, :, 1] = np.clip(f[:, :, 1] * 1.05, 0, 255)        # G
    f[:, :, 2] = np.clip(f[:, :, 2] * 0.9, 0, 255)         # R
    return f.astype(np.uint8)

def _glam(f):
    blur = cv2.GaussianBlur(f, (9, 9), 0)
    f = cv2.addWeighted(f, 1.3, blur, -0.3, 15)
    hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.3, 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

def _pastel(f):
    f = cv2.addWeighted(f, 0.75, np.full_like(f, 240), 0.25, 0)
    hsv = cv2.cvtColor(f, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 0.65, 0, 255)
    hsv[:, :, 2] = np.clip(hsv[:, :, 2] * 1.05 + 10, 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

def _neon_noir(f):
    gray = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
    f_dark = np.zeros_like(f)
    f_dark[:, :, 0] = np.clip(gray.astype(np.int32) // 2, 0, 255)  # dark blue
    edges = cv2.Canny(gray, 80, 160)
    f_dark[edges > 0] = [255, 80, 220]                               # neon pink
    return f_dark

def _fade(f):
    lut = np.array([int(i * 0.75 + 40) for i in range(256)], dtype=np.uint8)
    return cv2.LUT(f, lut)

def _sepia(f):
    k = np.array([[0.272, 0.534, 0.131],
                  [0.349, 0.686, 0.168],
                  [0.393, 0.769, 0.189]])
    sep = cv2.transform(f, k)
    return np.clip(sep, 0, 255).astype(np.uint8)
