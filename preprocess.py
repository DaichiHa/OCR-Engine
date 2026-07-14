# -*- coding: utf-8 -*-
"""
preprocess.py — Crop / Orient / Deskew for OCR-Engine (DaichiHa/OCR-Engine)

────────────────────────────────────────────────────────────────
WHY (measured 2026-07-15 on a Meiji-era scan, P.6.pdf, 300dpi)
────────────────────────────────────────────────────────────────
The README claims "Image Preprocessing: Noise reduction, orientation
correction". Grepping hybrid_ocr_runner.py (420 lines) for
    deskew / rotate / crop / denoise / threshold / cv2
returns ZERO hits. Only PIL.Image.open exists. There is no preprocessing.

What the raw page actually looks like:
    2481 x 3509 px
    ★ 63.8% of the frame is black scanner border + margin
    ★ the page is rotated 90 degrees (glyphs lying on their side)
    skew is only -0.10 deg  <- negligible; deskew was NOT the problem

So Qwen-VL is currently being handed an image that is two-thirds garbage
and lying on its side. Fixing that is free and does not touch the model.

    crop only  -> 2.76x more pixels land on the glyphs at the same token cost
    rotate     -> the difference between "unreadable" and "readable"

────────────────────────────────────────────────────────────────
ORIENTATION: what works and what does not (all measured)
────────────────────────────────────────────────────────────────
tesseract --psm 0 (OSD)     axis OK, ★180-deg flip WRONG (no jpn traineddata)
                              in=  0deg -> says 90  (correct)
                              in=180deg -> says 90  (WRONG, 270 is correct)
row/col projection          axis 100% reliable (3.3x margin), ★cannot see the
                            180-deg flip - the stripe pattern is identical

=> Two stages. Stage 1 is free. Stage 2 asks the VLM you already have,
   once, on a 512px thumbnail. Do not pretend a projection can do it.

    pip install opencv-python-headless numpy
"""
from __future__ import annotations

import cv2
import numpy as np

MIN_INK = 0.005          # below this a page is treated as blank
DESKEW_RANGE = 5.0       # deg
DESKEW_STEP = 0.1


# ───────────────────────── 1. crop ─────────────────────────
def crop_paper(gray, pad=8):
    """Drop the black scanner border. Returns (cropped, bbox, kept_ratio)."""
    H, W = gray.shape
    _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (31, 31))
    clean = cv2.morphologyEx(bw, cv2.MORPH_OPEN, k)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(clean, 8)
    if n < 2:
        return gray, (0, 0, W, H), 1.0
    i = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    x, y, w, h, _ = stats[i]
    x, y = max(x - pad, 0), max(y - pad, 0)
    w, h = min(w + 2 * pad, W - x), min(h + 2 * pad, H - y)
    return gray[y:y + h, x:x + w], (x, y, w, h), (w * h) / (W * H)


# ───────────────────────── 2. axis ─────────────────────────
def _ink(gray):
    _, b = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return b / 255.0


def _stripe(p):
    return float(np.var(np.diff(p)) / (p.mean() ** 2 + 1e-9))


def orient_axis(gray):
    """Free. Decides 0/180 vs 90/270 — NOT the flip.
       Returns 0 (already on the right axis) or 90 (needs a quarter turn)."""
    b = _ink(gray)
    if b.mean() < MIN_INK:
        return 0
    row, col = _stripe(b.sum(axis=1)), _stripe(b.sum(axis=0))
    return 0 if row >= col else 90


# ───────────────────────── 3. flip (needs the VLM) ─────────────────────────
def orient_flip(gray, vlm_is_upright=None, thumb=512):
    """Resolve the remaining 180-deg ambiguity.
       vlm_is_upright(img) -> bool. Pass your Qwen call. One 512px thumbnail.
       Returns 0 or 180. If no callback is given, returns 0 and says so."""
    if vlm_is_upright is None:
        return 0, "no VLM callback -> 180-deg flip NOT resolved"
    s = thumb / max(gray.shape)
    small = cv2.resize(gray, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    if vlm_is_upright(small):
        return 0, "VLM: upright"
    return 180, "VLM: flipped"


# ───────────────────────── 4. deskew ─────────────────────────
def deskew(gray):
    """Fine rotation, +-5 deg. Maximises the sharpness of the line stripes."""
    b = _ink(gray)
    if b.mean() < MIN_INK:
        return gray, 0.0
    h, w = gray.shape
    best, ang = -1.0, 0.0
    for a in np.arange(-DESKEW_RANGE, DESKEW_RANGE + 1e-9, DESKEW_STEP):
        M = cv2.getRotationMatrix2D((w / 2, h / 2), a, 1)
        r = cv2.warpAffine(b, M, (w, h), flags=cv2.INTER_NEAREST)
        s = _stripe(r.sum(axis=1))
        if s > best:
            best, ang = s, float(a)
    if abs(ang) < 0.05:
        return gray, 0.0
    M = cv2.getRotationMatrix2D((w / 2, h / 2), ang, 1)
    return cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC,
                          borderValue=255), ang


# ───────────────────────── pipeline ─────────────────────────
def prepare(path_or_img, vlm_is_upright=None):
    """Returns (image_ready_for_OCR, report:dict)."""
    g = (cv2.imread(path_or_img, cv2.IMREAD_GRAYSCALE)
         if isinstance(path_or_img, str) else path_or_img)
    H0, W0 = g.shape
    g, bbox, kept = crop_paper(g)

    ax = orient_axis(g)
    if ax == 90:
        g = cv2.rotate(g, cv2.ROTATE_90_CLOCKWISE)

    fl, why = orient_flip(g, vlm_is_upright)
    if fl == 180:
        g = cv2.rotate(g, cv2.ROTATE_180)

    g, sk = deskew(g)
    return g, {
        "src": f"{W0}x{H0}",
        "out": f"{g.shape[1]}x{g.shape[0]}",
        "cropped_away_pct": round((1 - kept) * 100, 1),
        "pixel_gain_on_text": round(1 / kept, 2),
        "axis_rot_deg": ax,
        "flip_deg": fl,
        "flip_source": why,
        "skew_deg": round(sk, 2),
    }


# ───────────────────────── cli ─────────────────────────
if __name__ == "__main__":
    import json
    import sys
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else "prepared.png"
    out, rep = prepare(src)
    cv2.imwrite(dst, out)
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    print(f"-> {dst}")
    if rep["flip_source"].startswith("no VLM"):
        print("★ 180-deg flip unresolved. Pass vlm_is_upright=<your Qwen call>.")
