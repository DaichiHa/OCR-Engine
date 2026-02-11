import json
import os
import subprocess
import sys
from pathlib import Path

# Disable oneDNN/ONEDNN for Paddle runtime to avoid ConvertPirAttribute2RuntimeAttribute errors
os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("PADDLE_WITH_ONEDNN", "0")
os.environ.setdefault("PADDLE_DISABLE_ONEDNN", "1")
os.environ.setdefault("PADDLE_WITH_MKL", "0")

from paddleocr import PaddleOCR  # noqa: E402

# per-image timeout (seconds)
TIMEOUT_SECONDS = 30
TIMEOUT_SECONDS_WARMUP = 180

# allow forcing tesseract-only mode via env var
FORCE_TESSERACT_ONLY = os.environ.get("FORCE_TESSERACT_ONLY", "0") == "1"

# initialize OCR (document models)
_pocr = PaddleOCR(use_textline_orientation=False, lang="japan")

# search the ops tree for any image files referencing 'page_010' (archive or consolidated locations)
base = Path(__file__).parent
exts = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")
imgs = sorted([p for p in base.rglob("*") if p.is_file() and "page_010" in p.name.lower() and p.suffix.lower() in exts])
if not imgs:
    print("No page_010 images found under", base)

first = True
for img in imgs:
    print("\n--- Processing", img, "---")
    timeout = TIMEOUT_SECONDS_WARMUP if first else TIMEOUT_SECONDS
    first = False

    if FORCE_TESSERACT_ONLY:
        # directly run tesseract for this image
        cfgp = Path(__file__).parent / "paths_config.json"
        try:
            cfg = json.loads(cfgp.read_text(encoding="utf-8")) if cfgp.exists() else {}
        except Exception:
            cfg = {}
        tesseract = cfg.get("tesseract")
        if tesseract:
            out_base = str(img.with_suffix(""))
            try:
                print(
                    "FORCE_TESSERACT_ONLY: running tesseract:",
                    tesseract,
                    str(img),
                )
                subprocess.run(
                    [tesseract, str(img), out_base],
                    check=True,
                    timeout=TIMEOUT_SECONDS,
                )
                produced = Path(out_base + ".txt")
                if produced.exists():
                    try:
                        produced.replace(img.with_suffix(".ppocr.txt"))
                    except Exception:
                        target = img.with_suffix(".ppocr.txt")
                        if target.exists():
                            try:
                                target.unlink()
                            except Exception:
                                pass
                        produced.rename(target)
                    print("Tesseract wrote", img.with_suffix(".ppocr.txt"))
                else:
                    print("Tesseract did not produce expected file", produced)
            except subprocess.TimeoutExpired:
                print("Tesseract fallback timed out for", img)
            except Exception as te:
                print("Tesseract fallback failed:", repr(te))
        else:
            print("No tesseract path in paths_config.json; skipping fallback")
        # after forcing tesseract, continue to next image
        out_txt = img.with_suffix(".ppocr.txt")
        if out_txt.exists():
            print("Output available:", out_txt)
        else:
            print("No .ppocr.txt produced for", img)
        continue

    # call worker via subprocess to allow per-image timeout and isolation
    worker = Path(__file__).parent / "paddle_probe_worker.py"
    if not worker.exists():
        print("Worker script missing:", worker)
        break
    try:
        subprocess.run(
            [sys.executable, str(worker), str(img)],
            check=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        print("Timeout expired for", img, f"({TIMEOUT_SECONDS}s)")
        # try fallback to tesseract if configured, with same timeout
        cfgp = Path(__file__).parent / "paths_config.json"
        try:
            cfg = json.loads(cfgp.read_text(encoding="utf-8")) if cfgp.exists() else {}
        except Exception:
            cfg = {}
        tesseract = cfg.get("tesseract")
        if tesseract:
            out_base = str(img.with_suffix(""))
            try:
                print(
                    "Running tesseract fallback (with timeout):",
                    tesseract,
                    str(img),
                )
                subprocess.run(
                    [tesseract, str(img), out_base],
                    check=True,
                    timeout=TIMEOUT_SECONDS,
                )
                produced = Path(out_base + ".txt")
                if produced.exists():
                    try:
                        # atomically replace target if possible
                        target = img.with_suffix(".ppocr.txt")
                        if target.exists():
                            try:
                                target.unlink()
                            except Exception:
                                pass
                        produced.replace(target)
                    except Exception:
                        try:
                            produced.rename(img.with_suffix(".ppocr.txt"))
                        except Exception as re:
                            print("Rename fallback failed:", repr(re))
                    print("Tesseract wrote", img.with_suffix(".ppocr.txt"))
                else:
                    print("Tesseract did not produce expected file", produced)
            except subprocess.TimeoutExpired:
                print("Tesseract fallback timed out for", img)
            except Exception as te:
                print("Tesseract fallback failed:", repr(te))
        else:
            print("No tesseract path in paths_config.json; skipping fallback")
    except subprocess.CalledProcessError as cpe:
        print("Worker failed for", img, "->", cpe)
        # attempt tesseract fallback without waiting longer than TIMEOUT_SECONDS
        cfgp = Path(__file__).parent / "paths_config.json"
        try:
            cfg = json.loads(cfgp.read_text(encoding="utf-8")) if cfgp.exists() else {}
        except Exception:
            cfg = {}
        tesseract = cfg.get("tesseract")
        if tesseract:
            out_base = str(img.with_suffix(""))
            try:
                subprocess.run(
                    [tesseract, str(img), out_base],
                    check=True,
                    timeout=TIMEOUT_SECONDS,
                )
                produced = Path(out_base + ".txt")
                if produced.exists():
                    try:
                        produced.replace(img.with_suffix(".ppocr.txt"))
                    except Exception:
                        target = img.with_suffix(".ppocr.txt")
                        if target.exists():
                            try:
                                target.unlink()
                            except Exception:
                                pass
                        produced.rename(target)
                    print("Tesseract wrote", img.with_suffix(".ppocr.txt"))
                else:
                    print("Tesseract did not produce expected file", produced)
            except subprocess.TimeoutExpired:
                print("Tesseract fallback timed out for", img)
            except Exception as te:
                print("Tesseract fallback failed:", repr(te))
        else:
            print("No tesseract path in paths_config.json; skipping fallback")
    # worker/subprocess mode: check for created .ppocr.txt or report fallback status
    out_txt = img.with_suffix(".ppocr.txt")
    if out_txt.exists():
        print("Output available:", out_txt)
    else:
        print("No .ppocr.txt produced for", img)
