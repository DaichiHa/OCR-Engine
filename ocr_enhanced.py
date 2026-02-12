"""
Enhanced OCR Script for Japanese Historical Document
Uses Tesseract OCR with image preprocessing for better accuracy
"""

import pytesseract
from PIL import Image, ImageEnhance, ImageFilter


def preprocess_image(img):
    """
    Preprocess image for better OCR accuracy
    - Convert to grayscale
    - Increase contrast
    - Apply sharpening
    - Binarize (convert to black and white)
    """
    # Convert to grayscale
    img = img.convert("L")

    # Increase contrast
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)

    # Sharpen
    img = img.filter(ImageFilter.SHARPEN)

    # Binarize - convert to pure black and white
    threshold = 140
    img = img.point(lambda x: 255 if x > threshold else 0, "1")

    return img


def ocr_page_enhanced(image_path, preprocess=True):
    """
    Perform enhanced OCR on a single page image

    Args:
        image_path: Path to the PNG image
        preprocess: Whether to apply image preprocessing

    Returns:
        Extracted text
    """
    try:
        img = Image.open(image_path)

        if preprocess:
            img = preprocess_image(img)

        # Try different configurations
        configs = [
            # Config 1: Vertical text, best for traditional Japanese documents
            (
                "jpn_vert",
                r"--oem 3 --psm 5",
            ),  # PSM 5: Single uniform block of vertical text
            # Config 2: Mixed vertical/horizontal
            (
                "jpn_vert+jpn",
                r"--oem 3 --psm 6",
            ),  # PSM 6: Assume single uniform block of text
            # Config 3: Auto orientation
            (
                "jpn+jpn_vert",
                r"--oem 3 --psm 3",
            ),  # PSM 3: Fully automatic page segmentation
        ]

        results = []
        for lang, config in configs:
            text = pytesseract.image_to_string(img, lang=lang, config=config)
            results.append(
                {
                    "lang": lang,
                    "config": config,
                    "text": text,
                    "char_count": len(text.replace("\n", "").replace(" ", "")),
                }
            )

        return results
    except Exception as e:
        return [{"error": str(e)}]


if __name__ == "__main__":
    # Test with page 3 (緒言 - Introduction)
    test_page = r"c:\Users\User\Downloads\日本帝國港灣統計_0001\pages\page_003.png"

    print("=" * 70)
    print("Enhanced OCR Test - Page 003 (緒言)")
    print("=" * 70)

    results = ocr_page_enhanced(test_page)

    output_lines = []
    for i, result in enumerate(results):
        header = (
            "\n"
            + "=" * 70
            + "\n"
            + f"Config {i+1}: lang={result.get('lang', 'N/A')}, psm={result.get('config', 'N/A')}\n"
            + f"Characters: {result.get('char_count', 0)}\n"
            + "=" * 70
            + "\n"
        )
        print(header)
        print(result.get("text", result.get("error", "Unknown error"))[:500])
        output_lines.append(header)
        output_lines.append(result.get("text", result.get("error", "Unknown error")))

    # Save all results to file
    output_file = r"c:\Users\User\Downloads\日本帝國港灣統計_0001\ocr_enhanced_test.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))

    print(f"\n\nResults saved to: {output_file}")
