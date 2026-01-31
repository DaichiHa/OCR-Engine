"""
Advanced OCR Script for Japanese Historical Document
Uses OpenCV for advanced preprocessing and Tesseract for OCR
"""

import cv2
import numpy as np
import pytesseract
from PIL import Image
import os

def save_debug_image(image, output_path):
    """
    Save image using cv2.imencode to handle non-ASCII paths.
    """
    if output_path is None:
        return
    extension = os.path.splitext(output_path)[1]
    result, encoded_img = cv2.imencode(extension, image)
    if result:
        with open(output_path, "wb") as f:
            f.write(encoded_img)

def order_points(pts):
    """
    Order points in the following order: top-left, top-right, bottom-right, bottom-left.
    """
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def find_document_corners(gray):
    """
    Find document corners using contours.
    """
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    for cnt in contours[:5]:
        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)
        if len(approx) == 4:
            return approx.reshape(4, 2)

    if contours:
        rect = cv2.minAreaRect(contours[0])
        box = cv2.boxPoints(rect)
        return box.astype("float32")
    return None

def apply_perspective_correction(image, debug_dir=None, debug_prefix="debug"):
    """
    Apply perspective correction if document corners are detected.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    corners = find_document_corners(gray)
    if corners is None:
        return image, False

    rect = order_points(corners)
    (tl, tr, br, bl) = rect

    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    max_width = int(max(width_a, width_b))

    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_height = int(max(height_a, height_b))

    dst = np.array([
        [0, 0],
        [max_width - 1, 0],
        [max_width - 1, max_height - 1],
        [0, max_height - 1]
    ], dtype="float32")

    matrix = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, matrix, (max_width, max_height))

    if debug_dir:
        save_debug_image(
            warped,
            os.path.join(debug_dir, f"{debug_prefix}_perspective.png")
        )
    return warped, True

def estimate_skew_angle(gray):
    """
    Estimate skew angle using Hough lines, fallback to minAreaRect.
    """
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, minLineLength=100, maxLineGap=10)
    angles = []

    if lines is not None:
        for x1, y1, x2, y2 in lines[:, 0]:
            if x2 == x1:
                continue
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            if -45 <= angle <= 45:
                angles.append(angle)

    if angles:
        return float(np.median(angles))

    coords = np.column_stack(np.where(gray < 255))
    if len(coords) == 0:
        return 0.0
    rect = cv2.minAreaRect(coords)
    angle = rect[-1]
    if angle < -45:
        angle = 90 + angle
    return float(angle)

def deskew_image(image, angle, debug_dir=None, debug_prefix="debug"):
    """
    Rotate image to correct skew.
    """
    if abs(angle) < 0.1:
        return image, False
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(image, matrix, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

    if debug_dir:
        save_debug_image(
            rotated,
            os.path.join(debug_dir, f"{debug_prefix}_deskew.png")
        )
    return rotated, True

def estimate_curvature_strength(binary):
    """
    Estimate curvature strength based on top edge deviation.
    """
    _, w = binary.shape
    xs = []
    ys = []
    for x in range(w):
        col = binary[:, x]
        ys_nonzero = np.where(col > 0)[0]
        if ys_nonzero.size:
            xs.append(x)
            ys.append(ys_nonzero[0])
    if len(xs) < max(50, w * 0.3):
        return 0.0, None, None

    xs = np.array(xs)
    ys = np.array(ys)
    linear_fit = np.polyfit(xs, ys, 1)
    quadratic_fit = np.polyfit(xs, ys, 2)
    linear_vals = np.polyval(linear_fit, xs)
    quad_vals = np.polyval(quadratic_fit, xs)
    curvature = float(np.mean(np.abs(quad_vals - linear_vals)))
    return curvature, quadratic_fit, linear_fit

def apply_curvature_correction(image, binary, strength_threshold=3.0, enabled=False, debug_dir=None, debug_prefix="debug"):
    """
    Apply curvature correction based on quadratic fit of the top edge.
    """
    curvature, quad_fit, linear_fit = estimate_curvature_strength(binary)
    if not enabled or quad_fit is None or linear_fit is None or curvature < strength_threshold:
        return image, False, curvature

    h, w = binary.shape
    xs = np.arange(w)
    quad_vals = np.polyval(quad_fit, xs)
    linear_vals = np.polyval(linear_fit, xs)
    shift = quad_vals - linear_vals

    map_x, map_y = np.meshgrid(np.arange(w), np.arange(h))
    for x in range(w):
        map_y[:, x] = np.clip(map_y[:, x] + shift[x], 0, h - 1)

    corrected = cv2.remap(image, map_x.astype(np.float32), map_y.astype(np.float32), cv2.INTER_LINEAR)

    if debug_dir:
        save_debug_image(
            corrected,
            os.path.join(debug_dir, f"{debug_prefix}_curvature.png")
        )
    return corrected, True, curvature

def preprocess_image_advanced(image_path, debug_save_dir=None, apply_curvature=False, curvature_threshold=3.0):
    """
    Apply advanced preprocessing using OpenCV
    """
    # Read image using numpy to handle non-ASCII paths
    # img = cv2.imread(image_path)
    stream = open(image_path, "rb")
    bytes = bytearray(stream.read())
    numpyarray = np.asarray(bytes, dtype=np.uint8)
    img = cv2.imdecode(numpyarray, cv2.IMREAD_UNCHANGED)
    stream.close()
    
    if img is None:
        raise ValueError(f"Could not read image: {image_path}")

    if debug_save_dir:
        os.makedirs(debug_save_dir, exist_ok=True)
        save_debug_image(
            img,
            os.path.join(debug_save_dir, "debug_original.png")
        )

    # Perspective correction
    img, _ = apply_perspective_correction(img, debug_dir=debug_save_dir, debug_prefix="debug")

    # Gray scale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Skew correction
    angle = estimate_skew_angle(gray)
    img, _ = deskew_image(img, angle, debug_dir=debug_save_dir, debug_prefix="debug")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Denoise (Non-local Means Denoising) - Good for removing paper grain
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

    # Adaptive Thresholding (Gaussian C) - Handles uneven lighting/aging
    # Block size 11, C=2 (standard starting points)
    thresh = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                 cv2.THRESH_BINARY, 11, 2)

    # Curvature correction (optional, for strongly curved pages)
    img_after_curvature, curvature_applied, _ = apply_curvature_correction(
        img,
        thresh,
        strength_threshold=curvature_threshold,
        enabled=apply_curvature,
        debug_dir=debug_save_dir,
        debug_prefix="debug"
    )
    if curvature_applied:
        gray = cv2.cvtColor(img_after_curvature, cv2.COLOR_BGR2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
        thresh = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )

    # Morphological operations to clean up dots/noise
    kernel = np.ones((1, 1), np.uint8) # Very small kernel to avoid damaging thin strokes
    
    # Slight dilation to connect broken characters (common in old print)
    # dilate = cv2.dilate(thresh, kernel, iterations=1)
    
    # For debugging - save using cv2.imencode for non-ASCII paths
    if debug_save_dir:
        save_debug_image(
            thresh,
            os.path.join(debug_save_dir, "debug_preprocessed.png")
        )

    return thresh

def ocr_page_advanced(image_path, lang='jpn_vert', psm=5, apply_curvature=False, curvature_threshold=3.0):
    """
    Perform OCR on a single page image with advanced settings
    """
    try:
        # Preprocess
        debug_dir = os.path.join(
            os.path.dirname(image_path),
            f"debug_{os.path.splitext(os.path.basename(image_path))[0]}"
        )
        
        preprocessed_img = preprocess_image_advanced(
            image_path,
            debug_save_dir=debug_dir,
            apply_curvature=apply_curvature,
            curvature_threshold=curvature_threshold
        )
        
        # Convert back to PIL for Tesseract
        pil_img = Image.fromarray(preprocessed_img)

        # OCR configuration
        # --oem 3: Default LSTM engine
        # --psm: Page segmentation mode passed as argument
        # -c preserve_interword_spaces=1: Keep spacing
        custom_config = f'--oem 3 --psm {psm} -c preserve_interword_spaces=1'
        
        text = pytesseract.image_to_string(pil_img, lang=lang, config=custom_config)
        
        # Get confidence data
        data = pytesseract.image_to_data(pil_img, lang=lang, config=custom_config, output_type=pytesseract.Output.DICT)
        conf_list = [int(x) for x in data['conf'] if x != '-1']
        avg_conf = sum(conf_list) / len(conf_list) if conf_list else 0

        return text, avg_conf, debug_dir
    except Exception as e:
        return f"Error: {str(e)}", 0, None

if __name__ == "__main__":
    # Test on Text Page (003) and Table Page (011)
    base_dir = r"c:\Users\User\Downloads\日本帝國港灣統計_0001\pages"
    test_pages = [
        ("Page 003 (Text)", os.path.join(base_dir, "page_003.png"), 'jpn_vert', 5),
        ("Page 011 (Table)", os.path.join(base_dir, "page_011.png"), 'jpn', 6) # Tables usually better with psm 6 or 4 in horizontal mode if they are standard tables, but vertical PDF tables are tricky.
    ]
    
    output_lines = []
    
    for label, path, lang, psm in test_pages:
        print(f"Processing {label} with lang={lang}, psm={psm}...")
        
        try:
            text, conf, debug_process_path = ocr_page_advanced(path, lang=lang, psm=psm)
            
            header = f"\n{'='*70}\n{label}\nLang: {lang}, PSM: {psm}\nConfidence: {conf:.2f}%\nProcessed Image: {debug_process_path}\n{'='*70}\n"
            print(header)
            print(text[:500]) # Preview
            
            output_lines.append(header)
            output_lines.append(text)
        except Exception as e:
            err_msg = f"Failed to process {label}: {e}"
            print(err_msg)
            output_lines.append(err_msg)

    # Save results
    output_file = r"c:\Users\User\Downloads\日本帝國港灣統計_0001\ocr_advanced_test.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))
    
    print(f"\n\nResults saved to: {output_file}")
