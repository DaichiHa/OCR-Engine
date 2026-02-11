"""
Table Structure Extractor for Japanese Historical Statistics
detects grid lines and extracts cells for individual OCR
"""

import os

import cv2
import numpy as np


def extract_table_structure(image_path, debug_dir):
    """
    Detects horizontal and vertical lines to identify table cells.
    Returns a list of cell coordinates and saves a debug image.
    """
    name = os.path.basename(image_path)
    img = cv2.imread(image_path)
    if img is None:
        # Use numpy logic for non-ascii paths if needed, but assuming standard path for test
        stream = open(image_path, "rb")
        bytes = bytearray(stream.read())
        numpyarray = np.asarray(bytes, dtype=np.uint8)
        img = cv2.imdecode(numpyarray, cv2.IMREAD_UNCHANGED)
        stream.close()

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Binary thresholding (inverted) - try simple Otsu first for better global line detection
    # thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    #                              cv2.THRESH_BINARY_INV, 11, 2)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    # Check content
    white_pixels = cv2.countNonZero(thresh)
    print(f"Threshold white pixels: {white_pixels}")

    # Detect Horizontal Lines
    # Kernel length proportional to image width - make it smaller to catch shorter lines
    horizontal_kernel_len = np.array(img).shape[1] // 50
    horizontal_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, (horizontal_kernel_len, 1)
    )
    detect_horizontal = cv2.morphologyEx(
        thresh, cv2.MORPH_OPEN, horizontal_kernel, iterations=2
    )

    # Detect Vertical Lines
    vertical_kernel_len = np.array(img).shape[0] // 50
    vertical_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, (1, vertical_kernel_len)
    )
    detect_vertical = cv2.morphologyEx(
        thresh, cv2.MORPH_OPEN, vertical_kernel, iterations=2
    )

    # Combine lines
    table_mask = cv2.addWeighted(detect_horizontal, 0.5, detect_vertical, 0.5, 0.0)
    table_mask = cv2.threshold(table_mask, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[
        1
    ]

    # Find Contours (Cells)
    contours, hierarchy = cv2.findContours(
        table_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
    )

    # Filter contours by size to remove noise
    cells = []
    min_area = 100  # Adjust based on resolution

    debug_img = img.copy()

    for c in contours:
        area = cv2.contourArea(c)
        if area > min_area:
            x, y, w, h = cv2.boundingRect(c)
            # Filter out very thin/long boxes that might be lines themselves
            if w > 10 and h > 10:
                cells.append((x, y, w, h))
                cv2.rectangle(debug_img, (x, y), (x + w, y + h), (0, 0, 255), 2)

    # Save debug image
    debug_path = os.path.join(debug_dir, f"table_debug_{name}")
    extension = os.path.splitext(debug_path)[1]
    result, encoded_img = cv2.imencode(extension, debug_img)
    if result:
        with open(debug_path, "wb") as f:
            f.write(encoded_img)

    return len(cells), debug_path


if __name__ == "__main__":
    test_page = r"c:\Users\User\Downloads\日本帝國港灣統計_0001\pages\page_011.png"
    debug_dir = r"c:\Users\User\Downloads\日本帝國港灣統計_0001\pages"

    print(f"Extracting table from {test_page}...")
    count, debug_path = extract_table_structure(test_page, debug_dir)

    print(f"Detected {count} cells.")
    print(f"Debug image saved to: {debug_path}")
