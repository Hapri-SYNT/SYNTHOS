"""
╔══════════════════════════════════════════════════════════════╗
║              🧠  VISION.PY — FINAL FUSION  🧠               ║
║         Python Visual Intelligence — Pure CV               ║
║     "Melihat, Memahami, dan MEMBACA Gambar" 👁️✨            ║
║                                                            ║
║  Kemampuan:                                                ║
║  • Analisis konteks & kategori gambar                      ║
║  • Komposisi fotografi (rule of thirds, simetri, dll)     ║
║  • Atmosfer & tone emosional                              ║
║  • Palet warna + harmoni warna                            ║
║  • Tekstur & pola (FFT-based)                             ║
║  • Depth of field & isolasi subjek                        ║
║  • Deteksi bentuk geometris                               ║
║  • Deteksi CAPTCHA + OCR Text Reader (Tesseract)          ║
║  • Visual storytelling                                    ║
║                                                            ║
║  Usage: python vision.py <path_gambar>                    ║
╚══════════════════════════════════════════════════════════════╝
"""

import sys
import inspect
import os
import numpy as np
from PIL import Image, ImageStat, ImageFilter, ImageEnhance
import cv2
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any
import math
from enum import Enum

# ═══════════════════════════════════════════════════════════════
# OPTIONAL IMPORTS (graceful degradation)
# ═══════════════════════════════════════════════════════════════

try:
    from sklearn.cluster import KMeans
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False


# ═══════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════

class ImageCategory(Enum):
    PORTRAIT = "Potret Wajah"
    LANDSCAPE = "Pemandangan"
    URBAN = "Urban/Arsitektur"
    MACRO = "Makro/Close-up"
    DOCUMENT = "Dokumen/Teks"
    ABSTRACT = "Abstrak/Pattern"
    FOOD = "Makanan"
    DARK_SCENE = "Low-light/Night"
    SILHOUETTE = "Siluet"
    CAPTCHA = "CAPTCHA/Verifikasi"
    UNKNOWN = "Tidak Terklasifikasi"

@dataclass
class CompositionAnalysis:
    rule_of_thirds_score: float
    symmetry_score: float
    leading_lines_score: float
    golden_ratio_score: float
    main_subject_position: str
    horizon_position: Optional[str]
    overall_score: float

@dataclass
class VisualStory:
    primary_subject: str
    secondary_elements: List[str]
    atmosphere: str
    suggested_use: List[str]
    emotional_tone: str

@dataclass
class OCRResult:
    best_text: str
    confidence: float
    source: str
    original_text: str
    preprocessed_text: str
    error: Optional[str] = None
    thresh_image: Optional[np.ndarray] = None
    cleaned_image: Optional[np.ndarray] = None

@dataclass
class CaptchaDetection:
    is_captcha: bool
    captcha_type: str
    score: float
    features: Dict[str, Any]


# ═══════════════════════════════════════════════════════════════
# UTILITY CLASSES & FUNCTIONS
# ═══════════════════════════════════════════════════════════════

