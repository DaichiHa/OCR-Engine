import argparse
import json
import os

import pytesseract
from PIL import Image


def iou(boxA, boxB):
    # boxes as [x1,y1,x2,y2]
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    interW = max(0, xB - xA)
    interH = max(0, yB - yA)
    inter = interW * interH
    boxAArea = max(0, boxA[2] - boxA[0]) * max(0, boxA[3] - boxA[1])
    boxBArea = max(0, boxB[2] - boxB[0]) * max(0, boxB[3] - boxB[1])
    denom = boxAArea + boxBArea - inter
    return inter / denom if denom > 0 else 0.0


def tess_words(img_path):
    im = Image.open(img_path)
    data = pytesseract.image_to_data(
        im, output_type=pytesseract.Output.DICT, lang="jpn+eng"
    )
    words = []
    n = len(data["text"])
    for i in range(n):
        txt = (data["text"][i] or "").strip()
        if txt == "":
            continue
        left = int(data["left"][i])
        t = int(data["top"][i])
        w = int(data["width"][i])
        h = int(data["height"][i])
        conf = float(data["conf"][i]) if data["conf"][i] not in (None, "") else -1.0
        box = [left, t, left + w, t + h]
        words.append({"box": box, "text": txt, "conf": conf, "source": "tess"})
    return words


def easy_items(easy_json_path):
    with open(easy_json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    items = []
    # data expected as list of dicts with 'bbox','text','prob' from our runner
    for it in data:
        bbox = it.get("bbox")
        if not bbox or len(bbox) < 4:
            continue
        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]
        box = [min(xs), min(ys), max(xs), max(ys)]
        items.append(
            {
                "box": box,
                "text": str(it.get("text", "")),
                "conf": float(it.get("prob", 0.0)),
                "source": "easy",
            }
        )
    return items


def merge(easy, tess, iou_thr=0.3):
    merged = []
    used_t = set()
    for e in easy:
        best = None
        bi = None
        for idx, t in enumerate(tess):
            if idx in used_t:
                continue
            score = iou(e["box"], t["box"])
            if score >= iou_thr and (best is None or score > best[0]):
                best = (score, t)
                bi = idx
        if best:
            t = best[1]
            used_t.add(bi)
            # choose by conf
            if e["conf"] >= max(0.0, t.get("conf", 0.0)):
                merged.append(
                    {
                        "box": e["box"],
                        "text": e["text"],
                        "conf": e["conf"],
                        "source": "easy",
                    }
                )
            else:
                merged.append(
                    {
                        "box": t["box"],
                        "text": t["text"],
                        "conf": t["conf"],
                        "source": "tess",
                    }
                )
        else:
            merged.append(e)

    # include leftover tess items
    for idx, t in enumerate(tess):
        if idx in used_t:
            continue
        merged.append(t)

    return merged


def layout_to_text(items):
    # sort by top then left
    items_sorted = sorted(items, key=lambda x: (x["box"][1], x["box"][0]))
    # compute median height
    heights = [
        b["box"][3] - b["box"][1]
        for b in items_sorted
        if (b["box"][3] - b["box"][1]) > 0
    ]
    med_h = sorted(heights)[len(heights) // 2] if heights else 20
    lines = []
    cur_line = []
    last_top = None
    for it in items_sorted:
        top = it["box"][1]
        if last_top is None:
            last_top = top
        if abs(top - last_top) > med_h * 1.2:
            if cur_line:
                lines.append(" ".join(cur_line))
            cur_line = [it["text"]]
            last_top = top
        else:
            cur_line.append(it["text"])
    if cur_line:
        lines.append(" ".join(cur_line))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", required=True)
    ap.add_argument("--easy", required=False)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    page = args.page
    outdir = args.out
    os.makedirs(outdir, exist_ok=True)

    easy_path = args.easy
    if easy_path is None:
        # fallback to likely path
        easy_path = os.path.join(
            os.path.dirname(outdir),
            "easyocr_outputs_page_010_full",
            "full_easyocr.json",
        )
    if not os.path.exists(easy_path):
        print("EasyOCR JSON not found:", easy_path)
        easy = []
    else:
        easy = easy_items(easy_path)

    tess = tess_words(page)

    merged = merge(easy, tess, iou_thr=0.3)

    merged_text = layout_to_text(merged)

    with open(os.path.join(outdir, "merged.md"), "w", encoding="utf-8") as f:
        f.write(merged_text)

    with open(os.path.join(outdir, "merged.json"), "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print("WROTE", outdir)


if __name__ == "__main__":
    main()
