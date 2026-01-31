"""
Table Structure Extractor V2 - Robust Line Detection
Specially tuned for historical documents with broken/faint lines.
"""

import cv2
import numpy as np
import os

def read_image_robust(path):
    stream = open(path, "rb")
    bytes = bytearray(stream.read())
    numpyarray = np.asarray(bytes, dtype=np.uint8)
    img = cv2.imdecode(numpyarray, cv2.IMREAD_UNCHANGED)
    stream.close()
    return img

def extract_table_structure_v2(image_path, debug_dir):
    filename = os.path.basename(image_path)
    img = read_image_robust(image_path)
    if img is None:
        print(f"Failed to load {image_path}")
        return 0, None

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 1. Binarization - Use simplistic thresholding to catch faint lines
    # Invert so lines are white, background is black
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, 
                                 cv2.THRESH_BINARY_INV, 15, 5) # Block size 15, C=5

    # 2. Extract Lines using Morphology
    # Use smaller kernels to catch broken lines
    scale = 20 # Play with this. 20 means kernel is 1/20th of dimension. 
    # For a 2000px image, 1/20 is 100px. That's good for main grid lines.
    
    horizontal_size = img.shape[1] // scale
    vertical_size = img.shape[0] // scale

    # Detection of horizontal lines
    horizontal_structure = cv2.getStructuringElement(cv2.MORPH_RECT, (horizontal_size, 1))
    horizontal = cv2.erode(thresh, horizontal_structure)
    horizontal = cv2.dilate(horizontal, horizontal_structure)
    
    # Detection of vertical lines
    vertical_structure = cv2.getStructuringElement(cv2.MORPH_RECT, (1, vertical_size))
    vertical = cv2.erode(thresh, vertical_structure)
    vertical = cv2.dilate(vertical, vertical_structure)
    
    # 3. Combine Grid
    # Dilate lines slightly to close gaps
    horizontal = cv2.dilate(horizontal, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 1)))
    vertical = cv2.dilate(vertical, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 5)))
    
    mask = horizontal + vertical
    
    # 4. Find Contours (Cells)
    # Find contours on the mask
    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    # Sort contours (top-to-bottom, left-to-right logic needs to be applied later)
    # Here we just filter and count
    
    bounding_boxes = []
    debug_img = img.copy()
    
    min_area = 500 # Ignore noise
    max_area = (img.shape[0] * img.shape[1]) * 0.9 # Ignore whole page box

    cells_found = 0
    for c in contours:
        area = cv2.contourArea(c)
        if area > min_area and area < max_area:
            x, y, w, h = cv2.boundingRect(c)
            # Filter distinct cell shapes (not too thin lines)
            if w > 20 and h > 10:
                bounding_boxes.append((x, y, w, h))
                cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 0, 255), 2)
                cells_found += 1

    # Save debug
    debug_path = os.path.join(debug_dir, f"debug_table_v2_{filename}")
    extension = os.path.splitext(debug_path)[1]
    result, encoded_img = cv2.imencode(extension, debug_img)
    if result:
        with open(debug_path, "wb") as f:
            f.write(encoded_img)

    return cells_found, debug_path

if __name__ == "__main__":
    test_page = r"c:\Users\User\Downloads\日本帝國港灣統計_0001\pages\page_011.png"
    debug_dir = r"c:\Users\User\Downloads\日本帝國港灣統計_0001\pages"
    
    print(f"Testing V2 extraction on {test_page}...")
    count, path = extract_table_structure_v2(test_page, debug_dir)
    print(f"Detected {count} cells.")
    print(f"Saved debug to {path}")