class Colors:
    """Terminal ANSI color codes for beautiful output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ORANGE = '\033[38;5;208m'
    PINK = '\033[38;5;205m'
    PURPLE = '\033[38;5;135m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    UNDERLINE = '\033[4m'
    RESET = '\033[0m'


def banner():
    """Tampilkan banner pembuka."""
    print(f"""
{Colors.CYAN}{Colors.BOLD}
  ╔══════════════════════════════════════════════╗
  ║         🧠  VISION.PY — FINAL  🧠            ║
  ║   Python Visual Intelligence — Pure CV      ║
  ║   "Melihat, Memahami, dan MEMBACA" 👁️📖     ║
  ╚══════════════════════════════════════════════╝
{Colors.RESET}""")


def header(title: str, emoji: str = ""):
    """Tampilkan header seksi."""
    print(f"\n{Colors.YELLOW}{Colors.BOLD}{'─'*65}")
    print(f"  {emoji} {title}")
    print(f"{'─'*65}{Colors.RESET}")


def info(label: str, value, color: str = ""):
    """Tampilkan informasi berlabel."""
    print(f"  {Colors.DIM}{label:<32}{Colors.RESET} {color}{value}{Colors.RESET}")


def sub_info(label: str, value):
    """Tampilkan sub-informasi."""
    print(f"    {Colors.DIM}└─ {label:<28}{Colors.RESET} {value}")


def color_swatch(r: int, g: int, b: int, size: int = 3) -> str:
    """Return ANSI colored block."""
    block = "█" * size
    return f"\033[38;2;{r};{g};{b}m{block}\033[0m"


def rgb_to_hsv(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """Convert RGB (0-255) to HSV (H:0-360, S:0-100, V:0-100)."""
    r_norm, g_norm, b_norm = r / 255.0, g / 255.0, b / 255.0
    mx = max(r_norm, g_norm, b_norm)
    mn = min(r_norm, g_norm, b_norm)
    df = mx - mn

    if mx == mn:
        h = 0
    elif mx == r_norm:
        h = (60 * ((g_norm - b_norm) / df) + 360) % 360
    elif mx == g_norm:
        h = (60 * ((b_norm - r_norm) / df) + 120) % 360
    else:
        h = (60 * ((r_norm - g_norm) / df) + 240) % 360

    s = 0 if mx == 0 else (df / mx) * 100
    v = mx * 100
    return h, s, v


def rgb_to_name(r: int, g: int, b: int) -> str:
    """
    Advanced color naming dengan 30+ varian warna.
    Mencakup achromatic, chromatic, dan nuansa spesifik.
    """
    h, s, v = rgb_to_hsv(r, g, b)

    # ── Achromatic (grayscale) ──
    if v < 20:
        return "Hitam Pekat"
    if v < 40:
        return "Hitam Keabuan"
    if s < 15:
        if v > 230:
            return "Putih Bersih"
        if v > 200:
            return "Putih Kecoklatan"
        if v > 160:
            return "Abu Terang"
        if v > 100:
            return "Abu Sedang"
        return "Abu Gelap"

    # ── Chromatic dengan hue ──
    color_map = [
        (10,   lambda: "Merah Darah" if v < 100 else "Merah Cerah"),
        (20,   lambda: "Merah Oranye" if v > 150 else "Merah Bata"),
        (35,   lambda: "Oranye Cerah" if v > 150 else "Oranye Terbakar"),
        (50,   lambda: "Kuning Oranye" if v > 150 else "Coklat Keemasan"),
        (65,   lambda: "Kuning Cerah" if v > 200 else "Kuning Mustard"),
        (85,   lambda: "Hijau Kuning" if v > 150 else "Hijau Zaitun"),
        (150,  lambda: "Hijau Segar" if v > 120 else "Hijau Gelap"),
        (180,  lambda: "Cyan Terang" if v > 150 else "Teal"),
        (220,  lambda: "Biru Langit" if v > 180 else "Biru Laut"),
        (260,  lambda: "Biru Ungu" if v > 100 else "Navy"),
        (290,  lambda: "Ungu Cerah" if v > 120 else "Ungu Tua"),
        (330,  lambda: "Magenta" if v > 100 else "Plum"),
    ]

    for max_hue, name_fn in color_map:
        if h < max_hue:
            return name_fn()

    return "Merah Muda" if v > 180 else "Rose"


# ═══════════════════════════════════════════════════════════════
# 1. INFORMASI DASAR (ENHANCED)
# ═══════════════════════════════════════════════════════════════

def analyze_basic(img_pil: Image.Image, path: str) -> Tuple[int, int]:
    """
    Analisis informasi dasar gambar:
    - Resolusi, orientasi, mode warna
    - Ukuran file
    - Estimasi kualitas
    """
    header("INFORMASI DASAR", "📋")

    w, h = img_pil.size
    mode = img_pil.mode
    size_kb = os.path.getsize(path) / 1024
    size_mb = size_kb / 1024
    channels = len(img_pil.getbands())
    aspect = round(w / h, 3)
    megapixels = w * h / 1_000_000

    # ── Orientasi ──
    if w > h * 1.2:
        orientation = "🖼️  Landscape"
    elif h > w * 1.2:
        orientation = "📱 Portrait"
    else:
        orientation = "⬜ Square"

    # ── Format file ──
    ext = os.path.splitext(path)[1].upper().replace(".", "")
    format_map = {
        "JPG": "JPEG (lossy compressed)",
        "JPEG": "JPEG (lossy compressed)",
        "PNG": "PNG (lossless compressed)",
        "WEBP": "WebP (modern compressed)",
        "BMP": "BMP (uncompressed)",
        "GIF": "GIF (palette-based)",
        "TIFF": "TIFF (high quality)",
    }
    file_format = format_map.get(ext, f"Format {ext}")

    info("File", os.path.basename(path))
    info("Format", file_format)
    info("Resolusi", f"{w:,} × {h:,} piksel ({megapixels:.1f} MP)")
    info("Orientasi", f"{orientation} (aspek rasio {aspect}:1)")
    info("Mode Warna", f"{mode} ({channels} channel{'s' if channels > 1 else ''})")
    info("Ukuran File", f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_mb:.2f} MB")

    # ── Estimasi kualitas ──
    if megapixels < 1:
        quality = f"{Colors.ORANGE}Resolusi rendah — cocok untuk web/thumbnail{Colors.RESET}"
    elif megapixels < 4:
        quality = f"{Colors.YELLOW}Resolusi standar — cukup untuk sosial media{Colors.RESET}"
    elif megapixels < 12:
        quality = f"{Colors.CYAN}Resolusi baik — cukup untuk cetak ukuran sedang{Colors.RESET}"
    elif megapixels < 24:
        quality = f"{Colors.GREEN}Resolusi tinggi — bisa cetak ukuran besar{Colors.RESET}"
    else:
        quality = f"{Colors.GREEN}{Colors.BOLD}Resolusi sangat tinggi — kualitas profesional{Colors.RESET}"

    info("Estimasi Kualitas", quality)

    return w, h


# ═══════════════════════════════════════════════════════════════
# 2. ANALISIS KONTEKS & KATEGORI GAMBAR
# ═══════════════════════════════════════════════════════════════

def analyze_context(img_pil: Image.Image, img_cv: np.ndarray) -> Dict[str, Any]:
    """
    Menganalisis KONTEKS gambar:
    - Kategori (portrait, landscape, urban, document, dll)
    - Skin tone detection
    - Sky detection
    - Nature/vegetation detection
    - Time of day estimation
    """
    header("ANALISIS KONTEKS & KATEGORI", "🔍")

    w, h = img_pil.size
    total_pixels = w * h
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)

    # ── Edge density (foto vs grafis) ──
    edges = cv2.Canny(gray, 50, 150)
    edge_density = np.sum(edges > 0) / total_pixels

    # ── Area solid (grafis/dokumen) ──
    local_var = cv2.blur(gray.astype(np.float32)**2, (15, 15)) - \
                cv2.blur(gray.astype(np.float32), (15, 15))**2
    solid_ratio = np.sum(np.sqrt(np.maximum(local_var, 0)) < 8) / total_pixels

    # ── Distribusi spasial ──
    grid_means = []
    for i in range(3):
        for j in range(3):
            region = gray[i*h//3:(i+1)*h//3, j*w//3:(j+1)*w//3]
            grid_means.append(np.mean(region))

    center_mean = grid_means[4]
    edge_means_list = [grid_means[i] for i in [0, 1, 2, 3, 5, 6, 7, 8]]
    center_vs_edge = center_mean / (np.mean(edge_means_list) + 1)

    # ── Mean color ──
    small = img_pil.resize((50, 50)).convert("RGB")
    mean_color = np.mean(np.array(small).reshape(-1, 3), axis=0)

    # ── Skin tone detection ──
    lower_skin = np.array([0, 20, 70], dtype=np.uint8)
    upper_skin = np.array([20, 255, 255], dtype=np.uint8)
    lower_skin2 = np.array([170, 20, 70], dtype=np.uint8)
    upper_skin2 = np.array([180, 255, 255], dtype=np.uint8)

    skin_mask1 = cv2.inRange(hsv, lower_skin, upper_skin)
    skin_mask2 = cv2.inRange(hsv, lower_skin2, upper_skin2)
    skin_mask = cv2.bitwise_or(skin_mask1, skin_mask2)
    skin_ratio = np.sum(skin_mask > 0) / total_pixels

    # ── Sky detection (biru di 1/3 atas) ──
    top_region = np.array(img_pil.crop((0, 0, w, h//3)).resize((30, 10)).convert("RGB"))
    top_colors = top_region.reshape(-1, 3)
    blue_mask = (top_colors[:, 2] > top_colors[:, 0]) & \
                (top_colors[:, 2] > top_colors[:, 1] * 0.9) & \
                (top_colors[:, 2] > 100)
    sky_ratio = np.sum(blue_mask) / len(top_colors)

    # ── Green/nature detection ──
    hsv_flat = hsv.reshape(-1, 3)
    green_mask = (hsv_flat[:, 0] > 35) & (hsv_flat[:, 0] < 85) & (hsv_flat[:, 1] > 40)
    green_ratio = np.sum(green_mask) / len(hsv_flat)

    # ── KLASIFIKASI ──
    categories = []

    # Face detection untuk portrait
    face_cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    if os.path.exists(face_cascade_path):
        face_cascade = cv2.CascadeClassifier(face_cascade_path)
        faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(40, 40))

        if len(faces) > 0 and skin_ratio > 0.05:
            face_areas = [fw * fh for (_, _, fw, fh) in faces]
            max_face_ratio = max(face_areas) / total_pixels
            if max_face_ratio > 0.05:
                categories.append((ImageCategory.PORTRAIT, 0.9))
            elif len(faces) > 3:
                categories.append((ImageCategory.PORTRAIT, 0.7))
            else:
                categories.append((ImageCategory.PORTRAIT, 0.5))
    elif skin_ratio > 0.15:
        categories.append((ImageCategory.PORTRAIT, 0.5))

    # Landscape
    if green_ratio > 0.25 or sky_ratio > 0.25:
        landscape_conf = 0.5 + (green_ratio + sky_ratio) * 0.5
        categories.append((ImageCategory.LANDSCAPE, min(landscape_conf, 0.95)))

    # Document/teks
    if solid_ratio > 0.35 and edge_density < 0.08:
        categories.append((ImageCategory.DOCUMENT, 0.75))
    elif solid_ratio > 0.25:
        categories.append((ImageCategory.DOCUMENT, 0.5))

    # Abstract
    if solid_ratio > 0.5 and edge_density < 0.05:
        categories.append((ImageCategory.ABSTRACT, 0.7))

    # Urban (banyak edge, sedikit vegetasi)
    if edge_density > 0.1 and green_ratio < 0.2:
        categories.append((ImageCategory.URBAN, 0.5))

    # Sort dan pilih top
    categories.sort(key=lambda x: x[1], reverse=True)
    top_category, top_conf = categories[0] if categories else (ImageCategory.UNKNOWN, 0.0)

    info("Kategori Utama", f"{Colors.BOLD}{top_category.value}{Colors.RESET} (confidence: {top_conf:.0%})")

    if len(categories) > 1:
        for cat, conf in categories[1:3]:
            sub_info("Alternatif", f"{cat.value} ({conf:.0%})")

    # ── Scene type & time of day ──
    mean_brightness = np.mean(gray)

    if mean_brightness < 50:
        scene_type = "🌑 Low-light / Malam hari"
        time_guess = "Malam"
    elif mean_brightness < 90:
        scene_type = "🌒 Indoor / Remang-remang"
        time_guess = "Sore/Malam"
    elif mean_brightness < 160:
        scene_type = "🌤️  Indoor terang / Outdoor berawan"
        time_guess = "Pagi/Sore"
    else:
        scene_type = "☀️  Outdoor terang / Siang hari"
        time_guess = "Siang"

    # Refine dengan sky detection
    if sky_ratio > 0.4 and mean_brightness > 150:
        time_guess = "Siang hari cerah"
    elif mean_brightness > 100 and mean_color[0] > mean_color[2] * 1.2:
        time_guess = "Golden hour / Senja"

    info("Pencahayaan", scene_type)
    info("Estimasi Waktu", time_guess)

    return {
        'category': top_category,
        'category_confidence': top_conf,
        'skin_ratio': skin_ratio,
        'sky_ratio': sky_ratio,
        'green_ratio': green_ratio,
        'center_vs_edge': center_vs_edge,
        'edge_density': edge_density,
        'solid_ratio': solid_ratio,
        'mean_brightness': mean_brightness
    }


# ═══════════════════════════════════════════════════════════════
# 3. ANALISIS KOMPOSISI FOTOGRAFI
# ═══════════════════════════════════════════════════════════════

def analyze_composition(img_cv: np.ndarray) -> CompositionAnalysis:
    """
    Analisis komposisi fotografis:
    - Rule of thirds
    - Simetri kiri-kanan
    - Leading lines (garis konvergen)
    - Golden ratio points
    - Posisi subjek utama (saliency map)
    - Garis horizon
    """
    header("ANALISIS KOMPOSISI", "📐")

    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    # ── Rule of Thirds ──
    thirds_x = [w//3, 2*w//3]
    thirds_y = [h//3, 2*h//3]
    intersections = [(x, y) for x in thirds_x for y in thirds_y]

    corners = cv2.goodFeaturesToTrack(gray, maxCorners=50, qualityLevel=0.01, minDistance=30)
    rot_score = 0

    if corners is not None:
        for corner in corners:
            cx, cy = corner.ravel()
            for ix, iy in intersections:
                dist = np.sqrt((cx - ix)**2 + (cy - iy)**2)
                if dist < min(w, h) * 0.1:
                    rot_score += 1

    rot_score = min(rot_score / 10, 1.0)

    # ── Simetri ──
    mid = w // 2
    left = gray[:, :mid]
    right = cv2.flip(gray[:, mid:], 1)

    if left.shape[1] != right.shape[1]:
        min_w_sym = min(left.shape[1], right.shape[1])
        left, right = left[:, :min_w_sym], right[:, :min_w_sym]

    symmetry_score = 1.0 - np.mean(np.abs(left.astype(float) - right.astype(float))) / 255.0

    # ── Leading Lines ──
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100,
                            minLineLength=min(w, h)//4, maxLineGap=20)

    leading_lines_score = 0
    if lines is not None and len(lines) > 0:
        center_x, center_y = w//2, h//2
        convergent_lines = 0

        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = abs(math.atan2(y2 - y1, x2 - x1) * 180 / math.pi)

            if 15 < angle < 75 or 105 < angle < 165:
                mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
                if abs(mid_x - center_x) < w * 0.3 and abs(mid_y - center_y) < h * 0.3:
                    convergent_lines += 1

        leading_lines_score = min(convergent_lines / 5, 1.0)

    # ── Golden Ratio ──
    golden_points = [
        (int(w * 0.382), int(h * 0.382)),
        (int(w * 0.618), int(h * 0.382)),
        (int(w * 0.382), int(h * 0.618)),
        (int(w * 0.618), int(h * 0.618)),
    ]
    golden_score = 0

    if corners is not None:
        for corner in corners:
            cx, cy = corner.ravel()
            for gx, gy in golden_points:
                dist = np.sqrt((cx - gx)**2 + (cy - gy)**2)
                if dist < min(w, h) * 0.08:
                    golden_score += 1

    golden_score = min(golden_score / 8, 1.0)

    # ── Main Subject Position (Saliency) ──
    try:
        saliency = cv2.saliency.StaticSaliencyFineGrained_create()
        success, saliency_map = saliency.computeSaliency(img_cv)

        if success:
            thresh_sal = np.percentile(saliency_map, 85)
            salient_mask = saliency_map > thresh_sal
            moments = cv2.moments(salient_mask.astype(np.uint8))

            if moments['m00'] > 0:
                cx_s = int(moments['m10'] / moments['m00'])
                cy_s = int(moments['m01'] / moments['m00'])

                vpos = "Atas" if cy_s < h/3 else ("Bawah" if cy_s > 2*h/3 else "Tengah")
                hpos = "Kiri" if cx_s < w/3 else ("Kanan" if cx_s > 2*w/3 else "Tengah")
                subject_pos = f"{vpos}-{hpos}"
            else:
                subject_pos = "Tidak terdeteksi"
        else:
            subject_pos = "N/A"
    except:
        subject_pos = "Tidak tersedia"

    # ── Horizon Detection ──
    horizon_pos = None
    if lines is not None:
        horizontal_lines = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = abs(math.atan2(y2 - y1, x2 - x1) * 180 / math.pi)
            if angle < 5 or angle > 175:
                length = abs(x2 - x1)
                if length > w * 0.5:
                    horizontal_lines.append((y1 + y2) / 2)

        if horizontal_lines:
            avg_y = np.mean(horizontal_lines)
            if avg_y < h / 3:
                horizon_pos = "Atas (1/3)"
            elif avg_y > 2 * h / 3:
                horizon_pos = "Bawah (2/3)"
            else:
                horizon_pos = "Tengah"

    # ── TAMPILKAN ──
    def star_bar(score):
        filled = int(score * 5)
        return f"{'★'*filled}{'☆'*(5-filled)} ({score:.0%})"

    info("Rule of Thirds", star_bar(rot_score))
    info("Simetri", star_bar(symmetry_score))
    info("Leading Lines", star_bar(leading_lines_score))
    info("Golden Ratio", star_bar(golden_score))
    info("Subjek Utama", subject_pos)
    if horizon_pos:
        info("Garis Horizon", horizon_pos)

    # ── Overall ──
    overall = (rot_score * 0.3 + symmetry_score * 0.2 +
               leading_lines_score * 0.3 + golden_score * 0.2)

    if overall > 0.7:
        quality = f"{Colors.GREEN}★★★★★ Excellent{Colors.RESET}"
    elif overall > 0.5:
        quality = f"{Colors.CYAN}★★★★  Baik{Colors.RESET}"
    elif overall > 0.3:
        quality = f"{Colors.YELLOW}★★★   Cukup{Colors.RESET}"
    else:
        quality = f"{Colors.ORANGE}★★    Perlu Improvement{Colors.RESET}"

    info("Skor Komposisi", quality)

    return CompositionAnalysis(
        rule_of_thirds_score=rot_score,
        symmetry_score=symmetry_score,
        leading_lines_score=leading_lines_score,
        golden_ratio_score=golden_score,
        main_subject_position=subject_pos,
        horizon_position=horizon_pos,
        overall_score=overall
    )


# ═══════════════════════════════════════════════════════════════
# 4. ANALISIS ATMOSFER & EMOSI
# ═══════════════════════════════════════════════════════════════

def analyze_atmosphere(img_pil: Image.Image, img_cv: np.ndarray,
                       context: Dict[str, Any]) -> Dict[str, Any]:
    """
    "Merasakan" mood/emosi gambar:
    - Temperatur warna (warm/cool)
    - Level saturasi
    - Distribusi tonal (low-key/high-key)
    - Tone emosional
    """
    header("ANALISIS ATMOSFER & EMOSI", "🎭")

    img_array = np.array(img_pil.convert("RGB"))
    hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

    # ── Color Temperature ──
    mean_rgb = np.mean(img_array.reshape(-1, 3), axis=0)
    r, g, b = mean_rgb
    temp_score = (r - b) / 255.0  # + = warm, - = cool

    if temp_score > 0.1:
        temperature = "🔥 Hangat"
    elif temp_score < -0.1:
        temperature = "🧊 Dingin"
    else:
        temperature = "⚖️  Netral"

    info("Temperatur Warna", temperature)

    # ── Saturasi ──
    mean_saturation = np.mean(hsv[:, :, 1])

    if mean_saturation < 30:
        sat_level = "🖤 Desaturated (muted/pucat)"
    elif mean_saturation < 60:
        sat_level = "🎨 Natural"
    elif mean_saturation < 100:
        sat_level = "🌈 Cukup Saturasi"
    else:
        sat_level = "💥 Sangat Saturat (vibrant)"

    info("Level Saturasi", f"{mean_saturation:.0f}% — {sat_level}")

    # ── Distribusi Tonal ──
    hist = cv2.calcHist([gray], [0], None, [10], [0, 256]).flatten()
    hist = hist / hist.sum()

    dark_ratio = np.sum(hist[:3])
    mid_ratio = np.sum(hist[3:7])
    bright_ratio = np.sum(hist[7:])

    if dark_ratio > 0.6:
        tonal = "Low-key (didominasi gelap)"
    elif bright_ratio > 0.6:
        tonal = "High-key (didominasi terang)"
    else:
        tonal = "Balanced tonal range"

    info("Distribusi Tonal", tonal)
    sub_info("Bayangan (0-30%)", f"{dark_ratio:.0%}")
    sub_info("Midtone (30-70%)", f"{mid_ratio:.0%}")
    sub_info("Highlight (70-100%)", f"{bright_ratio:.0%}")

    # ── Emotional Tone ──
    emotions = []

    if temp_score > 0.05 and bright_ratio > 0.3 and mean_saturation > 40:
        emotions.append(("Ceria/Energetik", 0.7))
    if temp_score > 0.05 and dark_ratio > 0.4:
        emotions.append(("Intim/Hangat", 0.6))
    if temp_score < -0.05 and bright_ratio > 0.3:
        emotions.append(("Segar/Tenang", 0.6))
    if temp_score < -0.05 and dark_ratio > 0.4:
        emotions.append(("Melankolis/Misterius", 0.7))
    if np.std(gray) > 70:
        emotions.append(("Dramatis", 0.5))
    if mean_saturation < 30 and dark_ratio > 0.5:
        emotions.append(("Muram/Suram", 0.6))
    if mean_saturation > 70 and bright_ratio > 0.4:
        emotions.append(("Gembira/Riang", 0.7))

    if not emotions:
        emotions.append(("Netral/Biasa", 0.3))

    emotions.sort(key=lambda x: x[1], reverse=True)

    print(f"\n  {Colors.PINK}🎭 Tone Emosional:{Colors.RESET}")
    for emotion, conf in emotions[:3]:
        bar = "█" * int(conf * 20)
        print(f"    {emotion:<25} {Colors.DIM}{bar}{Colors.RESET} ({conf:.0%})")

    return {
        'temperature': temp_score,
        'saturation': mean_saturation,
        'dark_ratio': dark_ratio,
        'bright_ratio': bright_ratio,
        'primary_emotion': emotions[0][0] if emotions else "Netral"
    }


# ═══════════════════════════════════════════════════════════════
# 5. ANALISIS TEKSTUR & PATTERN
# ═══════════════════════════════════════════════════════════════

def analyze_texture(img_cv: np.ndarray) -> Dict[str, Any]:
    """
    Analisis tekstur gambar:
    - Local variance (kekasaran)
    - FFT untuk periodic patterns
    """
    header("ANALISIS TEKSTUR", "🔬")

    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    # ── Local texture ──
    local_std = cv2.blur(gray.astype(np.float32)**2, (3, 3)) - \
                cv2.blur(gray.astype(np.float32), (3, 3))**2
    local_std = np.sqrt(np.maximum(local_std, 0))

    mean_texture = np.mean(local_std)
    texture_std = np.std(local_std)

    if mean_texture < 10:
        texture_type = "✨ Sangat Halus (seperti kulit/sutra)"
    elif mean_texture < 25:
        texture_type = "🧴 Halus (sedikit tekstur)"
    elif mean_texture < 45:
        texture_type = "🪨 Sedang (tekstur terlihat)"
    elif mean_texture < 70:
        texture_type = "🪵 Kasar (tekstur jelas)"
    else:
        texture_type = "🌋 Sangat Kasar (banyak detail)"

    info("Kekasaran Tekstur", f"{mean_texture:.1f} — {texture_type}")
    info("Variasi Tekstur", f"{'Seragam' if texture_std < 20 else 'Bervariasi'} (σ={texture_std:.1f})")

    # ── FFT Pattern Detection ──
    f_transform = np.fft.fft2(gray)
    f_shift = np.fft.fftshift(f_transform)
    magnitude_spectrum = np.log(np.abs(f_shift) + 1)

    center_h, center_w = h // 2, w // 2
    mask = np.ones_like(magnitude_spectrum, dtype=bool)
    mask[center_h-10:center_h+10, center_w-10:center_w+10] = False

    threshold_val = np.mean(magnitude_spectrum[mask]) + 2 * np.std(magnitude_spectrum[mask])
    peaks = magnitude_spectrum > threshold_val
    num_peaks = np.sum(peaks & mask)

    if num_peaks > 20:
        pattern_type = "🔄 Sangat Berpola (repetitive patterns)"
    elif num_peaks > 8:
        pattern_type = "🔁 Ada Pola Berulang"
    elif num_peaks > 3:
        pattern_type = "〰️ Sedikit Pola"
    else:
        pattern_type = "🌊 Organik/Tidak Berpola"

    info("Deteksi Pola", pattern_type)

    return {
        'texture_mean': mean_texture,
        'texture_std': texture_std,
        'num_patterns': num_peaks
    }


# ═══════════════════════════════════════════════════════════════
# 6. ANALISIS DEPTH & DIMENSI
# ═══════════════════════════════════════════════════════════════

def analyze_depth(img_cv: np.ndarray) -> str:
    """
    Estimasi kedalaman gambar:
    - Depth of field (shallow/deep)
    - Isolasi subjek (foreground vs background)
    """
    header("ANALISIS KEDALAMAN", "📏")

    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    center_y, center_x = h // 2, w // 2

    # ── Region-based sharpness ──
    regions = {'center': np.array([]), 'mid': [], 'edge': []}

    for y in range(0, h, h // 8):
        for x in range(0, w, w // 8):
            region = gray[y:y+h//8, x:x+w//8]
            dist = np.sqrt((x + w//16 - center_x)**2 + (y + h//16 - center_y)**2)
            max_dist = np.sqrt(center_x**2 + center_y**2)
            normalized_dist = dist / max_dist

            if normalized_dist < 0.3:
                regions['center'] = region if regions['center'].size == 0 else region
            elif normalized_dist < 0.6:
                regions['mid'].append(region)
            else:
                regions['edge'].append(region)

    def region_sharpness(r):
        if isinstance(r, list):
            if not r:
                return 0
            return np.mean([cv2.Laplacian(reg.astype(np.uint8), cv2.CV_64F).var() for reg in r])
        if r.size == 0:
            return 0
        return cv2.Laplacian(r.astype(np.uint8), cv2.CV_64F).var()

    center_sharp = region_sharpness(regions['center'])
    mid_sharp = region_sharpness(regions['mid'])
    edge_sharp = region_sharpness(regions['edge'])
    total_sharp = center_sharp + mid_sharp + edge_sharp + 1

    if center_sharp > max(mid_sharp, edge_sharp) * 1.5:
        dof = "Shallow (fokus pada subjek, background blur)"
    elif abs(center_sharp - edge_sharp) < total_sharp * 0.15:
        dof = "Deep (semua area fokus)"
    else:
        dof = "Moderate depth of field"

    info("Depth of Field", dof)
    sub_info("Ketajaman Center", f"{center_sharp:.0f}")
    sub_info("Ketajaman Edge", f"{edge_sharp:.0f}")

    # ── Subject isolation ──
    edges = cv2.Canny(gray, 30, 100)
    edge_center = np.sum(edges[center_y-h//4:center_y+h//4,
                               center_x-w//4:center_x+w//4])
    edge_total = np.sum(edges) + 1
    edge_center_ratio = edge_center / edge_total

    if edge_center_ratio > 0.4:
        isolation = "Subjek terisolasi dengan baik"
    elif edge_center_ratio > 0.2:
        isolation = "Subjek cukup terpisah dari background"
    else:
        isolation = "Subjek menyatu dengan background"

    info("Isolasi Subjek", isolation)

    return dof


# ═══════════════════════════════════════════════════════════════
# 7. DETEKSI BENTUK & OBJEK
# ═══════════════════════════════════════════════════════════════

def detect_shapes(img_cv: np.ndarray) -> Dict[str, int]:
    """
    Deteksi bentuk geometris sederhana:
    - Lingkaran (Hough Circles)
    - Persegi & segitiga (contour approximation)
    - Garis dominan (Hough Lines)
    """
    header("DETEKSI BENTUK & OBJEK", "🔺")

    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    min_dim = min(h, w)

    # ── Lingkaran ──
    blurred = cv2.medianBlur(gray, 5)
    circles = cv2.HoughCircles(blurred, cv2.HOUGH_GRADIENT, dp=1.2,
                               minDist=min_dim//8, param1=50, param2=30,
                               minRadius=min_dim//50, maxRadius=min_dim//4)
    circle_count = len(circles[0]) if circles is not None else 0

    # ── Persegi & Segitiga ──
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    rectangles, triangles = 0, 0
    significant = [c for c in contours if cv2.contourArea(c) > min_dim * 2]

    for contour in significant:
        peri = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * peri, True)

        if len(approx) == 3:
            triangles += 1
        elif len(approx) == 4:
            x_r, y_r, w_r, h_r = cv2.boundingRect(approx)
            area = cv2.contourArea(contour)
            rect_area = w_r * h_r
            if rect_area > 0 and area / rect_area > 0.8:
                rectangles += 1

    # ── Garis ──
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100,
                            minLineLength=min_dim//4, maxLineGap=20)
    line_count = len(lines) if lines is not None else 0

    # ── Display ──
    if circle_count > 0:
        info("● Lingkaran", f"{circle_count} terdeteksi")
    if rectangles > 0:
        info("■ Persegi/Kotak", f"{rectangles} terdeteksi")
    if triangles > 0:
        info("▲ Segitiga", f"{triangles} terdeteksi")
    if line_count > 0:
        info("─ Garis Dominan", f"{line_count} terdeteksi")

    if circle_count == 0 and rectangles == 0 and triangles == 0 and line_count == 0:
        info("Bentuk Geometris", f"{Colors.DIM}Tidak ada bentuk dominan{Colors.RESET}")

    return {
        'circles': circle_count,
        'rectangles': rectangles,
        'triangles': triangles,
        'lines': line_count
    }


# ═══════════════════════════════════════════════════════════════
# 8. PALET WARNA & HARMONI (ENHANCED)
# ═══════════════════════════════════════════════════════════════

def analyze_colors_enhanced(img_pil: Image.Image, n: int = 5) -> None:
    """
    Analisis warna dominan + harmoni warna:
    - KMeans clustering (atau quantization fallback)
    - Color naming dengan 30+ varian
    - Harmony detection (complementary, analog, monochromatic)
    - Contrast check
    """
    header("PALET WARNA & HARMONI", "🎨")

    small = img_pil.resize((150, 150)).convert("RGB")
    pixels = np.array(small).reshape(-1, 3)

    # Clustering warna dominan
    if HAS_SKLEARN:
        km = KMeans(n_clusters=n, n_init=10, random_state=42)
        km.fit(pixels)
        centers = km.cluster_centers_.astype(int)
        labels = km.labels_
        counts = Counter(labels)
        total = len(pixels)
        sorted_colors = sorted(zip(counts.values(), centers, range(n)), reverse=True)
    else:
        quantized = img_pil.quantize(colors=n)
        palette = np.array(quantized.getpalette()[:n*3]).reshape(-1, 3)
        sorted_colors = [(1, c, i) for i, c in enumerate(palette)]
        total = 1

    print()
    dominant_hues = []

    for rank, (count, color, _) in enumerate(sorted_colors[:n]):
        r, g, b = int(color[0]), int(color[1]), int(color[2])
        pct = count / total * 100
        name = rgb_to_name(r, g, b)
        h, s, v = rgb_to_hsv(r, g, b)
        dominant_hues.append(h)

        bar_len = int(pct / 3)
        bar = color_swatch(r, g, b, max(bar_len, 1)) + " " * (35 - bar_len)

        print(f"  \033[90m#{rank+1}\033[0m {color_swatch(r,g,b,4)} "
              f"RGB({r:3d},{g:3d},{b:3d})  {bar} {pct:5.1f}%  {name}")
        sub_info("HSV", f"H:{h:.0f}° S:{s:.0f}% V:{v:.0f}%")

    # ── Color Harmony ──
    print(f"\n  {Colors.PINK}🌈 Analisis Harmoni Warna:{Colors.RESET}")

    if len(dominant_hues) >= 2:
        hues = sorted(dominant_hues)
        diffs = [(abs(h1 - h2) % 360, h1, h2)
                 for i, h1 in enumerate(hues) for h2 in hues[i+1:]]
        diffs.sort(key=lambda x: abs(x[0] - 180))

        closest_to_comp = diffs[0][0] if diffs else 0

        if 150 < closest_to_comp < 210:
            print(f"    🟣🟡 Komplementer — kontras kuat dan dinamis")
        elif closest_to_comp < 30:
            print(f"    🔵🔷 Monokromatik — harmoni lembut dan kohesif")
        elif 30 <= closest_to_comp <= 90:
            print(f"    🟢🟨 Analog — harmoni natural dan tenang")
        elif 90 < closest_to_comp <= 150:
            print(f"    🔴🔵 Split-komplementer — seimbang dengan aksen")
        else:
            print(f"    🎯 Palet bebas — kombinasi warna unik")

    # ── Contrast ──
    if len(sorted_colors) >= 2:
        v_vals = [rgb_to_hsv(*c[1])[2] for c in sorted_colors[:n]]
        if max(v_vals) - min(v_vals) > 70:
            print(f"    ⚫⚪ High contrast — elemen terang dan gelap terpisah")
        else:
            print(f"    ◽◾ Low contrast — tonalitas lembut")


# ═══════════════════════════════════════════════════════════════
# 9. OCR & CAPTCHA DETECTION (FUSION BARU!)
# ═══════════════════════════════════════════════════════════════

def preprocess_for_ocr(img_cv: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Preprocessing gambar untuk OCR:
    1. Denoising
    2. Adaptive threshold
    3. Remove horizontal/vertical lines
    4. Connect broken characters
    """
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

    # Denoising
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

    # Adaptive threshold (kunci untuk CAPTCHA)
    thresh = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV, 11, 2
    )

    # Hapus garis panjang (khas CAPTCHA)
    kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 1))
    kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 15))

    horizontal_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel_h)
    vertical_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel_v)
    all_lines = cv2.bitwise_or(horizontal_lines, vertical_lines)
    cleaned = cv2.bitwise_and(thresh, cv2.bitwise_not(all_lines))

    # Connect broken characters
    kernel_dilate = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    dilated = cv2.dilate(cleaned, kernel_dilate, iterations=1)

    # Invert for Tesseract
    final = cv2.bitwise_not(dilated)

    return final, thresh, cleaned


