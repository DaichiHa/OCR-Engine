from pathlib import Path

from paddleocr import PaddleOCR

pocr = PaddleOCR(use_textline_orientation=False, lang="japan")
imgs = [Path("ops/page_010_clahe_1.png"), Path("ops/page_010_clahe_2.png")]
for img in imgs:
    print("Processing", img)
    res = pocr.ocr(str(img))
    out_txt = img.with_suffix(".ppocr.txt")
    with open(out_txt, "w", encoding="utf-8") as f:
        for line in res:
            for item in line:
                text = item[1][0] if isinstance(item[1], (list, tuple)) else str(item[1])
                f.write(text + "\n")
    print("Wrote", out_txt)
