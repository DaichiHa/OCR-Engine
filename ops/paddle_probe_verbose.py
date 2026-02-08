import os
from pathlib import Path
# Disable oneDNN/ONEDNN for Paddle runtime to avoid ConvertPirAttribute2RuntimeAttribute errors
os.environ.setdefault('FLAGS_use_mkldnn', '0')
os.environ.setdefault('PADDLE_WITH_ONEDNN', '0')
os.environ.setdefault('PADDLE_DISABLE_ONEDNN', '1')
os.environ.setdefault('PADDLE_WITH_MKL', '0')
from paddleocr import PaddleOCR
pocr = PaddleOCR(use_textline_orientation=False, lang='japan')
imgs = [Path('ops/page_010_clahe_1.png'), Path('ops/page_010_clahe_2.png')]
for img in imgs:
    print('\n--- Processing', img, '---')
    res = pocr.ocr(str(img))
    print('RAW RESULT REPR:\n', repr(res)[:4000])
    out_txt = img.with_suffix('.ppocr.txt')
    written = 0
    with open(out_txt, 'w', encoding='utf-8') as f:
        # handle nested structures
        if isinstance(res, (list, tuple)):
            for page in res:
                if isinstance(page, (list, tuple)):
                    for item in page:
                        # item may be [box, (text, score)] or [box, [text, score]]
                        try:
                            if isinstance(item, (list, tuple)) and len(item) >= 2:
                                txt = None
                                if isinstance(item[1], (list, tuple)):
                                    txt = item[1][0]
                                elif isinstance(item[1], str):
                                    txt = item[1]
                                elif isinstance(item[1], dict) and 'text' in item[1]:
                                    txt = item[1]['text']
                                if txt:
                                    f.write(str(txt) + '\n')
                                    written += 1
                        except Exception as e:
                            print('write-exc', e)
                else:
                    # fallback: try to stringify
                    s = str(page)
                    if s.strip():
                        f.write(s + '\n')
                        written += 1
        else:
            s = str(res)
            if s.strip():
                f.write(s + '\n')
                written += 1
    print('Wrote', out_txt, 'lines=', written)
