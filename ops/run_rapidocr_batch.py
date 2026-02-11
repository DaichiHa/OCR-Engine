import json
from pathlib import Path

from rapidocr_onnxruntime import RapidOCR


def process(img_path: Path):
    ocr = RapidOCR()
    res = ocr(str(img_path))
    # res may be tuple with first element list of detections
    if isinstance(res, tuple) and len(res) > 0:
        dets = res[0]
    else:
        dets = res
    out = []
    for item in dets:
        try:
            box, text, score = item
        except Exception:
            # fallback if structure differs
            if len(item) >= 3:
                box, text, score = item[0], item[1], item[2]
            else:
                continue
        out.append({"box": box, "text": text, "score": float(score)})
    # write json
    json_path = img_path.parent / (img_path.stem.replace("page_", "rapid_page_") + ".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    # make plain text sorted by top y
    def top_y(b):
        ys = [p[1] for p in b]
        return min(ys)

    sorted_out = sorted(out, key=lambda x: top_y(x["box"]))
    txt_path = img_path.parent / (img_path.stem.replace("page_", "rapid_page_") + ".txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        for o in sorted_out:
            f.write(f"{o['text']}\n")
    print("Wrote", json_path, "and", txt_path)


if __name__ == "__main__":
    imgs = [
        Path("ops/page_000_pre2x.png"),
        Path("ops/page_010_pre2x.png"),
        Path("ops/page_000_pre3x.png"),
        Path("ops/page_010_pre3x.png"),
    ]
    for img in imgs:
        if img.exists():
            process(img)
        else:
            print("Missing", img)
