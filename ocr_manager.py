"""
OCR Manager
Orchestrates the table extraction and cell-by-cell OCR process.
Generates Markdown output.
"""

import os

import cv2
import pytesseract
from PIL import Image

from table_extractor_v4 import extract_table_structure_v4, read_image_robust


def ocr_cell(img_path, cell_box, margin=2):
    """
    Crop and OCR a single cell.
    """
    x, y, w, h = cell_box

    # Load full image
    full_img = read_image_robust(img_path)
    if full_img is None:
        return ""

    # Crop with slight margin removal to avoid grid lines
    h_img, w_img = full_img.shape[:2]
    x1 = max(0, x + margin)
    y1 = max(0, y + margin)
    x2 = min(w_img, x + w - margin)
    y2 = min(h_img, y + h - margin)

    cell_img = full_img[y1:y2, x1:x2]

    if cell_img.size == 0:
        return ""

    # Convert to PIL for Tesseract
    # Preprocessing: handle different channel layouts then Grayscale -> Threshold
    if cell_img.ndim == 2:
        gray = cell_img
    else:
        if cell_img.shape[2] == 4:
            cell_bgr = cv2.cvtColor(cell_img, cv2.COLOR_RGBA2BGR)
        else:
            cell_bgr = cell_img
        gray = cv2.cvtColor(cell_bgr, cv2.COLOR_BGR2GRAY)
    # Simple Otsu is usually best for high-contrast text in cells
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

    pil_img = Image.fromarray(thresh)

    # OCR Config: Assume single line of text (psm 7) or single word (psm 8)
    # Use Japanese model
    config = r"--oem 3 --psm 7"
    text = pytesseract.image_to_string(pil_img, lang="jpn", config=config)

    return (
        text.strip().replace("\n", " ").replace("|", "")
    )  # Remove pipe to avoid markdown break


def process_page(image_path, output_dir):
    """
    Process a single page: Extract Table -> OCR Cells -> Markdown
    """
    print(f"Processing {os.path.basename(image_path)}...")

    # 1. Extract Structure
    cells, debug_path = extract_table_structure_v4(image_path, output_dir)
    print(f"  Found {len(cells)} cells. Debug: {debug_path}")

    if not cells:
        return ""

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
            text = ocr_cell(image_path, cell)
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

    with open(
        r"c:\Users\User\Downloads\日本帝國港灣統計_0001\page_011_ocr.md",
        "w",
        _encoding="utf-8",
    ) as f:
        f.write(md)
