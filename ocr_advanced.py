"""
Advanced OCR Script for Japanese Historical Document
Uses OpenCV for advanced preprocessing and Tesseract for OCR
"""

import os

import cv2
import numpy as np
import pytesseract
from PIL import Image


def preprocess_image_advanced(image_path, debug_save_path=None):
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

    # Gray scale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Denoise (Non-local Means Denoising) - Good for removing paper grain
    denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)

    # Adaptive Thresholding (Gaussian C) - Handles uneven lighting/aging
    # Block size 11, C=2 (standard starting points)
    thresh = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )

    # Morphological operations to clean up dots/noise
    kernel = np.ones(
        (1, 1), np.uint8
    )  # Very small kernel to avoid damaging thin strokes

    # Slight dilation to connect broken characters (common in old print)
    # dilate = cv2.dilate(thresh, kernel, iterations=1)

    # For debugging - save using cv2.imencode for non-ASCII paths
    if debug_save_path:
        # cv2.imwrite(debug_save_path, thresh)
        extension = os.path.splitext(debug_save_path)[1]
        result, encoded_img = cv2.imencode(extension, thresh)
        if result:
            with open(debug_save_path, "wb") as f:
                f.write(encoded_img)

    return thresh


def ocr_page_advanced(image_path, lang="jpn_vert", psm=5):
    """
    Perform OCR on a single page image with advanced settings
    """
    try:
        # Preprocess
        debug_filename = f"debug_preprocessed_{os.path.basename(image_path)}"
        debug_path = os.path.join(os.path.dirname(image_path), debug_filename)

        preprocessed_img = preprocess_image_advanced(image_path, debug_path)

        # Convert back to PIL for Tesseract
        pil_img = Image.fromarray(preprocessed_img)

        # OCR configuration
        # --oem 3: Default LSTM engine
        # --psm: Page segmentation mode passed as argument
        # -c preserve_interword_spaces=1: Keep spacing
        custom_config = f"--oem 3 --psm {psm} -c preserve_interword_spaces=1"

        text = pytesseract.image_to_string(pil_img, lang=lang, config=custom_config)

        # Get confidence data
        data = pytesseract.image_to_data(
            pil_img,
            lang=lang,
            config=custom_config,
            output_type=pytesseract.Output.DICT,
        )
        conf_list = [int(x) for x in data["conf"] if x != "-1"]
        avg_conf = sum(conf_list) / len(conf_list) if conf_list else 0

        return text, avg_conf, debug_path
    except Exception as e:
        return f"Error: {str(e)}", 0, None


if __name__ == "__main__":
    # Test on Text Page (003) and Table Page (011)
    base_dir = r"c:\Users\User\Downloads\日本帝國港灣統計_0001\pages"
    test_pages = [
        ("Page 003 (Text)", os.path.join(base_dir, "page_003.png"), "jpn_vert", 5),
        (
            "Page 011 (Table)",
            os.path.join(base_dir, "page_011.png"),
            "jpn",
            6,
        ),  # Tables usually better with psm 6 or 4 in horizontal mode if they are standard tables, but vertical PDF tables are tricky.
    ]

    output_lines = []

    for label, path, lang, psm in test_pages:
        print(f"Processing {label} with lang={lang}, psm={psm}...")

        try:
            text, conf, debug_process_path = ocr_page_advanced(path, lang=lang, psm=psm)

            header = f"\n{'='*70}\n{label}\nLang: {lang}, PSM: {psm}\nConfidence: {conf:.2f}%\nProcessed Image: {debug_process_path}\n{'='*70}\n"
            print(header)
            print(text[:500])  # Preview

            output_lines.append(header)
            output_lines.append(text)
        except Exception as e:
            err_msg = f"Failed to process {label}: {e}"
            print(err_msg)
            output_lines.append(err_msg)

    # Save results
    output_file = r"c:\Users\User\Downloads\日本帝國港灣統計_0001\ocr_advanced_test.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))

    print(f"\n\nResults saved to: {output_file}")
