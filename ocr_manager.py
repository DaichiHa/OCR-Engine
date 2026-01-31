"""
OCR Manager
Orchestrates the table extraction and cell-by-cell OCR process.
Generates Markdown output.
"""

import cv2
import pytesseract
from PIL import Image
import os
import concurrent.futures
from table_extractor_v4 import extract_table_structure_v4, read_image_robust
from ocr_text_utils import build_tesseract_config, normalize_kyuujitai


def ocr_cell(
    full_gray,
    cell_box,
    margin=2,
    lang="jpn",
    psm=7,
    oem=3,
    normalize_text=True,
    tesseract_config_dir=None,
    user_words_path=None,
    user_patterns_path=None,
):
    """
    Crop and OCR a single cell.
    """
    x, y, w, h = cell_box

    if full_gray is None:
        return ""

    # Crop with slight margin removal to avoid grid lines
    h_img, w_img = full_gray.shape[:2]
    x1 = max(0, x + margin)
    y1 = max(0, y + margin)
    x2 = min(w_img, x + w - margin)
    y2 = min(h_img, y + h - margin)

    cell_img = full_gray[y1:y2, x1:x2]

    if cell_img.size == 0:
        return ""

    # Convert to PIL for Tesseract
    # Preprocessing: Threshold
    # Simple Otsu is usually best for high-contrast text in cells
    thresh = cv2.threshold(cell_img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    pil_img = Image.fromarray(thresh)

    # OCR Config: Assume single line of text (psm 7) or single word (psm 8)
    # Use Japanese model
    base_config = f'--oem {oem} --psm {psm}'
    config = build_tesseract_config(
        base_config,
        config_dir=tesseract_config_dir,
        user_words_path=user_words_path,
        user_patterns_path=user_patterns_path,
    )
    text = pytesseract.image_to_string(pil_img, lang=lang, config=config)
    cleaned_text = text.strip().replace('\n', ' ').replace('|', '')

    return normalize_kyuujitai(cleaned_text, enabled=normalize_text)


def process_page(
    image_path,
    output_dir,
    lang="jpn",
    psm=7,
    oem=3,
    normalize_text=True,
    tesseract_config_dir=None,
    user_words_path=None,
    user_patterns_path=None,
):
    """
    Process a single page: Extract Table -> OCR Cells -> Markdown
    """
    print(f"Processing {os.path.basename(image_path)}...")

    # 1. Extract Structure
    cells, debug_path = extract_table_structure_v4(image_path, output_dir)
    print(f"  Found {len(cells)} cells. Debug: {debug_path}")

    if not cells:
        return ""

    full_img = read_image_robust(image_path)
    if full_img is None:
        return ""
    full_gray = cv2.cvtColor(full_img, cv2.COLOR_BGR2GRAY)

    # Group into rows
    rows = []
    if cells:
        current_row = [cells[0]]
        current_y = cells[0][1]

        for i in range(1, len(cells)):
            cell = cells[i]
            # If y difference is small (e.g. < 20px), consider same row
            if abs(cell[1] - current_y) < 20:
                current_row.append(cell)
            else:
                rows.append(current_row)
                current_row = [cell]
                current_y = cell[1]
        rows.append(current_row)

    print(f"  Grouped into {len(rows)} rows.")

    # Process Rows
    markdown_lines = []

    for row_idx, row_cells in enumerate(rows):
        # Sort by X within row (should already be sorted but safe to ensure)
        row_cells.sort(key=lambda c: c[0])

        row_texts = []
        for cell in row_cells:
            text = ocr_cell(
                full_gray,
                cell,
                lang=lang,
                psm=psm,
                oem=oem,
                normalize_text=normalize_text,
                tesseract_config_dir=tesseract_config_dir,
                user_words_path=user_words_path,
                user_patterns_path=user_patterns_path,
            )
            row_texts.append(text)

        line = "| " + " | ".join(row_texts) + " |"
        markdown_lines.append(line)
        print(f"    Row {row_idx}: {line[:50]}...")

    return "\n".join(markdown_lines)


if __name__ == "__main__":
    test_page = r"c:\Users\User\Downloads\日本帝國港灣統計_0001\pages\page_011.png"
    output_dir = r"c:\Users\User\Downloads\日本帝國港灣統計_0001\pages"

    print("Starting OCR Manager Test...")
    md = process_page(test_page, output_dir)

    print("\n" + "=" * 50)
    print("Generated Markdown:")
    print("=" * 50)
    print(md)

    with open(r"c:\Users\User\Downloads\日本帝國港灣統計_0001\page_011_ocr.md", "w", encoding="utf-8") as f:
        f.write(md)
