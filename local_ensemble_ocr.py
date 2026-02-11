"""
Local Multi-process Ensemble OCR (LME)
Runs multiple preprocessing variants per cell and combines results locally.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import cv2
import pytesseract
from PIL import Image

from table_extractor_v4 import extract_table_structure_v4, read_image_robust

NUMERIC_RE = re.compile(r"^[0-9.,\-\s]+$")


@dataclass(frozen=True)
class OcrVariant:
    name: str
    image: Image.Image


def load_dictionary_map(path: Optional[str]) -> Dict[str, str]:
    if not path:
        return {}
    if not os.path.exists(path):
        raise FileNotFoundError(f"Dictionary file not found: {path}")

    _, ext = os.path.splitext(path)
    mapping: Dict[str, str] = {}

    if ext.lower() == ".json":
        import json

        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError("Dictionary JSON must be an object of {wrong: correct} pairs.")
        mapping = {str(k): str(v) for k, v in data.items()}
        return mapping

    with open(path, "r", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if not row:
                continue
            if len(row) < 2:
                parts = re.split(r"\t+", row[0].strip())
                if len(parts) < 2:
                    continue
                wrong, correct = parts[0], parts[1]
            else:
                wrong, correct = row[0].strip(), row[1].strip()
            if wrong:
                mapping[wrong] = correct

    return mapping


def preprocess_variants(cell_img) -> List[OcrVariant]:
    gray = cv2.cvtColor(cell_img, cv2.COLOR_BGR2GRAY)

    original = Image.fromarray(gray)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrast = clahe.apply(gray)
    contrast = cv2.threshold(contrast, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    contrast_img = Image.fromarray(contrast)

    edges = cv2.Canny(gray, 50, 150)
    edges = cv2.dilate(edges, cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2)), iterations=1)
    edges = cv2.bitwise_not(edges)
    edge_img = Image.fromarray(edges)

    return [
        OcrVariant("original", original),
        OcrVariant("contrast", contrast_img),
        OcrVariant("edges", edge_img),
    ]


def run_tesseract(img: Image.Image, lang: str) -> str:
    config = r"--oem 3 --psm 7"
    text = pytesseract.image_to_string(img, lang=lang, config=config)
    return text.strip().replace("\n", " ").replace("|", "")


def score_numeric(text: str) -> int:
    return sum(1 for ch in text if ch.isdigit())


def pick_numeric_candidate(candidates: List[str]) -> Optional[str]:
    numeric_candidates = [c for c in candidates if NUMERIC_RE.match(c)]
    if not numeric_candidates:
        return None
    scored = sorted(
        numeric_candidates,
        key=lambda c: (score_numeric(c), len(c)),
        reverse=True,
    )
    return scored[0] if scored else None


def majority_vote_text(candidates: List[str]) -> str:
    if not candidates:
        return ""
    numeric_pick = pick_numeric_candidate(candidates)
    if numeric_pick:
        return numeric_pick

    max_len = max(len(c) for c in candidates)
    output_chars = []
    for idx in range(max_len):
        column_chars = [c[idx] for c in candidates if idx < len(c) and c[idx].strip()]
        if not column_chars:
            continue
        counts = Counter(column_chars)
        output_chars.append(counts.most_common(1)[0][0])
    return "".join(output_chars).strip()


def apply_dictionary(text: str, mapping: Dict[str, str]) -> str:
    if not mapping:
        return text
    return mapping.get(text, text)


def ocr_cell_ensemble(cell_img, lang: str, mapping: Dict[str, str]) -> str:
    variants = preprocess_variants(cell_img)
    results = [run_tesseract(variant.image, lang) for variant in variants]
    consensus = majority_vote_text(results)
    return apply_dictionary(consensus, mapping)


def group_rows(cells: List[Tuple[int, int, int, int]], tolerance: int = 20):
    rows = []
    if not cells:
        return rows
    current_row = [cells[0]]
    current_y = cells[0][1]
    for cell in cells[1:]:
        if abs(cell[1] - current_y) < tolerance:
            current_row.append(cell)
        else:
            rows.append(current_row)
            current_row = [cell]
            current_y = cell[1]
    rows.append(current_row)
    return rows


def process_page(image_path: str, output_dir: str, lang: str, mapping: Dict[str, str]) -> str:
    print(f"Processing {os.path.basename(image_path)}...")
    cells, debug_path = extract_table_structure_v4(image_path, output_dir)
    print(f"  Found {len(cells)} cells. Debug: {debug_path}")
    if not cells:
        return ""

    rows = group_rows(cells)
    print(f"  Grouped into {len(rows)} rows.")

    full_img = read_image_robust(image_path)
    if full_img is None:
        return ""

    markdown_lines = []
    for row_idx, row_cells in enumerate(rows):
        row_cells.sort(key=lambda c: c[0])
        row_texts = []
        for cell in row_cells:
            x, y, w, h = cell
            h_img, w_img = full_img.shape[:2]
            margin = 2
            x1 = max(0, x + margin)
            y1 = max(0, y + margin)
            x2 = min(w_img, x + w - margin)
            y2 = min(h_img, y + h - margin)
            cell_img = full_img[y1:y2, x1:x2]
            if cell_img.size == 0:
                row_texts.append("")
                continue
            text = ocr_cell_ensemble(cell_img, lang, mapping)
            row_texts.append(text)
        line = "| " + " | ".join(row_texts) + " |"
        markdown_lines.append(line)
        print(f"    Row {row_idx}: {line[:50]}...")

    output_path = os.path.join(
        output_dir,
        f"{os.path.splitext(os.path.basename(image_path))[0]}_LME.md",
    )
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(markdown_lines))

    return output_path


def collect_images(input_dir: str, pattern: str) -> List[str]:
    import glob

    paths = glob.glob(os.path.join(input_dir, pattern))
    paths.sort()
    return paths


def parse_page_limit(limit: Optional[str], paths: List[str]) -> List[str]:
    if not limit:
        return paths
    if limit.isdigit():
        return paths[: int(limit)]
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Local Multi-process Ensemble OCR")
    parser.add_argument("--input-dir", required=True, help="Directory with page images")
    parser.add_argument("--output-dir", required=True, help="Directory for output markdown")
    parser.add_argument("--pattern", default="page_*.png", help="Glob pattern for page images")
    parser.add_argument("--lang", default="jpn", help="Tesseract language code")
    parser.add_argument("--dictionary", help="Path to dictionary CSV/TSV/JSON for corrections")
    parser.add_argument("--max-pages", help="Process only the first N pages")
    parser.add_argument("--processes", type=int, default=2, help="Number of parallel processes")

    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    mapping = load_dictionary_map(args.dictionary)
    pages = collect_images(args.input_dir, args.pattern)
    pages = parse_page_limit(args.max_pages, pages)

    if not pages:
        raise SystemExit("No matching pages found.")

    results = []
    with ProcessPoolExecutor(max_workers=args.processes) as executor:
        futures = {executor.submit(process_page, page, args.output_dir, args.lang, mapping): page for page in pages}
        for future in as_completed(futures):
            page = futures[future]
            try:
                output_path = future.result()
            except Exception as exc:
                print(f"Failed processing {page}: {exc}")
                continue
            results.append(output_path)

    print("Completed pages:")
    for result in sorted(results):
        print(f"  {result}")


if __name__ == "__main__":
    main()
