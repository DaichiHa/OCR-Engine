import traceback
from pathlib import Path
img_path = Path('ops/page_010_clahe_1.png')
print('Image exists:', img_path.exists(), 'path=', img_path)
try:
    from paddleocr import PaddleOCR
    print('PaddleOCR import OK')
    try:
        pocr = PaddleOCR(use_textline_orientation=False, lang='japan')
        print('PaddleOCR initialized')
        res = pocr.ocr(str(img_path))
        print('PaddleOCR output:')
        print(res)
    except Exception:
        print('PaddleOCR runtime error:')
        traceback.print_exc()
except Exception:
    print('PaddleOCR not available:')
    traceback.print_exc()

try:
    from PIL import Image
    import pytesseract
    # prefer configured tesseract if present
    try:
        from .paths_loader import get_path
        t = get_path('tesseract')
        if t:
            pytesseract.pytesseract.tesseract_cmd = t
    except Exception:
        pass
    print('pytesseract import OK')
    try:
        img = Image.open(img_path)
        print('Image size:', img.size)
        txt = pytesseract.image_to_string(img, lang='jpn')
        print('pytesseract output:')
        print(repr(txt))
    except Exception:
        print('pytesseract runtime error:')
        traceback.print_exc()
except Exception:
    print('pytesseract not available:')
    traceback.print_exc()