def detect_captcha_type(img_cv: np.ndarray) -> CaptchaDetection:
    """
    Deteksi apakah gambar adalah CAPTCHA berdasarkan fitur visual:
    - Jumlah garis (Hough Lines)
    - Level noise
    - Aspek rasio
    - Area solid
    - Jumlah blob kecil (karakter)
    """
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    features = {}

    # Feature 1: Jumlah garis
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50,
                            minLineLength=20, maxLineGap=5)
    features['line_count'] = len(lines) if lines is not None else 0

    # Feature 2: Noise level
    local_std = cv2.blur(gray.astype(np.float32)**2, (5, 5)) - \
                cv2.blur(gray.astype(np.float32), (5, 5))**2
    features['noise_level'] = np.mean(np.sqrt(np.maximum(local_std, 0)))

    # Feature 3: Aspek rasio
    features['aspect_ratio'] = w / h if h > 0 else 0

    # Feature 4: Area solid (foreground)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    features['solid_ratio'] = np.sum(thresh < 128) / (w * h)

    # Feature 5: Small blobs (karakter)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    small_contours = [c for c in contours if 20 < cv2.contourArea(c) < (w * h * 0.1)]
    features['small_blob_count'] = len(small_contours)

    # ── Scoring ──
    captcha_score = 0

    if features['line_count'] > 15:
        captcha_score += 30
    elif features['line_count'] > 8:
        captcha_score += 15

    if features['noise_level'] > 40:
        captcha_score += 25
    elif features['noise_level'] > 25:
        captcha_score += 15

    if 2.5 < features['aspect_ratio'] < 8:
        captcha_score += 20
    elif 1.5 < features['aspect_ratio'] < 10:
        captcha_score += 10

    if 0.1 < features['solid_ratio'] < 0.4:
        captcha_score += 15

    if 3 <= features['small_blob_count'] <= 15:
        captcha_score += 10

    # ── Tentukan tipe ──
    if captcha_score > 60:
        if features['line_count'] > 20:
            captcha_type = "CAPTCHA dengan garis coret (reCAPTCHA style)"
        elif features['noise_level'] > 50:
            captcha_type = "CAPTCHA dengan noise/dot berat"
        elif features['small_blob_count'] > 8:
            captcha_type = "CAPTCHA teks terdistorsi"
        else:
            captcha_type = "CAPTCHA standar"
    elif captcha_score > 40:
        captcha_type = "Kemungkinan CAPTCHA / teks dalam noise"
    else:
        captcha_type = "Bukan CAPTCHA (gambar normal / teks biasa)"

    return CaptchaDetection(
        is_captcha=captcha_score > 50,
        captcha_type=captcha_type,
        score=captcha_score,
        features=features
    )


