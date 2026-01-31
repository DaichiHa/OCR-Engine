"""
Hybrid Extractor Module
Reusable function for table page processing.
"""

import cv2
import logging
import numpy as np
import os
import pytesseract
from PIL import Image

import ocr_box_utils

logger = logging.getLogger(__name__)

def read_image_robust(path):
    stream = open(path, "rb")
    bytes = bytearray(stream.read())
    numpyarray = np.asarray(bytes, dtype=np.uint8)
    img = cv2.imdecode(numpyarray, cv2.IMREAD_UNCHANGED)
    stream.close()
    return img

def extract_table_content(image_path, debug_dir=None, return_boxes=False, page=None, engine_label="tesseract-table"):
    """
    Extracts table content from an image using Hybrid Line/Text approach.
    Returns list of rows (list of strings).
    """
    img = read_image_robust(image_path)
    if img is None:
        return [] if not return_boxes else ([], [])

    if len(img.shape) == 3 and img.shape[2] > 1:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
    
    # 1. Detect Vertical Lines (LSD)
    lsd = cv2.createLineSegmentDetector(0)
    lines, _, _, _ = lsd.detect(gray)
    
    vertical_lines = []
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            # More lenient filter for vertical lines
            if abs(x1 - x2) < 10 and abs(y1 - y2) > 30: 
                vertical_lines.append(( (x1+x2)/2, min(y1,y2), max(y1,y2) ))
    
    # Cluster Columns
    vertical_lines.sort(key=lambda x: x[0])
    cols = []
    if vertical_lines:
        current = [vertical_lines[0][0]]
        for i in range(1, len(vertical_lines)):
            if vertical_lines[i][0] - vertical_lines[i-1][0] < 15:
                current.append(vertical_lines[i][0])
            else:
                cols.append(int(np.mean(current)))
                current = [vertical_lines[i][0]]
        cols.append(int(np.mean(current)))
    
    # If no columns detected, fallback or assume full width
    if not cols:
        cols = [0, img.shape[1]]

    # 2. Detect Text
    # Use PSM 6 (Sparse text) or PSM 4 (Column data)
    config = r'--oem 3 --psm 6'
    
    # Advanced Preprocessing
    # 1. Denoise (Bilateral filter keeps edges but removes paper grain)
    denoised = cv2.bilateralFilter(gray, 9, 75, 75)
    
    # 2. Adaptive Contrast (CLAHE) - Enhances faint text without blowing out background
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(denoised)

    # 3. Robust Thresholding
    thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    pil_img = Image.fromarray(thresh)
    
    try:
        data = pytesseract.image_to_data(
            pil_img,
            lang='jpn',
            config=config,
            output_type=pytesseract.Output.DICT,
        )
    except Exception as exc:
        logger.exception("Failed to extract table content with Tesseract.", exc_info=exc)
        return [] if not return_boxes else ([], [])

    text_blocks = []
    n_boxes = len(data['level'])
    for i in range(n_boxes):
        text = data['text'][i].strip()
        if text != "":
            (x, y, w, h) = (data['left'][i], data['top'][i], data['width'][i], data['height'][i])
            text_blocks.append({'x': x, 'y': y, 'w': w, 'h': h, 'text': text})

    # 3. Cluster Rows
    text_blocks.sort(key=lambda b: b['y'] + b['h']/2)
    
    rows = []
    if text_blocks:
        current_row = [text_blocks[0]]
        current_y_center = text_blocks[0]['y'] + text_blocks[0]['h']/2
        
        for i in range(1, len(text_blocks)):
            b = text_blocks[i]
            y_center = b['y'] + b['h']/2
            # Row tolerance
            if abs(y_center - current_y_center) < 15:
                current_row.append(b)
            else:
                rows.append(current_row)
                current_row = [b]
                current_y_center = y_center
        rows.append(current_row)

    # 4. Map to Columns
    boundaries = sorted([0] + cols + [img.shape[1]])
    # Remove duplicates if any
    boundaries = sorted(list(set(boundaries)))
    
    table_data = []
    for r_blocks in rows:
        row_cells = [""] * (len(boundaries) - 1)
        for b in r_blocks:
            center_x = b['x'] + b['w']/2
            for i in range(len(boundaries)-1):
                if boundaries[i] <= center_x < boundaries[i+1]:
                    if row_cells[i]:
                        row_cells[i] += " " + b['text']
                    else:
                        row_cells[i] = b['text']
                    break
        table_data.append(row_cells)
        
    if return_boxes:
        if page is None:
            raise ValueError("page is required when return_boxes is True.")
        boxes = ocr_box_utils.tesseract_data_to_boxes(data, page, engine_label)
        return table_data, boxes
    return table_data

def extract_vertical_text(image_path, return_boxes=False, page=None, engine_label="tesseract-vertical"):
    """
    Simple function for vertical text pages (1-6)
    """
    img = read_image_robust(image_path)
    if img is None:
        return "" if not return_boxes else ("", [])
    
    if len(img.shape) == 3 and img.shape[2] > 1:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
    # Advanced Preprocessing for Vertical Text
    denoised = cv2.bilateralFilter(gray, 9, 75, 75)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(denoised)
    
    thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    pil_img = Image.fromarray(thresh)
    
    config = r'--oem 3 --psm 5' # Vertical text block
    text = pytesseract.image_to_string(pil_img, lang='jpn_vert', config=config)
    if return_boxes:
        if page is None:
            raise ValueError("page is required when return_boxes is True.")
        boxes = ocr_box_utils.collect_tesseract_boxes(
            pil_img,
            page=page,
            engine=engine_label,
            config=config,
            lang='jpn_vert',
        )
        return text, boxes
    return text
