import json
import os
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def _locate_tesseract():
    # Allow explicit override via environment variable
    env_cmd = os.environ.get("TESSERACT_CMD")
    if env_cmd:
        return env_cmd

    # Prefer system PATH-installed tesseract if available
    w = shutil.which("tesseract")
    if w:
        return w
    # Common install locations (prefer official install over bundled vendor)
    for p in (
        Path("C:/Program Files/Tesseract-OCR/tesseract.exe"),
        Path("C:/Program Files (x86)/Tesseract-OCR/tesseract.exe"),
    ):
        if p.exists():
            return str(p)

    # Fall back to repository bundled binary
    cand = REPO_ROOT / "vendor" / "tesseract" / "tesseract.exe"
    if cand.exists():
        return str(cand.resolve())
    return None


def levenshtein(a: str, b: str) -> int:
    # simple DP
    if a == b:
        return 0
    la, lb = len(a), len(b)
    if la == 0:
        return lb
    if lb == 0:
        return la
    dp = list(range(lb + 1))
    for i in range(1, la + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, lb + 1):
            cur = dp[j]
            cost = 0 if a[i - 1] == b[j - 1] else 1
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev + cost)
            prev = cur
    return dp[lb]


def normalize(s: str) -> str:
    return " ".join(s.strip().split()).upper()


def main():
    outdir = Path("ops") / "small_eval_out"
    outdir.mkdir(parents=True, exist_ok=True)

    # create synthetic image
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception as e:
        print("PIL not available:", e)
        sys.exit(2)

    expected = "SAMPLE TEXT 123"
    img = Image.new("RGB", (800, 200), color="white")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    d.text((10, 10), expected, fill="black", font=font)
    img_path = outdir / "sample.png"
    img.save(img_path)

    # locate and configure tesseract/pytesseract
    tess = _locate_tesseract()
    if tess:
        tess_dir = str(Path(tess).parent)
        os.environ["PATH"] = os.environ.get("PATH", "") + os.pathsep + tess_dir

    try:
        import pytesseract

        if tess:
            pytesseract.pytesseract.tesseract_cmd = tess
    except Exception as e:
        print("pytesseract not available:", e)
        sys.exit(3)

    try:
        recognized = pytesseract.image_to_string(str(img_path))
    except Exception as e:
        print("pytesseract failed:", e)
        sys.exit(4)

    norm_exp = normalize(expected)
    norm_rec = normalize(recognized)

    # metrics
    char_dist = levenshtein(norm_exp, norm_rec)
    char_acc = 1.0 - (char_dist / max(1, len(norm_exp)))

    exp_words = norm_exp.split()
    rec_words = norm_rec.split()
    matched = sum(1 for e, r in zip(exp_words, rec_words) if e == r)
    word_acc = matched / max(1, len(exp_words))

    results = {
        "expected": expected,
        "recognized_raw": recognized,
        "recognized_normalized": norm_rec,
        "char_levenshtein": char_dist,
        "char_accuracy": round(char_acc, 4),
        "word_accuracy": round(word_acc, 4),
    }

    out_file = outdir / "small_eval.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print("WROTE", out_file)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