def read_text_with_ocr(img_cv: np.ndarray, lang: str = 'eng') -> OCRResult:
    """
    Membaca teks dari gambar menggunakan Tesseract OCR.
    Mencoba original + preprocessed, pilih hasil terbaik.
    """
    if not HAS_TESSERACT:
        return OCRResult(
            best_text="",
            confidence=0,
            source="",
            original_text="",
            preprocessed_text="",
            error="pytesseract tidak terinstall. Install: pip install pytesseract"
        )

    gray_original = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    preprocessed, thresh, cleaned = preprocess_for_ocr(img_cv)

    def ocr_image(img, desc):
        try:
            data = pytesseract.image_to_data(img, lang=lang,
                                             output_type=pytesseract.Output.DICT)
            text = ' '.join([w for w, c in zip(data['text'], data['conf'])
                            if c > 30 and w.strip()])
            conf = np.mean([c for c in data['conf'] if c > 0]) if data['conf'] else 0
        except:
            text = pytesseract.image_to_string(img, lang=lang).strip()
            conf = 0
        return text, round(conf, 1)

    original_text, original_conf = ocr_image(gray_original, "original")
    preprocessed_text, preprocessed_conf = ocr_image(preprocessed, "preprocessed")

    # Pilih hasil terbaik
    if preprocessed_conf > original_conf:
        best_text = preprocessed_text
        best_conf = preprocessed_conf
        source = 'preprocessed'
    else:
        best_text = original_text
        best_conf = original_conf
        source = 'original'

    return OCRResult(
        best_text=best_text,
        confidence=best_conf,
        source=source,
        original_text=original_text,
        preprocessed_text=preprocessed_text,
        thresh_image=thresh,
        cleaned_image=cleaned
    )


