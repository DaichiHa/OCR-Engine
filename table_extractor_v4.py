"""
Table Structure Extractor V4 - Line Segment Detector (LSD)
Uses LSD for high-precision line detection, robust against broken/faint lines.
"""

import cv2
import numpy as np
import os
import math

def read_image_robust(path):
    stream = open(path, "rb")
    bytes = bytearray(stream.read())
    numpyarray = np.asarray(bytes, dtype=np.uint8)
    img = cv2.imdecode(numpyarray, cv2.IMREAD_UNCHANGED)
    stream.close()
    return img

def extract_table_structure_v4(image_path, debug_dir):
    filename = os.path.basename(image_path)
    img = read_image_robust(image_path)
    if img is None:
        return [], None

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Create LSD
    lsd = cv2.createLineSegmentDetector(0)
    
    # Detect lines
    lines, width, prec, nfa = lsd.detect(gray)
    
    # Draw detected raw lines for debug
    debug_raw = img.copy()
    lsd.drawSegments(debug_raw, lines)

    # Filter Lines
    horizontal_lines = []
    vertical_lines = []
    
    img_width = img.shape[1]
    img_height = img.shape[0]

    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            dx = x2 - x1
            dy = y2 - y1
            length = math.sqrt(dx*dx + dy*dy)
            
            if length < 30: # Ignore very short noise (tuned down from 50)
                continue
                
            angle = math.degrees(math.atan2(dy, dx))
            # Horizontal: angle near 0 or 180
            if abs(angle) < 5 or abs(angle) > 175:
                # Store (y, x1, x2) - use average Y
                horizontal_lines.append(( (y1+y2)/2, min(x1, x2), max(x1, x2) ))
            
            # Vertical: angle near 90 or -90
            elif abs(abs(angle) - 90) < 5:
                # Store (x, y1, y2)
                vertical_lines.append(( (x1+x2)/2, min(y1, y2), max(y1, y2) ))

    # Cluster Lines
    def cluster_lines(lines, tolerance=10):
        if not lines: return []
        lines.sort(key=lambda x: x[0]) # Sort by main coordinate
        clusters = []
        current = [lines[0][0]]
        
        for i in range(1, len(lines)):
            if lines[i][0] - lines[i-1][0] < tolerance:
                current.append(lines[i][0])
            else:
                clusters.append(int(np.mean(current)))
                current = [lines[i][0]]
        clusters.append(int(np.mean(current)))
        return clusters

    rows = cluster_lines(horizontal_lines, tolerance=10) # Tuned down from 20
    cols = cluster_lines(vertical_lines, tolerance=10) # Tuned down from 20

    print(f"Detected {len(horizontal_lines)} raw H-lines -> {len(rows)} Row Clusters")
    print(f"Detected {len(vertical_lines)} raw V-lines -> {len(cols)} Col Clusters")

    # Filter Grid - Remove edges if necessary or just keep all
    # Usually the first/last detected line is the border.
    
    # Visualize Grid
    debug_grid = img.copy()
    for r in rows:
        cv2.line(debug_grid, (0, r), (img_width, r), (0, 0, 255), 2)
    for c in cols:
        cv2.line(debug_grid, (c, 0), (c, img_height), (0, 255, 0), 2)

    # Calculate Cells (Intersections)
    cells = []
    if len(rows) > 1 and len(cols) > 1:
        for i in range(len(rows) - 1):
            for j in range(len(cols) - 1):
                y1 = rows[i]
                y2 = rows[i+1]
                x1 = cols[j]
                x2 = cols[j+1]
                
                h = y2 - y1
                w = x2 - x1
                
                # Filter logical cell sizes
                if h > 15 and w > 15:
                    cells.append((x1, y1, w, h))

    # Sort cells row by row, then col by col
    # We use a tolerance for 'same row' determination
    cells.sort(key=lambda c: (int(c[1] // 20), c[0]))

    debug_path = os.path.join(debug_dir, f"debug_table_v4_{filename}")
    extension = os.path.splitext(debug_path)[1]
    result, encoded_img = cv2.imencode(extension, debug_grid)
    if result:
        with open(debug_path, "wb") as f:
            f.write(encoded_img)

    return cells, debug_path

if __name__ == "__main__":
    test_page = r"c:\Users\User\Downloads\日本帝國港灣統計_0001\pages\page_011.png"
    debug_dir = r"c:\Users\User\Downloads\日本帝國港灣統計_0001\pages"
    
    print(f"Testing V4 (LSD) extraction on {test_page}...")
    try:
        cells, path = extract_table_structure_v4(test_page, debug_dir)
        print(f"Detected {len(cells)} cells.")
        print(f"Saved debug to {path}")
    except Exception as e:
        print(f"Error: {e}")
