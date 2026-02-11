import json
import os
import shutil
import sys
from pathlib import Path

# Ensure repo root is on sys.path so imports like `ocr_ensemble` work
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


# Try to locate a tesseract executable and ensure it's available in PATH
def _locate_tesseract():
    # common vendor location inside repo
    cand = REPO_ROOT / "vendor" / "tesseract" / "tesseract.exe"
    if cand.exists():
        return str(cand.resolve())
    # common install locations
    for p in (
        Path("C:/Program Files/Tesseract-OCR/tesseract.exe"),
        Path("C:/Program Files (x86)/Tesseract-OCR/tesseract.exe"),
    ):
        if p.exists():
            return str(p)
    # fallback to system PATH
    w = shutil.which("tesseract")
    if w:
        return w
    return None


tess = _locate_tesseract()
if tess:
    tess_dir = str(Path(tess).parent)
    # ensure subprocesses inherit the PATH that includes tesseract
    os.environ["PATH"] = os.environ.get("PATH", "") + ";" + tess_dir
    try:
        import pytesseract

        pytesseract.pytesseract.tesseract_cmd = tess
    except Exception:
        pass
    print("Using tesseract:", tess)
else:
    print("tesseract not found; subprocesses may fail if Tesseract isn't installed or bundled")

OUT = Path("ops") / "smoke_out"
OUT.mkdir(parents=True, exist_ok=True)

# 1) Create a synthetic image
try:
    from PIL import Image, ImageDraw
except Exception as e:
    print("PIL missing:", e)
    sys.exit(2)

img_path = OUT / "smoke_img.png"
img = Image.new("RGB", (800, 200), color="white")
d = ImageDraw.Draw(img)
d.text((10, 10), "SAMPLE TEXT 123", fill="black")
img.save(img_path)
print("Wrote sample image:", img_path)

results = {}

# 2) Run ocr_ensemble.process_image
try:
    from ocr_ensemble import process_image
except Exception as e:
    results["ocr_ensemble_import_error"] = repr(e)
    print("ocr_ensemble import failed:", e)
else:
    try:
        outdir = str(OUT / "ocr_ensemble")
        res = process_image(str(img_path), outdir)
        # convert selected lines to simple serializable form
        lines = [
            {
                "text": getattr(ln, "text", str(ln)),
                "bbox": getattr(ln, "bbox", None),
                "conf": getattr(ln, "conf", None),
                "engine": getattr(ln, "engine", None),
            }
            for ln in res.get("lines", [])
        ]
        results["ocr_ensemble"] = {
            "out": res.get("raw_path"),
            "lines": lines,
            "diffs_count": len(res.get("diffs", [])),
        }
        print("ocr_ensemble result written to", res.get("raw_path"))
    except Exception as e:
        results["ocr_ensemble_error"] = repr(e)
        print("ocr_ensemble processing failed:", e)

# 3) Run clahe_sweep_page010.py --smoke
try:
    import subprocess

    cmd = [
        sys.executable,
        str(Path("ops") / "clahe_sweep_page010.py"),
        "--page",
        "010",
        "--smoke",
    ]
    print("Running:", " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    results["clahe_returncode"] = proc.returncode
    results["clahe_stdout"] = proc.stdout.splitlines()[-50:]
    results["clahe_stderr"] = proc.stderr.splitlines()[-50:]
    print("clahe returncode", proc.returncode)
except Exception as e:
    results["clahe_error"] = repr(e)
    print("clahe run failed:", e)

# Save results
with open(OUT / "smoke_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("WROTE", OUT / "smoke_results.json")
print(json.dumps(results, ensure_ascii=False, indent=2))
