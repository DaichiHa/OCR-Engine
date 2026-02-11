"""
Table Structure Extractor V3 - Projection Profile Method
Detects table grid by sum of pixels along rows/cols.
Robust for faint lines if the layout is aligned.
"""

import os

import cv2
import numpy as np


def read_image_robust(path):
    stream = open(path, "rb")
    bytes = bytearray(stream.read())
    numpyarray = np.asarray(bytes, dtype=np.uint8)
    img = cv2.imdecode(numpyarray, cv2.IMREAD_UNCHANGED)
    stream.close()
    return img


def extract_table_structure_v3(image_path, debug_dir):
    filename = os.path.basename(image_path)
    img = read_image_robust(image_path)
    if img is None:
        print(f"Failed to load {image_path}")
        return 0, None

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Adaptive threshold for clean binary
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 5
    )

    height, width = binary.shape

    # 1. Horizontal Projection
    horizontal_proj = np.sum(binary, axis=1)
    # Normalize
    horizontal_proj = horizontal_proj / 255

    # Threshold for detection (line candidate if > width * 0.2 pixels are black/white)
    # Since we inverted, relevant pixels are white (255)
    # Lines should be peaks

    row_candidates = np.where(horizontal_proj > (width * 0.5))[0]

    # Clean up adjacent lines (group close peaks)
    rows = []
    if len(row_candidates) > 0:
        current_group = [row_candidates[0]]
        for i in range(1, len(row_candidates)):
            if (
                row_candidates[i] - row_candidates[i - 1] < 10
            ):  # If lines are within 10px
                current_group.append(row_candidates[i])
            else:
                rows.append(int(np.mean(current_group)))
                current_group = [row_candidates[i]]
        rows.append(int(np.mean(current_group)))

    # 2. Vertical Projection
    vertical_proj = np.sum(binary, axis=0)
    vertical_proj = vertical_proj / 255

    # Vertical lines are often thinner/fainter, verify threshold
    col_candidates = np.where(vertical_proj > (height * 0.1))[
        0
    ]  # Lower threshold

    cols = []
    if len(col_candidates) > 0:
        current_group = [col_candidates[0]]
        for i in range(1, len(col_candidates)):
            if (
                col_candidates[i] - col_candidates[i - 1] < 20
            ):  # If lines are within 20px
                current_group.append(col_candidates[i])
            else:
                cols.append(int(np.mean(current_group)))
                current_group = [col_candidates[i]]
        cols.append(int(np.mean(current_group)))

    print(
        f"Detected {len(rows)} potential rows and {len(cols)} potential cols"
    )

    # 3. Form Grid
    debug_img = img.copy()
    cells = []

    # Draw Lines
    for r in rows:
        cv2.line(debug_img, (0, r), (width, r), (0, 0, 255), 2)
    for c in cols:
        cv2.line(debug_img, (c, 0), (c, height), (0, 255, 0), 2)

    # Extract Cells (Gaps between lines)
    # We need to find intersections
    # Simple approach: Iterate row/col intervals

    if len(rows) > 1 and len(cols) > 1:
        for i in range(len(rows) - 1):
            for j in range(len(cols) - 1):
                y1 = rows[i]
                y2 = rows[i + 1]
                x1 = cols[j]
                x2 = cols[j + 1]

                h_cell = y2 - y1
                w_cell = x2 - x1

                # Filter noise
                if h_cell > 10 and w_cell > 10:
                    cells.append((x1, y1, w_cell, h_cell))
                    # Draw cell center
                    # cv2.circle(debug_img, (x1 + w_cell//2, y1 + h_cell//2), 5, (255, 0, 0), -1)

    debug_path = os.path.join(debug_dir, f"debug_table_v3_{filename}")
    extension = os.path.splitext(debug_path)[1]
    result, encoded_img = cv2.imencode(extension, debug_img)
    if result:
        with open(debug_path, "wb") as f:
            f.write(encoded_img)

    return len(cells), debug_path


if __name__ == "__main__":
    test_page = (
        r"c:\Users\User\Downloads\日本帝國港灣統計_0001\pages\page_011.png"
    )
    debug_dir = r"c:\Users\User\Downloads\日本帝國港灣統計_0001\pages"

    print(f"Testing V3 extraction on {test_page}...")
    try:
        count, path = extract_table_structure_v3(test_page, debug_dir)
        print(f"Detected {count} cells.")
        print(f"Saved debug to {path}")
    except Exception as e:
        print(f"Error: {e}")
