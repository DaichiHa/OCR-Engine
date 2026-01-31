"""
Layout detection using PaddleOCR PP-Structure.
"""

import importlib
import importlib.util

import hybrid_extractor


TYPE_MAP = {
    "table": "table",
    "text": "text",
    "figure": "figure",
    "title": "text",
}


def _paddleocr_available():
    return importlib.util.find_spec("paddleocr") is not None


def _load_ppstructure():
    if not _paddleocr_available():
        return None
    paddleocr = importlib.import_module("paddleocr")
    return paddleocr.PPStructure


def _normalize_bbox(bbox):
    if not bbox or len(bbox) != 4:
        return None
    x1, y1, x2, y2 = bbox
    return [int(x1), int(y1), int(x2), int(y2)]


def detect_layout_regions(image_path):
    """
    Detect layout regions using PP-Structure.
    Returns list of dicts: {"type": "text|table|figure", "bbox": [x1,y1,x2,y2]}.
    """
    ppstructure = _load_ppstructure()
    if ppstructure is None:
        return []

    image = hybrid_extractor.read_image_robust(image_path)
    if image is None:
        return []

    engine = ppstructure(layout=True, table=False, ocr=False, show_log=False)
    results = engine(image)
    regions = []

    for region in results:
        region_type = TYPE_MAP.get(region.get("type"))
        bbox = _normalize_bbox(region.get("bbox"))
        if not region_type or bbox is None:
            continue
        regions.append({"type": region_type, "bbox": bbox})

    regions.sort(key=lambda item: (item["bbox"][1], item["bbox"][0]))
    return regions
