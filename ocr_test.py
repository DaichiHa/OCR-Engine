"""
OCR Test Script for Japanese Historical Document
Uses Tesseract OCR with Japanese vertical text model
"""


import pytesseract
from PIL import Image

# Set Tesseract path if needed (Windows typical path)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def ocr_page(image_path, lang="jpn_vert+jpn"):
    """
    Perform OCR on a single page image

    Args:
        image_path: Path to the PNG image
        lang: Language model to use (jpn_vert for vertical Japanese text)

    Returns:
        Extracted text
    """
    try:
        img = Image.open(image_path)

        # OCR configuration for best accuracy
        custom_config = r"--oem 3 --psm 6"

        text = pytesseract.image_to_string(img, lang=lang, config=custom_config)
        return text
    except Exception as e:
        return f"Error: {str(e)}"


if __name__ == "__main__":
    # Test with page 3 (緒言 - Introduction)
    test_page = r"c:\Users\User\Downloads\日本帝國港灣統計_0001\pages\page_003.png"

    print("=" * 60)
    print("OCR Test - Page 003 (緒言)")
    print("=" * 60)

    result = ocr_page(test_page)
    print(result)

    # Save result to file for review
    output_file = r"c:\Users\User\Downloads\日本帝國港灣統計_0001\ocr_test_result.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(result)

    print("\n" + "=" * 60)
    print(f"Result saved to: {output_file}")
    print("=" * 60)