def analyze_text_content(img_cv: np.ndarray) -> OCRResult:
    """
    Analisis teks lengkap: deteksi CAPTCHA + baca teksnya.
    """
    header("🔤 ANALISIS TEKS & CAPTCHA", "🔤")

    # ── Deteksi CAPTCHA ──
    captcha = detect_captcha_type(img_cv)

    print(f"\n  {Colors.BOLD}Deteksi CAPTCHA:{Colors.RESET}")

    if captcha.is_captcha:
        print(f"  {Colors.RED}{Colors.BOLD}⚠️  GAMBAR INI ADALAH CAPTCHA! "
              f"({captcha.score:.0f}%){Colors.RESET}")
    elif captcha.score > 40:
        print(f"  {Colors.ORANGE}⚡ Kemungkinan CAPTCHA ({captcha.score:.0f}%){Colors.RESET}")
    else:
        print(f"  {Colors.GREEN}✅ Bukan CAPTCHA ({captcha.score:.0f}%) - Gambar normal{Colors.RESET}")

    info("Tipe CAPTCHA", captcha.captcha_type)
    info("Jumlah Garis", f"{captcha.features['line_count']} garis")
    info("Level Noise", f"{captcha.features['noise_level']:.1f}")
    info("Blob Karakter", f"{captcha.features['small_blob_count']} karakter/objek kecil")

    # ── OCR Reading ──
    print(f"\n  {Colors.BOLD}🔍 Membaca Teks...{Colors.RESET}")

    ocr_result = read_text_with_ocr(img_cv)

    if ocr_result.error:
        print(f"  {Colors.YELLOW}⚠️  {ocr_result.error}{Colors.RESET}")
        return ocr_result

    # ── Tampilkan hasil ──
    print(f"\n  {Colors.BOLD}📝 Hasil Pembacaan:{Colors.RESET}")

    if ocr_result.original_text:
        print(f"  {Colors.DIM}Original: {Colors.RESET}\"{ocr_result.original_text}\" "
              f"({ocr_result.confidence}%)")

    if ocr_result.preprocessed_text:
        print(f"  {Colors.DIM}Cleaned:  {Colors.RESET}\"{ocr_result.preprocessed_text}\" "
              f"({ocr_result.confidence}%)")

    # Best result
    best = ocr_result.best_text if ocr_result.best_text else "(tidak terbaca)"
    print(f"\n  {Colors.GREEN}{Colors.BOLD}✨ Teks Terbaca: \"{best}\"{Colors.RESET}")
    print(f"  {Colors.DIM}   Confidence: {ocr_result.confidence}% "
          f"[source: {ocr_result.source}]{Colors.RESET}")

    # ── Analisis konten teks ──
    if ocr_result.best_text:
        text = ocr_result.best_text.strip()
        alnum_ratio = sum(c.isalnum() for c in text) / len(text) if text else 0

        if alnum_ratio > 0.8 and 4 <= len(text) <= 10:
            print(f"\n  {Colors.PURPLE}🔐 Teks ini terlihat seperti kode CAPTCHA/verifikasi{Colors.RESET}")
            print(f"     (alfanumerik, {len(text)} karakter, random string)")
        elif len(text.split()) >= 3:
            print(f"\n  {Colors.CYAN}📄 Teks ini terlihat seperti kalimat biasa{Colors.RESET}")
        elif text.isdigit():
            print(f"\n  {Colors.CYAN}🔢 Teks ini adalah angka{Colors.RESET}")

    return ocr_result


