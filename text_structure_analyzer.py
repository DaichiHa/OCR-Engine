"""
Hybrid Table Structure Analyzer
Uses Vertical Lines (LSD) + Text Position (Tesseract) to reconstruct tables
Robust against missing horizontal lines.
"""

import cv2
import numpy as np
import os
import math
import pytesseract
from PIL import Image

import ocr_box_utils

def read_image_robust(path):
    stream = open(path, "rb")
    bytes = bytearray(stream.read())
    numpyarray = np.asarray(bytes, dtype=np.uint8)
    img = cv2.imdecode(numpyarray, cv2.IMREAD_UNCHANGED)
    stream.close()
    return img

def analyze_hybrid_structure(image_path, debug_dir, return_boxes=False, page=None, engine_label="tesseract-structure"):
    filename = os.path.basename(image_path)
    img = read_image_robust(image_path)
    if img is None:
        return None

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 1. Detect Vertical Lines using LSD
    lsd = cv2.createLineSegmentDetector(0)
    lines, _, _, _ = lsd.detect(gray)
    
    vertical_lines = []
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if abs(x1 - x2) < 5 and abs(y1 - y2) > 50: # Verticalish and long enough
                vertical_lines.append(( (x1+x2)/2, min(y1,y2), max(y1,y2) ))
    
    # Cluster Vertical Lines (Columns)
    vertical_lines.sort(key=lambda x: x[0])
    cols = []
    if vertical_lines:
        current = [vertical_lines[0][0]]
        for i in range(1, len(vertical_lines)):
            if vertical_lines[i][0] - vertical_lines[i-1][0] < 20:
                current.append(vertical_lines[i][0])
            else:
                cols.append(int(np.mean(current)))
                current = [vertical_lines[i][0]]
        cols.append(int(np.mean(current)))
    
    print(f"Detected {len(cols)} columns at x={cols}")

    # 2. Detect Text Blocks using Tesseract (PSM 6: Sparse text)
    # We want bounding boxes for every word/character
    # Using image_to_data
    
    custom_config = r'--oem 3 --psm 6'
    pil_img = Image.fromarray(gray)
    data = pytesseract.image_to_data(
        pil_img,
        lang='jpn',
        config=custom_config,
        output_type=pytesseract.Output.DICT,
    )
    
    # Filter valid text blocks
    text_blocks = []
    n_boxes = len(data['level'])
    for i in range(n_boxes):
        if data['text'][i].strip() != "":
            (x, y, w, h) = (data['left'][i], data['top'][i], data['width'][i], data['height'][i])
            text_blocks.append({'x': x, 'y': y, 'w': w, 'h': h, 'text': data['text'][i]})

    # 3. Assign Text to Rows based on Y-coordinate clustering
    # Sort by Y center
    text_blocks.sort(key=lambda b: b['y'] + b['h']/2)
    
    rows = []
    if text_blocks:
        current_row = [text_blocks[0]]
        current_y_center = text_blocks[0]['y'] + text_blocks[0]['h']/2
        
        for i in range(1, len(text_blocks)):
            b = text_blocks[i]
            y_center = b['y'] + b['h']/2
            
            # If Y centers are close (within 10px), same row
            if abs(y_center - current_y_center) < 15:
                current_row.append(b)
            else:
                rows.append(current_row)
                current_row = [b]
                current_y_center = y_center
        rows.append(current_row)
    
    print(f"Detected {len(rows)} text rows using Tesseract.")

    # 4. Generate Markdown
    # Use cols to map text to table columns
    # cols = [x1, x2, x3...] defines boundaries? No, cols are lines.
    # So boundaries are bins: (-inf, col1), (col1, col2), ... (coln, inf)
    
    csv_rows = []
    
    # Add implicit boundaries: 0 and Width
    boundaries = [0] + cols + [img.shape[1]]
    
    for r_idx, row_blocks in enumerate(rows):
        # Create empty cells
        row_content = [""] * (len(boundaries) - 1)
        
        for b in row_blocks:
            b_x_center = b['x'] + b['w']/2
            
            # Find which column bin this block belongs to
            for c_idx in range(len(boundaries) - 1):
                if boundaries[c_idx] <= b_x_center < boundaries[c_idx+1]:
                    # Append text to that cell
                    if row_content[c_idx]:
                        row_content[c_idx] += " " + b['text']
                    else:
                        row_content[c_idx] = b['text']
                    break
        
        csv_rows.append(row_content)

    # 5. Visualize
    debug_img = img.copy()
    for c in cols:
        cv2.line(debug_img, (c, 0), (c, img.shape[0]), (0, 255, 0), 2)
    
    for b in text_blocks:
        cv2.rectangle(debug_img, (b['x'], b['y']), (b['x']+b['w'], b['y']+b['h']), (0, 0, 255), 1)

    debug_path = os.path.join(debug_dir, f"debug_hybrid_{filename}")
    extension = os.path.splitext(debug_path)[1]
    result, encoded_img = cv2.imencode(extension, debug_img)
    if result:
        with open(debug_path, "wb") as f:
            f.write(encoded_img)

    if return_boxes:
        if page is None:
            raise ValueError("page is required when return_boxes is True.")
        boxes = ocr_box_utils.tesseract_data_to_boxes(data, page, engine_label)
        return csv_rows, debug_path, boxes
    return csv_rows, debug_path


def collect_tesseract_boxes(image_path, page, engine_label="tesseract-structure"):
    img = read_image_robust(image_path)
    if img is None:
        return []
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    pil_img = Image.fromarray(gray)
    custom_config = r'--oem 3 --psm 6'
    return ocr_box_utils.collect_tesseract_boxes(
        pil_img,
        page=page,
        engine=engine_label,
        config=custom_config,
        lang='jpn',
    )

if __name__ == "__main__":
    test_page = r"c:\Users\User\Downloads\日本帝國港灣統計_0001\pages\page_011.png"
    debug_dir = r"c:\Users\User\Downloads\日本帝國港灣統計_0001\pages"
    
    print(f"Testing Hybrid Extraction on {test_page}...")
    rows, path = analyze_hybrid_structure(test_page, debug_dir)
    
    print(f"Generated {len(rows)} rows.")
    print("\nPreview:")
    for row in rows[:5]:
        print("| " + " | ".join(row) + " |")
        
    # Save md
    with open(r"c:\Users\User\Downloads\日本帝國港灣統計_0001\page_011_hybrid.md", "w", encoding="utf-8") as f:
        for row in rows:
            f.write("| " + " | ".join(row) + " |\n")
