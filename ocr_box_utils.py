import json
from typing import Dict, Iterable, List, Tuple

import cv2
import numpy as np
import pytesseract


def tesseract_data_to_boxes(
    data: Dict[str, List],
    page: int,
    engine: str,
) -> List[Dict]:
    records: List[Dict] = []
    total = len(data.get("text", []))
    for i in range(total):
        text = str(data["text"][i]).strip()
        if not text:
            continue
        conf_str = str(data["conf"][i])
        conf = float(conf_str) if conf_str not in ("", "-1") else 0.0
        bbox = [
            int(data["left"][i]),
            int(data["top"][i]),
            int(data["width"][i]),
            int(data["height"][i]),
        ]
        records.append(
            {
                "page": page,
                "block_id": i,
                "bbox": bbox,
                "conf": conf,
                "engine": engine,
                "text": text,
            }
        )
    return records


def collect_tesseract_boxes(
    pil_img,
    page: int,
    engine: str,
    config: str,
    lang: str,
) -> List[Dict]:
    data = pytesseract.image_to_data(
        pil_img,
        lang=lang,
        config=config,
        output_type=pytesseract.Output.DICT,
    )
    return tesseract_data_to_boxes(data, page, engine)


def write_jsonl(path: str, records: Iterable[Dict]) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def bbox_iou(a: List[int], b: List[int]) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    ax2, ay2 = ax + aw, ay + ah
    bx2, by2 = bx + bw, by + bh
    inter_x1, inter_y1 = max(ax, bx), max(ay, by)
    inter_x2, inter_y2 = min(ax2, bx2), min(ay2, by2)
    if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
        return 0.0
    inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
    a_area = aw * ah
    b_area = bw * bh
    union = a_area + b_area - inter_area
    return inter_area / union if union else 0.0


def find_engine_mismatches(
    primary: List[Dict],
    secondary: List[Dict],
    iou_threshold: float = 0.5,
) -> List[Tuple[int, str, int]]:
    mismatches: List[Tuple[int, str, int]] = []
    for p in primary:
        best_match = None
        best_iou = 0.0
        for s in secondary:
            if p["page"] != s["page"]:
                continue
            iou = bbox_iou(p["bbox"], s["bbox"])
            if iou > best_iou:
                best_iou = iou
                best_match = s
        if best_match and best_iou >= iou_threshold:
            if p["text"] != best_match["text"]:
                mismatches.append((p["page"], p["engine"], p["block_id"]))
                mismatches.append(
                    (
                        best_match["page"],
                        best_match["engine"],
                        best_match["block_id"],
                    )
                )
    return mismatches


def compute_edge_map(gray_image: np.ndarray) -> np.ndarray:
    return cv2.Canny(gray_image, 50, 150)


def is_wrinkle_suspect(
    edge_map: np.ndarray,
    bbox: List[int],
    density_threshold: float = 0.35,
) -> bool:
    x, y, w, h = bbox
    if w <= 0 or h <= 0:
        return False
    roi = edge_map[y : y + h, x : x + w]
    if roi.size == 0:
        return False
    density = float(np.count_nonzero(roi)) / float(roi.size)
    return density >= density_threshold
