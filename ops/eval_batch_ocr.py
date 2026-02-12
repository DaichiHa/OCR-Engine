import argparse
import json
import os
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def levenshtein(a: str, b: str) -> int:
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


def _locate_tesseract():
    env_cmd = os.environ.get("TESSERACT_CMD")
    if env_cmd:
        return env_cmd
    w = shutil.which("tesseract")
    if w:
        return w
    for p in (
        Path("C:/Program Files/Tesseract-OCR/tesseract.exe"),
        Path("C:/Program Files (x86)/Tesseract-OCR/tesseract.exe"),
    ):
        if p.exists():
            return str(p)
    cand = REPO_ROOT / "vendor" / "tesseract" / "tesseract.exe"
    if cand.exists():
        return str(cand.resolve())
    return None


def process_image_pytesseract(img_path: Path, tess_cmd: str | None):
    try:
        import pytesseract

        # Image is not used directly here but kept for compatibility checks
        # and to surface import errors early.
        from PIL import Image  # noqa: F401
    except Exception as e:
        return None, f"import_error: {e}"

    if tess_cmd:
        pytesseract.pytesseract.tesseract_cmd = tess_cmd

    try:
        txt = pytesseract.image_to_string(str(img_path))
        return txt, None
    except Exception as e:
        return None, repr(e)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input-dir", default="ops/small_eval_out")
    p.add_argument("--out", default="ops/small_eval_out/batch_results.json")
    p.add_argument("--restore-spaces", action="store_true", help="Try to restore missing spaces using wordninja")
    p.add_argument("--recursive", action="store_true", help="Recursively search for images under input dir")
    p.add_argument("--csv", action="store_true", help="Write a CSV summary alongside the JSON report")
    p.add_argument("--csv-out", default=None, help="Path to write CSV output (defaults to <out>.csv)")
    args = p.parse_args()

    inp = Path(args.input_dir)
    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)

    tess = _locate_tesseract()
    # optional space restoration
    restore_spaces = args.restore_spaces
    has_wordninja = False
    if restore_spaces:
        try:
            import wordninja

            has_wordninja = True
        except Exception:
            has_wordninja = False

    exts = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
    if args.recursive:
        images = [p for p in inp.rglob("*") if p.suffix.lower() in exts]
    else:
        images = [p for p in inp.iterdir() if p.suffix.lower() in exts]

    results = {"summary": {}, "items": []}
    total_char_acc = 0.0
    total_word_acc = 0.0
    count = 0

    for img in images:
        expected_file = img.with_suffix(".txt")
        if not expected_file.exists():
            # try a helper small_eval.json
            small_json = inp / "small_eval.json"
            expected = None
            if small_json.exists():
                try:
                    sj = json.loads(small_json.read_text(encoding="utf-8"))
                    expected = sj.get("expected")
                except Exception:
                    expected = None
            if expected is None:
                results["items"].append({"image": str(img), "skipped": "no expected ground-truth (.txt)"})
                continue
        else:
            expected = expected_file.read_text(encoding="utf-8").strip()

        rec, err = process_image_pytesseract(img, tess)
        if err:
            results["items"].append({"image": str(img), "error": err})
            continue

        norm_e = normalize(expected)
        # Optionally attempt to restore spaces when OCR drops them
        if restore_spaces and has_wordninja and (rec is not None):
            compact = "".join((rec or "").split())
            try:
                words = wordninja.split(compact.lower())
                restored = " ".join(w.upper() for w in words)
                norm_r = normalize(restored)
            except Exception:
                norm_r = normalize(rec or "")
        else:
            norm_r = normalize(rec or "")
        char_dist = levenshtein(norm_e, norm_r)
        char_acc = 1.0 - (char_dist / max(1, len(norm_e)))
        exp_words = norm_e.split()
        rec_words = norm_r.split()
        matched = sum(1 for e, r in zip(exp_words, rec_words) if e == r)
        word_acc = matched / max(1, len(exp_words))

        results["items"].append(
            {
                "image": str(img),
                "expected": expected,
                "recognized": rec,
                "char_levenshtein": char_dist,
                "char_accuracy": round(char_acc, 4),
                "word_accuracy": round(word_acc, 4),
            }
        )

        total_char_acc += char_acc
        total_word_acc += word_acc
        count += 1

    if count:
        results["summary"]["mean_char_accuracy"] = round(total_char_acc / count, 4)
        results["summary"]["mean_word_accuracy"] = round(total_word_acc / count, 4)
        results["summary"]["evaluated_count"] = count
    else:
        results["summary"]["evaluated_count"] = 0

    outp.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print("WROTE", outp)
    print(json.dumps(results.get("summary", {}), ensure_ascii=False, indent=2))

    if args.csv:
        import csv

        csv_out = args.csv_out or str(outp) + ".csv"
        with open(csv_out, "w", newline="", encoding="utf-8") as cf:
            writer = csv.writer(cf)
            writer.writerow(["image", "expected", "recognized", "char_accuracy", "word_accuracy", "error", "skipped"])
            for it in results["items"]:
                writer.writerow(
                    [
                        it.get("image"),
                        it.get("expected"),
                        it.get("recognized"),
                        it.get("char_accuracy"),
                        it.get("word_accuracy"),
                        it.get("error", ""),
                        it.get("skipped", ""),
                    ]
                )
        print("WROTE", csv_out)


if __name__ == "__main__":
    main()
