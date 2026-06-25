# ✦ BoothBloom — Korean Aesthetic Photobooth

Sistem photobooth modern dengan estetik Korea, dibangun menggunakan **PyQt6** + **OpenCV** 

---

## 🌸 Fitur

| Fitur | Keterangan |
|---|---|
| Live Preview | Pratinjau kamera real-time dengan filter langsung |
| 12 Filter Foto | Normal, Soft Bloom, Vintage, B&W Film, Lomo, Warm Honey, Cool Breeze, Glam, Pastel, Neon Noir, Fade, Sepia |
| 8 Background | Sakura Mist, Ocean Dream, Lavender Field, Peach Cream, Mint Dew, Noir Studio, Golden Hour, Cotton Candy |
| 7 Frame/Template | None, Simple White, Film Strip, Polaroid, Heart Deco, Star Deco, Double Thin |
| Countdown 3..2..1 | Overlay animasi di atas preview |
| Auto-Save | Foto tersimpan otomatis di folder `photos/` |
| Simpan Manual | Pilih lokasi dan format (PNG/JPG) |
| Cetak | Dialog print langsung dari Qt |
| Fullscreen Mode | Tombol atau F11 |
| Galeri | Buka folder hasil foto |

---


## ⚙️ Persiapan

### 1. Buat virtual enviroment terlebih dahulu
```bash
cd photobooth
python3 -m venv .env
source .env/bin/activate
```




### 2. Install Python packages

```bash
pip install -r requirements.txt
```

> **Catatan:** Jika muncul error `libxcb-cursor.so.0`, jalankan:
> ```bash
> sudo apt install libxcb-cursor0 (linux untuk windows menyesuaikan)
> ```

### 3. Jalankan aplikasi

```bash
python main.py
```

---

## ⌨️ Keyboard Shortcuts

| Shortcut | Aksi |
|---|---|
| `Space` | Ambil foto (mulai countdown) |
| `F11` | Toggle fullscreen |
| `Escape` | Keluar dari fullscreen |

---


## 🛠️ Troubleshooting

**Kamera tidak terdeteksi:**
```bash
ls /dev/video*          # cek device kamera
python -c "import cv2; print(cv2.VideoCapture(0).isOpened())"
```

**Error font / rendering:**
```bash
sudo apt install fonts-noto
```

**Error Qt platform plugin:**
```bash
sudo apt install libxcb-xinerama0 libxcb-cursor0
```
