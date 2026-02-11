from pathlib import Path

import pytesseract
from PIL import Image

img = Path("ops/page_010_clahe_1.png")
print("Image:", img.exists(), img)
for psm in (3, 6, 11):
    try:
        conf = f"--psm {psm} --oem 3"
        txt = pytesseract.image_to_string(Image.open(img), lang="jpn", config=conf)
        print("\n==== PSM", psm, "====")
        print(txt.strip())
    except Exception as e:
        print("PSM", psm, "error:", e)