# ═══════════════════════════════════════════════════════════════
# 10. VISUAL STORY TELLING
# ═══════════════════════════════════════════════════════════════

def tell_visual_story(context: Dict[str, Any], atmosphere: Dict[str, Any],
                      composition: CompositionAnalysis, texture: Dict[str, Any]) -> None:
    """
    Menggabungkan semua analisis menjadi narasi deskriptif
    seperti manusia yang mendeskripsikan gambar.
    """
    header("CERITA VISUAL", "📖")

    story_parts = []
    category = context['category'].value

    # ── Opening ──
    category_openings = {
        "Potret Wajah": "👤 Ini adalah foto potret yang berfokus pada subjek manusia.",
        "Pemandangan": "🏞️  Pemandangan alam dengan komposisi yang luas.",
        "Urban/Arsitektur": "🏙️  Foto urban/arsitektur yang menampilkan struktur buatan manusia.",
        "Dokumen/Teks": "📄 Gambar ini berupa dokumen atau mengandung elemen teks dominan.",
        "CAPTCHA/Verifikasi": "🤖 Gambar ini adalah CAPTCHA — teks terdistorsi untuk verifikasi.",
    }
    story_parts.append(category_openings.get(category,
                       "🖼️  Sebuah gambar dengan komposisi yang menarik."))

    # ── Atmosphere ──
    emotion = atmosphere.get('primary_emotion', 'Netral')
    temp = atmosphere.get('temperature', 0)

    if temp > 0.1:
        story_parts.append(f"Nuansa hangat menciptakan kesan {emotion.lower()}.")
    elif temp < -0.1:
        story_parts.append(f"Warna-warna dingin memberikan atmosfer {emotion.lower()}.")
    else:
        story_parts.append(f"Palet warna netral menghadirkan mood {emotion.lower()}.")

    # ── Composition ──
    if composition.rule_of_thirds_score > 0.5:
        story_parts.append("Komposisi mengikuti kaidah rule-of-thirds dengan baik.")
    if composition.symmetry_score > 0.6:
        story_parts.append("Simetri yang kuat memberikan kesan formal dan terstruktur.")
    if composition.leading_lines_score > 0.5:
        story_parts.append("Garis-garis mengarahkan mata ke subjek utama.")

    # ── Texture ──
    if texture['texture_mean'] < 20:
        story_parts.append("Tekstur halus memberikan kesan lembut dan bersih.")
    elif texture['texture_mean'] > 50:
        story_parts.append("Detail tekstur yang kaya menambah dimensi visual.")

    # ── Print story ──
    print(f"\n  {Colors.CYAN}{Colors.BOLD}")
    for part in story_parts:
        print(f"  {part}")
    print(f"{Colors.RESET}")

    # ── Suggested Use Cases ──
    print(f"\n  {Colors.YELLOW}💡 Saran Penggunaan:{Colors.RESET}")
    suggestions = set()

    if context['category'] == ImageCategory.PORTRAIT:
        suggestions.update(["Foto profil profesional", "Media sosial personal"])
    elif context['category'] == ImageCategory.LANDSCAPE:
        suggestions.update(["Wallpaper/background", "Poster dekoratif", "Konten travel"])
    elif context['category'] == ImageCategory.URBAN:
        suggestions.update(["Portofolio arsitektur", "Konten editorial"])
    elif context['category'] == ImageCategory.DOCUMENT:
        suggestions.update(["Arsip digital", "Presentasi", "OCR/digitalisasi"])
    elif context['category'] == ImageCategory.CAPTCHA:
        suggestions.update(["Verifikasi keamanan", "Testing OCR/anti-bot"])

    if atmosphere.get('saturation', 50) > 70:
        suggestions.add("Desain eye-catching")
    if composition.horizon_position:
        suggestions.add("Background website/header")

    if not suggestions:
        suggestions.add("Konten visual umum")

    for sug in list(suggestions)[:5]:
        print(f"    • {sug}")

