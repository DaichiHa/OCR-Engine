"""
Hybrid Extractor Module
Reusable function for table page processing.
"""

import cv2
import numpy as np
import pytesseract
from PIL import Image

def read_image_robust(path):
    stream = open(path, "rb")
    bytes = bytearray(stream.read())
    numpyarray = np.asarray(bytes, dtype=np.uint8)
    img = cv2.imdecode(numpyarray, cv2.IMREAD_UNCHANGED)
    stream.close()
    return img

def build_tesseract_config(psm, user_words_path=None, user_patterns_path=None, oem=3):
    config = f"--oem {oem} --psm {psm}"
    if user_words_path:
        config += f" --user-words {user_words_path}"
    if user_patterns_path:
        config += f" --user-patterns {user_patterns_path}"
    return config

def compute_ocr_metrics(data, low_conf_threshold=70):
    conf_values = []
    for conf in data.get('conf', []):
        try:
            conf_value = float(conf)
        except (TypeError, ValueError):
            continue
        if conf_value >= 0:
            conf_values.append(conf_value)

    if not conf_values:
        return {'mean_conf': 0.0, 'low_ratio': 1.0, 'count': 0}

    low_count = sum(1 for conf in conf_values if conf < low_conf_threshold)
    mean_conf = float(np.mean(conf_values))
    low_ratio = low_count / float(len(conf_values))
    return {'mean_conf': mean_conf, 'low_ratio': low_ratio, 'count': len(conf_values)}

def detect_table_regions(image, min_area_ratio=0.02, min_aspect_ratio=1.2):
    if image is None:
        return []

    if len(image.shape) == 3 and image.shape[2] > 1:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
    h_lines = cv2.dilate(cv2.erode(bw, h_kernel), h_kernel)
    v_lines = cv2.dilate(cv2.erode(bw, v_kernel), v_kernel)
    lines = cv2.bitwise_or(h_lines, v_lines)

    contours, _ = cv2.findContours(lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return []

    img_area = gray.shape[0] * gray.shape[1]
    table_regions = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        if img_area == 0:
            continue
        if area / img_area < min_area_ratio:
            continue
        if h == 0:
            continue
        aspect_ratio = w / float(h)
        if aspect_ratio < min_aspect_ratio:
            continue
        table_regions.append((x, y, w, h))

    table_regions.sort(key=lambda box: (box[1], box[0]))
    return table_regions

def extract_table_content(image_path, debug_dir=None, table_region=None, user_words_path=None, user_patterns_path=None, return_metrics=False):
    """
    Extracts table content from an image using Hybrid Line/Text approach.
    Returns list of rows (list of strings).
    """
    img = read_image_robust(image_path)
    if img is None:
        return ([], {'mean_conf': 0.0, 'low_ratio': 1.0, 'count': 0}) if return_metrics else []

    if table_region is not None:
        x, y, w, h = table_region
        img = img[y:y + h, x:x + w]

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
    config = build_tesseract_config(6, user_words_path, user_patterns_path)
    
    # Preprocess for Tesseract (Otsu)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    pil_img = Image.fromarray(thresh)
    
    try:
        data = pytesseract.image_to_data(pil_img, lang='jpn', config=config, output_type=pytesseract.Output.DICT)
    except:
        return ([], {'mean_conf': 0.0, 'low_ratio': 1.0, 'count': 0}) if return_metrics else []

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
        
    if return_metrics:
        return table_data, compute_ocr_metrics(data)
    return table_data

def extract_vertical_text(image_path, user_words_path=None, user_patterns_path=None, return_metrics=False):
    """
    Simple function for vertical text pages (1-6)
    """
    img = read_image_robust(image_path)
    if img is None:
        return ("", {'mean_conf': 0.0, 'low_ratio': 1.0, 'count': 0}) if return_metrics else ""
    
    if len(img.shape) == 3 and img.shape[2] > 1:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    pil_img = Image.fromarray(thresh)
    
    config = build_tesseract_config(5, user_words_path, user_patterns_path) # Vertical text block
    text = pytesseract.image_to_string(pil_img, lang='jpn_vert', config=config)
    if return_metrics:
        data = pytesseract.image_to_data(pil_img, lang='jpn_vert', config=config, output_type=pytesseract.Output.DICT)
        return text, compute_ocr_metrics(data)
    return text
