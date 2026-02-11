import os
import sys
from pathlib import Path

# minimal worker that runs PaddleOCR for a single image and writes .ppocr.txt
os.environ.setdefault("FLAGS_use_mkldnn", "0")
os.environ.setdefault("PADDLE_WITH_ONEDNN", "0")
os.environ.setdefault("PADDLE_DISABLE_ONEDNN", "1")
os.environ.setdefault("PADDLE_WITH_MKL", "0")


def main():
    if len(sys.argv) < 2:
        print("Usage: paddle_probe_worker.py <image-path>")
        return 2
    img = Path(sys.argv[1])
    if not img.exists():
        print("Image not found:", img)
        return 3
    try:
        from paddleocr import PaddleOCR

        pocr = PaddleOCR(use_textline_orientation=False, lang="japan")
        res = pocr.ocr(str(img))
    except Exception as e:
        print("Worker PaddleOCR error:", repr(e))
        return 4

    out_txt = img.with_suffix(".ppocr.txt")
    out_tmp = img.with_suffix(".ppocr.txt.tmp")
    written = 0
    try:
        # write to a temp file first, then atomically replace
        if out_tmp.exists():
            try:
                out_tmp.unlink()
            except Exception:
                pass
        with open(out_tmp, "w", encoding="utf-8") as f:
            if isinstance(res, (list, tuple)):
                for page in res:
                    if isinstance(page, (list, tuple)):
                        for item in page:
                            try:
                                if isinstance(item, (list, tuple)) and len(item) >= 2:
                                    txt = None
                                    if isinstance(item[1], (list, tuple)):
                                        txt = item[1][0]
                                    elif isinstance(item[1], str):
                                        txt = item[1]
                                    elif isinstance(item[1], dict) and "text" in item[1]:
                                        txt = item[1]["text"]
                                    if txt:
                                        f.write(str(txt) + "\n")
                                        written += 1
                            except Exception:
                                continue
                    else:
                        s = str(page)
                        if s.strip():
                            f.write(s + "\n")
                            written += 1
            else:
                s = str(res)
                if s.strip():
                    f.write(s + "\n")
                    written += 1
    except Exception as e:
        print("Write error:", repr(e))
        # cleanup tmp
        try:
            if out_tmp.exists():
                out_tmp.unlink()
        except Exception:
            pass
        return 5

    # atomic replace tmp -> final
    try:
        out_tmp.replace(out_txt)
    except Exception as e:
        print("Atomic replace failed:", repr(e))
        try:
            if out_txt.exists():
                out_txt.unlink()
        except Exception:
            pass
        try:
            out_tmp.rename(out_txt)
        except Exception as e2:
            print("Final rename failed:", repr(e2))
            return 6

    print("Wrote", out_txt, "lines=", written)
    return 0


if __name__ == "__main__":
    sys.exit(main())
