import json
from pathlib import Path

import cv2
import numpy as np


def load_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def rect_from_box(box):
    xs = [p[0] for p in box]
    ys = [p[1] for p in box]
    return int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))


def expand_rect(r, w, h, pad=0.05):
    x1, y1, x2, y2 = r
    dx = int((x2 - x1) * pad)
    dy = int((y2 - y1) * pad)
    x1 = max(0, x1 - dx)
    y1 = max(0, y1 - dy)
    x2 = min(w - 1, x2 + dx)
    y2 = min(h - 1, y2 + dy)
    return x1, y1, x2, y2


def run(
    ppocr_json,
    img_path,
    out_report="ops/local_refine_report_page010.json",
    score_thr=0.75,
    upscale=3,
):
    data = load_json(ppocr_json)
    img = (
        cv2.imdecode(np.fromfile(img_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if False
        else cv2.imread(str(img_path))
    )
    if img is None:
        raise SystemExit("failed to read image: " + str(img_path))
    h, w = img.shape[:2]

    # lazy imports
    rapid_ok = False
    try:
        from rapidocr_onnxruntime import RapidOCR

        rapid = RapidOCR()
        rapid_ok = True
    except Exception:
        rapid = None

    ppocr_ok = False
    try:
        from onnxocr.onnx_paddleocr import ONNXPaddleOcr

        ppocr = ONNXPaddleOcr(
            _use_angle_cls=True, use_gpu=False, use_dml=False, use_openvino=False
        )
        ppocr_ok = True
    except Exception:
        ppocr = None

    out = []
    out_dir = Path("ops/local_refine")
    out_dir.mkdir(exist_ok=True)

    idx = 0
    for item in data:
        score = float(item.get("score", 0.0))
        if score >= score_thr:
            continue
        idx += 1
        box = item["box"]
        x1, y1, x2, y2 = rect_from_box(box)
        x1, y1, x2, y2 = expand_rect((x1, y1, x2, y2), w, h, pad=0.08)
        crop = img[y1:y2, x1:x2].copy()
        if crop.size == 0:
            continue
        up = cv2.resize(
            crop, None, fx=upscale, fy=upscale, interpolation=cv2.INTER_CUBIC
        )
        crop_path = out_dir / f"crop_{idx}.png"
        cv2.imwrite(str(crop_path), up)

        entry = {
            "idx": idx,
            "box": [x1, y1, x2, y2],
            "orig_text": item.get("text", ""),
            "orig_score": score,
            "crop": str(crop_path),
            "rapid": None,
            "ppocr": None,
        }

        if rapid_ok:
            try:
                r = rapid(str(crop_path))
                _cand = None
                if isinstance(r, tuple) or isinstance(r, list):
                    dets = r[0] if len(r) > 0 else r
                else:
                    dets = r
                if isinstance(dets, list) and len(dets) > 0:
                    best = max(dets, key=lambda z: float(z[2]) if len(z) >= 3 else 0)
                    entry["rapid"] = {"text": best[1], "score": float(best[2])}
                else:
                    entry["rapid"] = {"text": None, "score": None}
            except Exception as e:
                entry["rapid"] = {"error": str(e)}

        if ppocr_ok:
            try:
                res = ppocr.ocr(up)
                if res and isinstance(res, list) and len(res) > 0 and len(res[0]) > 0:
                    best = res[0][0]
                    txt = best[1][0] if isinstance(best[1], (list, tuple)) else best[1]
                    sc = (
                        float(best[1][1])
                        if isinstance(best[1], (list, tuple)) and len(best[1]) > 1
                        else None
                    )
                    entry["ppocr"] = {"text": txt, "score": sc}
                else:
                    entry["ppocr"] = {"text": None, "score": None}
            except Exception as e:
                entry["ppocr"] = {"error": str(e)}

        out.append(entry)

    Path(out_report).write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Wrote", out_report)


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--ppocr", default="ops/ppocr_page_010_pre3x.json")
    p.add_argument("--img", default="ops/page_010_pre3x.png")
    p.add_argument("--out", default="ops/local_refine_report_page010.json")
    p.add_argument("--thr", type=float, default=0.75)
    p.add_argument("--scale", type=int, default=3)
    args = p.parse_args()
    run(
        args.ppocr,
        args.img,
        out_report=args.out,
        score_thr=args.thr,
        upscale=args.scale,
    )
