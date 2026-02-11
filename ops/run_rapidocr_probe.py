import sys
from pathlib import Path

from rapidocr_onnxruntime import RapidOCR

print("python:", sys.executable)
print("rapidocr module file:", RapidOCR.__module__)
print("Creating RapidOCR instance...")
ocr = RapidOCR()
print("Instance:", ocr)
img_paths = [Path("ops/page_000_pre2x.png"), Path("ops/page_010_pre2x.png")]
methods = [
    "ocr",
    "detect",
    "__call__",
    "predict",
    "run",
    "inference",
    "process",
]
for img in img_paths:
    print("\n---", img)
    for m in methods:
        if hasattr(ocr, m) and callable(getattr(ocr, m)):
            print("Trying method:", m)
            try:
                res = getattr(ocr, m)(str(img))
                print("Result type:", type(res))
                print("Sample repr:", repr(res)[:1000])
            except Exception as e:
                print("Method", m, "raised:", e)
        else:
            print("No method:", m)
