"""
Ensemble OCR for Tesseract and PaddleOCR.
Aligns line-level results to a shared coordinate system and selects
best lines based on bbox overlap and confidence.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from statistics import median
from typing import Iterable, List, Optional, Tuple

import pytesseract
from PIL import Image


@dataclass(frozen=True)
class OcrLine:
    text: str
    bbox: Tuple[int, int, int, int]
    conf: float
    engine: str


@dataclass(frozen=True)
class EnsembleLine:
    text: str
    bbox: Tuple[int, int, int, int]
    conf: float
    engine: str
    iou: Optional[float]


def _safe_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _bbox_iou(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)
    inter_w = max(0, inter_x2 - inter_x1)
    inter_h = max(0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h
    if inter_area == 0:
        return 0.0
    area_a = max(0, ax2 - ax1) * max(0, ay2 - ay1)
    area_b = max(0, bx2 - bx1) * max(0, by2 - by1)
    denom = area_a + area_b - inter_area
    return inter_area / denom if denom > 0 else 0.0


def _line_center_y(line: OcrLine) -> float:
    return (line.bbox[1] + line.bbox[3]) / 2.0


def _line_height(line: OcrLine) -> int:
    return max(1, line.bbox[3] - line.bbox[1])


def _default_y_tolerance(lines: Iterable[OcrLine]) -> int:
    heights = [_line_height(line) for line in lines]
    if not heights:
        return 10
    return max(10, int(median(heights) * 0.6))


def _order_lines(
    lines: List[OcrLine], y_tolerance: Optional[int] = None
) -> List[OcrLine]:
    if not lines:
        return []
    tolerance = y_tolerance if y_tolerance is not None else _default_y_tolerance(lines)
    sorted_lines = sorted(lines, key=lambda l: (_line_center_y(l), l.bbox[0]))

    rows: List[dict] = []
    for line in sorted_lines:
        center = _line_center_y(line)
        placed = False
        for row in rows:
            if abs(center - row["center"]) <= tolerance:
                row["lines"].append(line)
                row["centers"].append(center)
                row["center"] = sum(row["centers"]) / len(row["centers"])
                placed = True
                break
        if not placed:
            rows.append({"center": center, "centers": [center], "lines": [line]})

    ordered: List[OcrLine] = []
    for row in rows:
        ordered.extend(sorted(row["lines"], key=lambda l: l.bbox[0]))
    return ordered


def _normalize_text(text: str) -> str:
    return " ".join(text.strip().split())


def run_tesseract_lines(image_path: str, lang: str = "jpn") -> List[OcrLine]:
    image = Image.open(image_path)
    data = pytesseract.image_to_data(
        image,
        lang=lang,
        config="--oem 3 --psm 6",
        output_type=pytesseract.Output.DICT,
    )

    lines: List[OcrLine] = []
    for idx, level in enumerate(data.get("level", [])):
        if int(level) != 4:
            continue
        text = _normalize_text(data["text"][idx])
        if not text:
            continue
        left = int(data["left"][idx])
        top = int(data["top"][idx])
        width = int(data["width"][idx])
        height = int(data["height"][idx])
        bbox = (left, top, left + width, top + height)
        conf = _safe_float(data["conf"][idx], default=0.0) / 100.0
        lines.append(OcrLine(text=text, bbox=bbox, conf=conf, engine="tesseract"))
    return _order_lines(lines)


@lru_cache(maxsize=1)
def _get_paddle_ocr(lang: str = "japan"):
    try:
        from paddleocr import PaddleOCR  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "PaddleOCR is not installed. Install paddleocr to enable ensemble OCR."
        ) from exc
    return PaddleOCR(lang=lang, use_angle_cls=True)


def run_paddle_lines(image_path: str, lang: str = "japan") -> List[OcrLine]:
    ocr_engine = _get_paddle_ocr(lang=lang)
    result = ocr_engine.ocr(image_path, cls=True)
    lines: List[OcrLine] = []
    for page in result:
        for item in page:
            points, (text, conf) = item
            clean_text = _normalize_text(text)
            if not clean_text:
                continue
            xs = [pt[0] for pt in points]
            ys = [pt[1] for pt in points]
            bbox = (int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys)))
            lines.append(
                OcrLine(text=clean_text, bbox=bbox, conf=float(conf), engine="paddle")
            )
    return _order_lines(lines)


def _match_lines(
    t_lines: List[OcrLine],
    p_lines: List[OcrLine],
    y_tolerance: Optional[int] = None,
) -> Tuple[List[Tuple[Optional[OcrLine], Optional[OcrLine]]], List[OcrLine]]:
    tolerance = (
        y_tolerance
        if y_tolerance is not None
        else _default_y_tolerance(t_lines + p_lines)
    )
    matches: List[Tuple[Optional[OcrLine], Optional[OcrLine]]] = []
    used_paddle: set[int] = set()

    for t_line in t_lines:
        t_center = _line_center_y(t_line)
        best_idx = None
        best_delta = None
        for idx, p_line in enumerate(p_lines):
            if idx in used_paddle:
                continue
            delta = abs(_line_center_y(p_line) - t_center)
            if delta <= tolerance and (best_delta is None or delta < best_delta):
                best_delta = delta
                best_idx = idx
        if best_idx is not None:
            used_paddle.add(best_idx)
            matches.append((t_line, p_lines[best_idx]))
        else:
            matches.append((t_line, None))

    remaining = [p for idx, p in enumerate(p_lines) if idx not in used_paddle]
    for p_line in remaining:
        matches.append((None, p_line))

    return matches, remaining


def _choose_line(
    t_line: Optional[OcrLine],
    p_line: Optional[OcrLine],
    iou_threshold: float = 0.3,
    conf_margin: float = 0.05,
) -> Tuple[Optional[EnsembleLine], Optional[dict]]:
    if t_line is None and p_line is None:
        return None, None
    if t_line is None:
        diff = {
            "reason": "tesseract_missing",
            "paddle": p_line.__dict__,
        }
        selected = EnsembleLine(
            text=p_line.text,
            bbox=p_line.bbox,
            conf=p_line.conf,
            engine=p_line.engine,
            iou=None,
        )
        return selected, diff
    if p_line is None:
        diff = {
            "reason": "paddle_missing",
            "tesseract": t_line.__dict__,
        }
        selected = EnsembleLine(
            text=t_line.text,
            bbox=t_line.bbox,
            conf=t_line.conf,
            engine=t_line.engine,
            iou=None,
        )
        return selected, diff

    iou = _bbox_iou(t_line.bbox, p_line.bbox)
    same_text = _normalize_text(t_line.text) == _normalize_text(p_line.text)
    conf_delta = t_line.conf - p_line.conf

    if same_text and iou >= iou_threshold:
        chosen = t_line if conf_delta >= 0 else p_line
        selected = EnsembleLine(
            text=chosen.text,
            bbox=chosen.bbox,
            conf=chosen.conf,
            engine=chosen.engine,
            iou=iou,
        )
        return selected, None

    if abs(conf_delta) >= conf_margin:
        chosen = t_line if conf_delta >= 0 else p_line
        reason = "conf_delta"
    else:
        chosen = t_line if conf_delta >= 0 else p_line
        reason = "low_conf_delta"

    diff = {
        "reason": reason,
        "iou": iou,
        "tesseract": t_line.__dict__,
        "paddle": p_line.__dict__,
    }
    selected = EnsembleLine(
        text=chosen.text,
        bbox=chosen.bbox,
        conf=chosen.conf,
        engine=chosen.engine,
        iou=iou,
    )
    return selected, diff


def ensemble_ocr_lines(
    image_path: str,
    tesseract_lang: str = "jpn",
    paddle_lang: str = "japan",
) -> Tuple[List[EnsembleLine], List[dict]]:
    t_lines = run_tesseract_lines(image_path, lang=tesseract_lang)
    p_lines = run_paddle_lines(image_path, lang=paddle_lang)

    matches, _ = _match_lines(t_lines, p_lines)

    selected: List[EnsembleLine] = []
    diffs: List[dict] = []
    for t_line, p_line in matches:
        chosen, diff = _choose_line(t_line, p_line)
        if chosen:
            selected.append(chosen)
        if diff:
            diffs.append(diff)

    return selected, diffs


def _write_jsonl(path: str, rows: List[dict]) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")


def process_image(
    image_path: str,
    output_dir: str,
    tesseract_lang: str = "jpn",
    paddle_lang: str = "japan",
) -> dict:
    os.makedirs(output_dir, exist_ok=True)
    selected_lines, diffs = ensemble_ocr_lines(
        image_path,
        tesseract_lang=tesseract_lang,
        paddle_lang=paddle_lang,
    )

    raw_lines = [line.text for line in selected_lines]
    raw_path = os.path.join(output_dir, "raw.txt")
    with open(raw_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(raw_lines))

    boxes_path = os.path.join(output_dir, "boxes.jsonl")
    boxes_payload = [
        {
            "text": line.text,
            "bbox": line.bbox,
            "conf": line.conf,
            "engine": line.engine,
            "iou": line.iou,
        }
        for line in selected_lines
    ]
    _write_jsonl(boxes_path, boxes_payload)

    diff_path = os.path.join(output_dir, "diff_queue.jsonl")
    _write_jsonl(diff_path, diffs)

    return {
        "raw_path": raw_path,
        "boxes_path": boxes_path,
        "diff_path": diff_path,
        "lines": selected_lines,
        "diffs": diffs,
    }
