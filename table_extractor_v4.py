"""
Table Structure Extractor V4 - Line Segment Detector (LSD)
Uses LSD for high-precision line detection, robust against broken/faint lines.
"""

import math
import os

import cv2
import numpy as np

try:
    import pytesseract
    from PIL import Image
except Exception:
    pytesseract = None
    Image = None


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

    # Handle various image channel layouts robustly
    # keep a BGR copy for drawing/debugging
    # and obtain a gray image for processing
    if img.ndim == 2:
        gray = img
        bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    else:
        # RGBA -> BGR, otherwise assume BGR
        if img.shape[2] == 4:
            bgr = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        else:
            bgr = img.copy()
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    # Create LSD
    lsd = cv2.createLineSegmentDetector(0)

    # Detect lines
    lines, width, prec, nfa = lsd.detect(gray)

    # Draw detected raw lines for debug (use BGR copy)
    debug_raw = bgr.copy()
    lsd.drawSegments(debug_raw, lines)

    # Filter Lines
    horizontal_lines = []
    vertical_lines = []

    img_width = bgr.shape[1]
    img_height = bgr.shape[0]

    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            dx = x2 - x1
            dy = y2 - y1
            length = math.sqrt(dx * dx + dy * dy)

            if length < 30:  # Ignore very short noise (tuned down from 50)
                continue

            angle = math.degrees(math.atan2(dy, dx))
            # Horizontal: angle near 0 or 180
            if abs(angle) < 5 or abs(angle) > 175:
                # Store (y, x1, x2) - use average Y
                horizontal_lines.append(
                    ((y1 + y2) / 2, min(x1, x2), max(x1, x2))
                )

            # Vertical: angle near 90 or -90
            elif abs(abs(angle) - 90) < 5:
                # Store (x, y1, y2)
                vertical_lines.append(
                    ((x1 + x2) / 2, min(y1, y2), max(y1, y2))
                )

    # Cluster Lines
    def cluster_lines(lines, tolerance=10):
        if not lines:
            return []
        lines.sort(key=lambda x: x[0])  # Sort by main coordinate
        clusters = []
        current = [lines[0][0]]

        for i in range(1, len(lines)):
            if lines[i][0] - lines[i - 1][0] < tolerance:
                current.append(lines[i][0])
            else:
                clusters.append(int(np.mean(current)))
                current = [lines[i][0]]
        clusters.append(int(np.mean(current)))
        return clusters

    rows = cluster_lines(horizontal_lines, tolerance=10)  # Tuned down from 20
    cols = cluster_lines(vertical_lines, tolerance=10)  # Tuned down from 20

    print(f"Detected {len(horizontal_lines)} raw H-lines")
    print(f"Row clusters: {len(rows)}")
    print(f"Detected {len(vertical_lines)} raw V-lines")
    print(f"Col clusters: {len(cols)}")

    # Filter Grid - Remove edges if necessary or just keep all
    # Usually the first/last detected line is the border.

    # Visualize Grid (use BGR copy)
    debug_grid = bgr.copy()
    for r in rows:
        cv2.line(debug_grid, (0, r), (img_width, r), (0, 0, 255), 2)
    for c in cols:
        cv2.line(debug_grid, (c, 0), (c, img_height), (0, 255, 0), 2)

    # Calculate Cells (Intersections)
    cells = []
    # initialize grid and median defaults to avoid undefined-name F821
    grid = []
    median_w = 0
    median_h = 0
    if len(rows) > 1 and len(cols) > 1:
        for i in range(len(rows) - 1):
            row_cells = []
            for j in range(len(cols) - 1):
                y1 = rows[i]
                y2 = rows[i + 1]
                x1 = cols[j]
                x2 = cols[j + 1]

                h = y2 - y1
                w = x2 - x1

                row_cells.append([int(x1), int(y1), int(w), int(h)])
            grid.append(row_cells)

    # If grid is empty, skip merging
    # Allow adjusting merge aggressiveness via env var
    # `TBL_MERGE_FACTOR` (float, default 0.6)
    try:
        merge_factor = float(os.environ.get("TBL_MERGE_FACTOR", "0.8"))
    except Exception:
        merge_factor = 0.8

    if grid:
        # Compute typical cell size (median) to detect 'small' cells
        widths = [
            c[2]
            for r in grid
            for c in r
            if c[2] > 0
        ]
        heights = [
            c[3]
            for r in grid
            for c in r
            if c[3] > 0
        ]
        if widths and heights:
            median_w = int(np.median(widths))
            median_h = int(np.median(heights))
        else:
            median_w = median_h = 0

        # Merge small cells: prefer merging to the right.
        # Fallback to merging downward when necessary.
        rows_n = len(grid)
        cols_n = len(grid[0])
        merged = [[False] * cols_n for _ in range(rows_n)]

        # First: merge entire narrow column spans into
        # their right neighbor (or left for last col)
        # This helps when an entire column is consistently
        # too narrow (e.g., index/sep columns)
        col_medians = []
        for j in range(cols_n):
            col_ws = [
                grid[i][j][2]
                for i in range(rows_n)
                if grid[i][j][2] > 0
            ]
            if col_ws:
                col_medians.append(int(np.median(col_ws)))
            else:
                col_medians.append(0)

        # Chain-merge adjacent narrow column groups first
        narrow_flags = [False] * cols_n
        for j in range(cols_n):
            cm = col_medians[j]
            if cm > 0 and median_w > 0 and cm < median_w * merge_factor:
                narrow_flags[j] = True

        # Find runs of adjacent narrow columns and
        # merge each run into an outer neighbor
        j = 0
        while j < cols_n:
            if not narrow_flags[j]:
                j += 1
                continue
            # start of run
            run_start = j
            while j + 1 < cols_n and narrow_flags[j + 1]:
                j += 1
            run_end = j

            # choose target: prefer right of run, else left
            target_j = (
                run_end + 1
                if run_end + 1 < cols_n
                else (run_start - 1 if run_start - 1 >= 0 else None)
            )
            if target_j is not None:
                for i in range(rows_n):
                    # accumulate widths from run into target
                    if merged[i][run_start]:
                        # already merged
                        continue
                    # compute combined bbox of run columns for this row
                    rx = grid[i][run_start][0]
                    ry = grid[i][run_start][1]
                    rw = grid[i][run_start][2]
                    rh = grid[i][run_start][3]
                    for k in range(run_start + 1, run_end + 1):
                        kx, ky, kw, kh = grid[i][k]
                        rx = min(rx, kx)
                        ry = min(ry, ky)
                        rw = rw + kw
                        rh = max(rh, kh)
                    tx, ty, tw, th = grid[i][target_j]
                    new_x = min(rx, tx)
                    new_y = min(ry, ty)
                    new_w = rw + tw
                    new_h = max(rh, th)
                    grid[i][target_j] = [new_x, new_y, new_w, new_h]
                    # mark run slots as merged-away (except target)
                    for k in range(run_start, run_end + 1):
                        if k != target_j:
                            merged[i][k] = True
            j += 1

        # Then perform local merging for residual small cells.
        # Rightward preference, then downward.
        for i in range(rows_n):
            for j in range(cols_n):
                if merged[i][j]:
                    continue
                cell = grid[i][j]
                x, y, w, h = cell
                # ignore degenerate
                if w <= 0 or h <= 0:
                    continue

                small_w = (median_w > 0) and (w < median_w * merge_factor)
                small_h = (median_h > 0) and (h < median_h * merge_factor)

                if small_w and j + 1 < cols_n and not merged[i][j + 1]:
                    # merge with right neighbor
                    nx, ny, nw, nh = grid[i][j + 1]
                    new_x = min(x, nx)
                    new_y = min(y, ny)
                    new_w = w + nw
                    new_h = max(h, nh)
                    grid[i][j] = [new_x, new_y, new_w, new_h]
                    merged[i][j + 1] = True
                    merged[i][j] = False
                elif small_h and i + 1 < rows_n and not merged[i + 1][j]:
                    # merge with cell below
                    nx, ny, nw, nh = grid[i + 1][j]
                    new_x = min(x, nx)
                    new_y = min(y, ny)
                    new_w = max(w, nw)
                    new_h = h + nh
                    grid[i][j] = [new_x, new_y, new_w, new_h]
                    merged[i + 1][j] = True
                    merged[i][j] = False

        # Optional: merge small cells by content density
        # using a lightweight OCR pass.
        # Controlled by env var `TBL_OCR_MERGE` (1 to enable),
        # `TBL_OCR_MIN_CHARS` (int threshold), and
        # `TBL_OCR_LANG` (lang for tesseract, default 'jpn').
        try:
            ocr_merge_enabled = int(os.environ.get("TBL_OCR_MERGE", "1")) == 1
        except Exception:
            ocr_merge_enabled = True

        try:
            ocr_min_chars = int(os.environ.get("TBL_OCR_MIN_CHARS", "2"))
        except Exception:
            ocr_min_chars = 2

        ocr_lang = os.environ.get("TBL_OCR_LANG", "jpn")

        if ocr_merge_enabled and pytesseract is not None and Image is not None:
            for i in range(rows_n):
                for j in range(cols_n):
                    if merged[i][j]:
                        continue
                    x, y, w, h = grid[i][j]
                    if w <= 0 or h <= 0:
                        continue
                    small_w = (median_w > 0) and (w < median_w * merge_factor)
                    small_h = (median_h > 0) and (h < median_h * merge_factor)
                    if not (small_w or small_h):
                        continue

                    # crop region with small padding and run light OCR
                    pad_x = max(2, int(w * 0.05))
                    pad_y = max(2, int(h * 0.05))
                    x0 = max(0, x - pad_x)
                    y0 = max(0, y - pad_y)
                    x1 = min(img_width, x + w + pad_x)
                    y1 = min(img_height, y + h + pad_y)
                    try:
                        crop = bgr[y0:y1, x0:x1]
                        if crop is None or crop.size == 0:
                            continue
                        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
                        pil = Image.fromarray(rgb)
                        # use a compact config for speed
                        txt = pytesseract.image_to_string(
                            pil, lang=ocr_lang, config="--psm 6"
                        )
                        txt = txt.strip()
                    except Exception:
                        txt = ""

                    if len(txt) < ocr_min_chars:
                        # merge into right neighbor if possible, else below
                        if j + 1 < cols_n and not merged[i][j + 1]:
                            nx, ny, nw, nh = grid[i][j + 1]
                            new_x = min(x, nx)
                            new_y = min(y, ny)
                            new_w = w + nw
                            new_h = max(h, nh)
                            grid[i][j + 1] = [new_x, new_y, new_w, new_h]
                            merged[i][j] = True
                        elif i + 1 < rows_n and not merged[i + 1][j]:
                            nx, ny, nw, nh = grid[i + 1][j]
                            new_x = min(x, nx)
                            new_y = min(y, ny)
                            new_w = max(w, nw)
                            new_h = h + nh
                            grid[i + 1][j] = [new_x, new_y, new_w, new_h]
                            merged[i][j] = True

        # Flatten grid into cells, skipping merged-away slots
        for i in range(rows_n):
            for j in range(cols_n):
                if merged[i][j]:
                    continue
                x, y, w, h = grid[i][j]
                # Filter logical cell sizes post-merge
                if h > 15 and w > 15:
                    cells.append((x, y, w, h))

        # Re-cluster cells after merging to coalesce fragmented row spans
    # We group by vertical center and then merge
    # horizontally-close cells within each row cluster.
    # Allow tuning of row tolerance and horizontal gap via env vars:
    # `TBL_ROW_TOL_FACTOR` (multiplier of median_h, default 0.5)
    # and `TBL_H_GAP` (pixels, default 15)
    try:
        row_tol_factor = float(os.environ.get("TBL_ROW_TOL_FACTOR", "0.5"))
    except Exception:
        row_tol_factor = 0.5
    try:
        h_gap = int(os.environ.get("TBL_H_GAP", "15"))
    except Exception:
        h_gap = 15

    final_cells = []
    if cells:
        centers = [(c[1] + c[3] / 2.0, idx) for idx, c in enumerate(cells)]
        centers.sort()
        # tolerance based on median_h
        row_tol = (
            max(12, int(median_h * row_tol_factor)) if median_h > 0 else 20
        )
        groups = []
        current = [centers[0][1]]
        for k in range(1, len(centers)):
            if centers[k][0] - centers[k - 1][0] < row_tol:
                current.append(centers[k][1])
            else:
                groups.append(current)
                current = [centers[k][1]]
        groups.append(current)

        for g in groups:
            row_cells = [cells[idx] for idx in g]
            # sort by x
            row_cells.sort(key=lambda c: c[0])
            # merge horizontally-close fragments
            merged_row = []
            cur = list(row_cells[0])
            for c in row_cells[1:]:
                x, y, w, h = c
                cur_x, cur_y, cur_w, cur_h = cur
                gap = x - (cur_x + cur_w)
                if gap <= h_gap:
                    # merge
                    new_x = cur_x
                    new_y = min(cur_y, y)
                    new_w = (x + w) - cur_x
                    new_h = max(cur_h, h)
                    cur = [new_x, new_y, new_w, new_h]
                else:
                    merged_row.append(tuple(cur))
                    cur = [x, y, w, h]
            merged_row.append(tuple(cur))
            final_cells.extend(merged_row)
    else:
        final_cells = []

    # Sort final cells row by row, then col by col
    final_cells.sort(key=lambda c: (int(c[1] // 20), c[0]))
    cells = final_cells

    debug_path = os.path.join(debug_dir, f"debug_table_v4_{filename}")
    extension = os.path.splitext(debug_path)[1]
    result, encoded_img = cv2.imencode(extension, debug_grid)
    if result:
        with open(debug_path, "wb") as f:
            f.write(encoded_img)

    return cells, debug_path


if __name__ == "__main__":
    test_page = (
        "c:\\Users\\User\\Downloads\\日本帝國港灣統計_0001\\pages\\"
        + "page_011.png"
    )
    debug_dir = (
        "c:\\Users\\User\\Downloads\\日本帝國港灣統計_0001\\"
        + "pages"
    )

    print(f"Testing V4 (LSD) extraction on {test_page}...")
    try:
        cells, path = extract_table_structure_v4(test_page, debug_dir)
        print(f"Detected {len(cells)} cells.")
        print(f"Saved debug to {path}")
    except Exception as e:
        print(f"Error: {e}")
