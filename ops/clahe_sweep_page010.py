import argparse
import os
import subprocess
import sys
from pathlib import Path

try:
    from rapidocr_onnxruntime import RapidOCR
except Exception:
    RapidOCR = None


# Fallback wrapper that mimics RapidOCR minimal output shape
def _make_fallback_ocr():
    try:
        # prefer paddleocr if available
        from paddleocr import PaddleOCR

        pocr = PaddleOCR(use_textline_orientation=False, lang="japan")

        class PaddleWrapper:
            def __call__(self, img_path):
                res = pocr.ocr(img_path)
                dets = []
                for line in res:
                    for item in line:
                        box = item[0]
                        text = item[1][0]
                        score = float(item[1][1]) if len(item[1]) > 1 else 1.0
                        dets.append((box, text, score))
                return dets

        return PaddleWrapper()
    except Exception:
        pass
    try:
        # fallback to pytesseract (line-based, no boxes)
        import pytesseract
        from PIL import Image

        class TesseractWrapper:
            def __call__(self, img_path):
                img = Image.open(img_path)
                txt = pytesseract.image_to_string(img, lang="jpn")
                lines = [line.strip() for line in txt.splitlines() if line.strip()]
                dets = []
                for t in lines:
                    dets.append((None, t, 1.0))
                return dets

        return TesseractWrapper()
    except Exception:
        # last-resort no-op OCR: return empty list
        class EmptyWrapper:
            def __call__(self, img_path):
                return []

        return EmptyWrapper()


if RapidOCR is None:
    ocr = _make_fallback_ocr()
else:
    ocr = RapidOCR()


# CLI: allow selecting page and preprocess python executable
def _parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--page", default="010", help="page id (e.g. 000, 010)")
    p.add_argument(
        "--smoke", action="store_true", help="run a fast smoke test (limit combos)"
    )
    p.add_argument(
        "--preprocess-python",
        default=None,
        help="python executable to run preprocess script",
    )
    return p.parse_args()


args = _parse_args()
page = args.page
miniconda_py = r"C:/Users/User/Miniconda3/envs/ocr311/python.exe"
if args.preprocess_python:
    preprocess_python = args.preprocess_python
else:
    preprocess_python = miniconda_py if Path(miniconda_py).exists() else sys.executable

user_src = Path(f"C:/Users/User/Downloads/PDF/_img/page_{page}.png")
repo_src = Path(f"ops/page_{page}.png")
if user_src.exists():
    src = user_src
else:
    src = repo_src
    if not src.exists():
        print(
            f"Input image not found: {user_src} -- creating synthetic sample at {src} for CI"
        )
        try:
            from PIL import Image, ImageDraw

            # create a simple white sample image with page label
            img_w, img_h = 1200, 1600
            img = Image.new("RGB", (img_w, img_h), color="white")
            draw = ImageDraw.Draw(img)
            text = f"SAMPLE PAGE {page}"
            draw.text((40, 40), text, fill="black")
            src.parent.mkdir(parents=True, exist_ok=True)
            img.save(src)
            print("Wrote synthetic sample image to", src)
        except Exception as e:
            print("Failed to create sample image:", e)
            sys.exit(0)
print("Using input image:", src)
# CI-specific workaround: when running on GitHub Actions, try to disable oneDNN/mkldnn
# to avoid runtime NotImplementedError originating from Paddle/PaddleX oneDNN integration.
if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
    os.environ.setdefault("FLAGS_use_mkldnn", "0")
    os.environ.setdefault("PADDLE_WITH_ONEDNN", "0")
    os.environ.setdefault("PADDLE_DISABLE_ONEDNN", "1")
    os.environ.setdefault("PADDLE_WITH_MKL", "0")
    print("Detected CI environment: set Paddle/OneDNN disable env vars")
from itertools import product

import pytesseract
from PIL import Image
from postprocess_and_score import process_and_score

# broader grid of SR scales + CLAHE combos: (scale, clip, tile, denoise_h)
scales = [2, 3]
clip_vals = [1.5, 2.5, 4.0]
tile_vals = [4, 8, 16]
denoise_vals = [0, 8, 12]
combos = list(product(scales, clip_vals, tile_vals, denoise_vals))
# smoke: limit the number of combos to keep runs fast
if args.smoke:
    combos = combos[:2]
results = []
for i, combo in enumerate(combos, start=1):
    scale, clip, tile, denoise = combo
    out = Path(f"ops/page_010_clahe_{i}.png")
    cmd = [
        preprocess_python,
        "ops/preprocess_sr_clahe.py",
        "--in",
        str(src),
        "--out",
        str(out),
        "--scale",
        str(scale),
        "--clahe-clip",
        str(clip),
        "--clahe-tile",
        str(tile),
        "--denoise-h",
        str(denoise),
        "--deskew",
        "--binarize",
    ]
    print("Running:", " ".join(cmd))
    try:
        subprocess.run(cmd, check=True, timeout=90)
        print("Preprocessed ->", out)
    except subprocess.TimeoutExpired:
        print("Preprocess timeout for", out, "skipping this combo")
        continue
    except subprocess.CalledProcessError as e:
        print("Preprocess failed for", out, "->", e)
        continue
    except Exception as e:
        print("Preprocess error for", out, "->", e)
        continue
    # RapidOCR inference (normalize various return shapes)
    try:
        res = ocr(str(out))
    except Exception as e:
        print("OCR engine failed on", out, "->", repr(e))
        res = []

    def _normalize_res(r):
        if r is None:
            return []
        if isinstance(r, (tuple, list)):
            if len(r) == 0:
                return []
            # case: (dets, scores...) where dets is a list/tuple
            if isinstance(r[0], (list, tuple)):
                return list(r[0])
            # case: flat list of detections
            if all(isinstance(x, (list, tuple)) for x in r):
                return list(r)
        # single detection fallback
        return [r]

    dets = _normalize_res(res)
    txt_path = out.with_suffix(".rapid.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        for item in dets:
            try:
                _, text, _ = item
            except Exception:
                if len(item) >= 3:
                    _, text, _ = item[0], item[1], item[2]
                else:
                    continue
            f.write(str(text) + "\n")
    print("Wrote rapid txt:", txt_path)
    # Postprocess KPI for rapid output
    _, summary_rapid = process_and_score(str(txt_path))
    # Also run Tesseract (PSM 11) as an additional engine and score it
    tess_path = out.with_suffix(".tess.psm11.txt")
    try:
        tess_txt = pytesseract.image_to_string(
            Image.open(out), lang="jpn", config="--psm 11 --oem 3"
        )
    except Exception:
        tess_txt = ""
    with open(tess_path, "w", encoding="utf-8") as f:
        f.write(tess_txt)
    _, summary_tess = process_and_score(str(tess_path))
    results.append(
        {
            "combo": (scale, clip, tile, denoise),
            "rapid": summary_rapid,
            "tesseract_psm11": summary_tess,
        }
    )

# write results
import json

with open("ops/clahe_sweep_page010_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print("WROTE ops/clahe_sweep_page010_results.json")