# ═══════════════════════════════════════════════════════════════
# VISION EXECUTOR — Skill ke-7 DNA Colony
# Dipanggil via SkillOrchestrator
# ═══════════════════════════════════════════════════════════════

class VisionExecutor:
    """
    Mata buatan DNA — bisa lihat, baca, dan solve CAPTCHA.
    
    Modes:
    - solve_captcha: lihat gambar → baca teks CAPTCHA
    - scan_page: lihat screenshot → deteksi tombol, input, teks
    - detect_error: lihat halaman error → identifikasi masalah
    - read_text: baca teks apa aja dari gambar
    """
    
    def __init__(self):
        self.history = []
        self.best_params = {
            "threshold_block": 11,
            "dilate_iter": 1,
            "canny_low": 50,
            "canny_high": 150
        }
    
    def execute(self, dna=None, mode: str = "solve_captcha", image_path: str = None, 
                auto_evolve: bool = False, **kwargs):
        """
        Entry point — dipanggil SkillOrchestrator.
        
        Args:
            dna: DNA object (dari orchestrator)
            mode: "solve_captcha" | "scan_page" | "detect_error" | "read_text"
            image_path: path ke gambar/screenshot
            auto_evolve: kalo True, kalo gagal panggil UHEE buat optimasi
        
        Returns:
            dict: {"success": bool, "mode": str, "result": ...}
        """
        if not image_path:
            image_path = kwargs.get("image", kwargs.get("path", ""))
        
        if not image_path or not os.path.exists(image_path):
            return {"success": False, "mode": mode, "error": "No image path provided"}
        
        img_cv = cv2.imread(image_path)
        if img_cv is None:
            return {"success": False, "mode": mode, "error": f"Failed to load: {image_path}"}
        
        if mode == "solve_captcha":
            result = self._solve_captcha(img_cv, image_path, dna, auto_evolve)
        elif mode == "scan_page":
            result = self._scan_page(img_cv)
        elif mode == "detect_error":
            result = self._detect_error(img_cv)
        elif mode == "read_text":
            result = self._read_any_text(img_cv)
        else:
            result = {"success": False, "error": f"Unknown mode: {mode}"}
        
        self.history.append({"mode": mode, "image": image_path, "success": result.get("success", False)})
        
        return {"success": result.get("success", False), "mode": mode, "result": result}
    
    # ── SOLVE CAPTCHA ──
    def _solve_captcha(self, img_cv, image_path, dna=None, auto_evolve=False):
        """Baca dan solve CAPTCHA."""
        captcha = detect_captcha_type(img_cv)
        
        if not captcha.is_captcha:
            return {"success": False, "captcha_detected": False, "message": "Not a CAPTCHA image"}
        
        ocr = read_text_with_ocr(img_cv)
        
        result = {
            "success": ocr.best_text != "",
            "captcha_detected": True,
            "captcha_type": captcha.captcha_type,
            "text": ocr.best_text,
            "confidence": ocr.confidence,
            "source": ocr.source
        }
        
        # Kalo gagal + auto_evolve + DNA ada → panggil UHEE
        if not result["success"] and auto_evolve and dna:
            result = self._evolve_and_retry(img_cv, image_path, dna)
        
        return result
    
    def _evolve_and_retry(self, img_cv, image_path, dna):
        """Panggil UHEE buat mutasi preprocessing lalu coba lagi."""
        try:
            dna.log_action("🧬 [Vision] CAPTCHA failed, evolving preprocessing...")
            
            evolve_result = dna.skills.execute_skill(
                dna, "uhee",
                action="evolve",
                source=inspect.getsource(preprocess_for_ocr),
                func_name="preprocess_for_ocr",
                generations=20,
                target="captcha_accuracy"
            )
            
            if evolve_result and evolve_result.get("success"):
                # Pakai parameter terbaik dari UHEE
                best = evolve_result.get("best_params", self.best_params)
                self.best_params = best
                
                # Retry dengan parameter baru
                ocr = read_text_with_ocr(img_cv)
                
                return {
                    "success": ocr.best_text != "",
                    "captcha_detected": True,
                    "text": ocr.best_text,
                    "confidence": ocr.confidence,
                    "evolved": True,
                    "params_used": best
                }
        except Exception as e:
            pass  # UHEE gak available, return apa adanya
        
        return {"success": False, "message": "Evolve failed or UHEE not available"}
    
    # ── SCAN PAGE ──
    def _scan_page(self, img_cv):
        """Scan halaman web — deteksi elemen UI."""
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        
        # Deteksi teks
        ocr = read_text_with_ocr(img_cv)
        
        # Deteksi tombol (area solid dengan kontur persegi)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        buttons = []
        inputs = []
        
        for c in contours:
            x, y, cw, ch = cv2.boundingRect(c)
            area = cw * ch
            aspect = cw / ch if ch > 0 else 0
            
            # Tombol: area kecil-sedang, aspect ratio masuk akal
            if 500 < area < 50000 and 1.5 < aspect < 10:
                buttons.append({"x": x, "y": y, "w": cw, "h": ch})
            # Input field: area panjang horizontal
            elif 1000 < area < 100000 and 3 < aspect < 20:
                inputs.append({"x": x, "y": y, "w": cw, "h": ch})
        
        return {
            "success": True,
            "text_on_page": ocr.best_text,
            "buttons_found": len(buttons),
            "buttons": buttons[:10],
            "inputs_found": len(inputs),
            "inputs": inputs[:10]
        }
    
    # ── DETECT ERROR ──
    def _detect_error(self, img_cv):
        """Deteksi halaman error — cari kata kunci error."""
        ocr = read_text_with_ocr(img_cv)
        text = ocr.best_text.lower() if ocr.best_text else ""
        
        error_patterns = {
            "404": "Page not found",
            "403": "Access forbidden",
            "500": "Server error",
            "502": "Bad gateway",
            "503": "Service unavailable",
            "captcha": "CAPTCHA verification required",
            "rate limit": "Too many requests",
            "blocked": "IP or account blocked",
            "error": "Generic error detected",
            "failed": "Operation failed"
        }
        
        detected = []
        for pattern, meaning in error_patterns.items():
            if pattern in text:
                detected.append({"pattern": pattern, "meaning": meaning})
        
        return {
            "success": True,
            "is_error": len(detected) > 0,
            "errors": detected,
            "full_text": ocr.best_text
        }
    
    # ── READ ANY TEXT ──
    def _read_any_text(self, img_cv):
        """Baca teks apapun dari gambar."""
        ocr = read_text_with_ocr(img_cv)
        
        return {
            "success": ocr.best_text != "",
            "text": ocr.best_text,
            "confidence": ocr.confidence
        }

