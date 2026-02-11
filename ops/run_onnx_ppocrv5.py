import json
from pathlib import Path

import cv2
from onnxocr.onnx_paddleocr import ONNXPaddleOcr

ocr = ONNXPaddleOcr(_use_angle_cls=True, use_gpu=False, use_dml=False, use_openvino=False)


def process(img_path: Path):
    img = (
        cv2.imdecode(np.fromfile(str(img_path), dtype=np.uint8), cv2.IMREAD_COLOR)
        if False
        else cv2.imread(str(img_path))
    )
    if img is None:
        print("Failed to read", img_path)
        return
    res = ocr.ocr(img)
    out = []
    if res and isinstance(res, list) and len(res) > 0:
        for item in res[0]:
            box = item[0]
            text = item[1][0]
            score = float(item[1][1])
            out.append({"box": box, "text": text, "score": score})
    js = img_path.parent / (img_path.stem.replace("page_", "ppocr_page_") + ".json")
    with open(js, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    txt = img_path.parent / (img_path.stem.replace("page_", "ppocr_page_") + ".txt")
    with open(txt, "w", encoding="utf-8") as f:
        for o in out:
            f.write(o["text"] + "\n")
    print("Wrote", js, txt)


if __name__ == "__main__":

    import numpy as np

    imgs = [Path("ops/page_000_pre3x.png"), Path("ops/page_010_pre3x.png")]
    for p in imgs:
        if p.exists():
            process(p)
        else:
            print("Missing", p)