# ═══════════════════════════════════════════════════════════════
# MAIN — SEMUA BERGABUNG
# ═══════════════════════════════════════════════════════════════

def main():
    """Entry point utama — jalankan semua analisis."""
    banner()

    if len(sys.argv) < 2:
        print(f"  {Colors.RED}{Colors.BOLD}Usage: python vision.py <path_gambar>{Colors.RESET}")
        print(f"  {Colors.DIM}Contoh: python vision.py foto.jpg")
        print(f"  Contoh: python vision.py captcha.png")
        print(f"  Contoh: python vision.py pemandangan.jpg{Colors.RESET}\n")
        sys.exit(1)

    path = sys.argv[1]

    if not os.path.exists(path):
        print(f"  {Colors.RED}✗ File tidak ditemukan: {path}{Colors.RESET}\n")
        sys.exit(1)

    print(f"  {Colors.DIM}📂 Membaca: {path}{Colors.RESET}")

    # ── Load gambar ──
    try:
        img_pil = Image.open(path)
        img_cv = cv2.imread(path)
        if img_cv is None:
            raise ValueError("OpenCV gagal membaca file")
    except Exception as e:
        print(f"  {Colors.RED}✗ Gagal membuka gambar: {e}{Colors.RESET}\n")
        sys.exit(1)

    print(f"  {Colors.DIM}🔬 Menganalisis... Mohon tunggu{Colors.RESET}")

    # ═══════════════════════════════════════════════
    # JALANKAN SEMUA ANALISIS
    # ═══════════════════════════════════════════════

    # 1. Info dasar
    w, h = analyze_basic(img_pil, path)

    # 2. Konteks & kategori
    context = analyze_context(img_pil, img_cv)

    # 3. Palet warna & harmoni
    analyze_colors_enhanced(img_pil)

    # 4. Atmosfer & emosi
    atmosphere = analyze_atmosphere(img_pil, img_cv, context)

    # 5. Komposisi fotografi
    composition = analyze_composition(img_cv)

    # 6. Tekstur & pola
    texture = analyze_texture(img_cv)

    # 7. Depth & dimensi
    depth = analyze_depth(img_cv)

    # 8. Deteksi bentuk geometris
    shapes = detect_shapes(img_cv)

    # 9. OCR & CAPTCHA Detection (FITUR BARU!)
    ocr_result = analyze_text_content(img_cv)

    # 10. Visual storytelling
    tell_visual_story(context, atmosphere, composition, texture)

    # ═══════════════════════════════════════════════
    # FOOTER
    # ═══════════════════════════════════════════════
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'─'*65}")
    print(f"  ✓ Analisis lengkap — Vision.py melihat, memahami, dan membaca 🧠👁️📖")
    print(f"{'─'*65}{Colors.RESET}\n")


if __name__ == "__main__":
    main()
