import subprocess
import argparse
import sys
from pathlib import Path
try:
    from rapidocr_onnxruntime import RapidOCR
except Exception:
    RapidOCR = None
from postprocess_langchain import run_rule_pipeline
# Fallback wrapper that mimics RapidOCR minimal output shape
def _make_fallback_ocr():
    try:
        # prefer paddleocr if available
        from paddleocr import PaddleOCR
        pocr = PaddleOCR(use_angle_cls=False, lang='japan')

        class PaddleWrapper:
            def __call__(self, img_path):
                res = pocr.ocr(img_path, cls=False)
                dets = []
                for line in res:
                    for item in line:
                        box = item[0]
                        text = item[1][0]
                        score = float(item[1][1]) if len(item[1]) > 1 else 1.0
                        dets.append((box, text, score))
                return dets

        return PaddleWrapper()
    except Exception:
        pass
    try:
        # fallback to pytesseract (line-based, no boxes)
        import pytesseract
        from PIL import Image

        class TesseractWrapper:
            def __call__(self, img_path):
                img = Image.open(img_path)
                txt = pytesseract.image_to_string(img, lang='jpn')
                lines = [l.strip() for l in txt.splitlines() if l.strip()]
                dets = []
                for t in lines:
                    dets.append((None, t, 1.0))
                return dets

        return TesseractWrapper()
    except Exception:
        # last-resort no-op OCR: return empty list
        class EmptyWrapper:
            def __call__(self, img_path):
                return []
        return EmptyWrapper()

if RapidOCR is None:
    ocr = _make_fallback_ocr()
else:
    ocr = RapidOCR()

# CLI: allow selecting page and preprocess python executable
def _parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('--page', default='010', help='page id (e.g. 000, 010)')
    p.add_argument('--preprocess-python', default=None, help='python executable to run preprocess script')
    return p.parse_args()

args = _parse_args()
page = args.page
miniconda_py = r'C:/Users/User/Miniconda3/envs/ocr311/python.exe'
if args.preprocess_python:
    preprocess_python = args.preprocess_python
else:
    preprocess_python = miniconda_py if Path(miniconda_py).exists() else sys.executable

src = Path(f'C:/Users/User/Downloads/PDF/_img/page_{page}.png')
from itertools import product

# broader grid of CLAHE combos: (clip, tile, denoise_h)
clip_vals = [1.5, 2.5, 4.0]
tile_vals = [4, 8, 16]
denoise_vals = [0, 8, 12]
combos = list(product(clip_vals, tile_vals, denoise_vals))
results = []
for i,(clip,tile,denoise) in enumerate(combos, start=1):
    out = Path(f'ops/page_010_clahe_{i}.png')
    cmd = [
        preprocess_python,
        'ops/preprocess_sr_clahe.py',
        '--in', str(src),
        '--out', str(out),
        '--scale', '2',
        '--clahe-clip', str(clip),
        '--clahe-tile', str(tile),
        '--denoise-h', str(denoise)
    ]
    print('Running:', ' '.join(cmd))
    subprocess.run(cmd, check=True)
    print('Preprocessed ->', out)
    # RapidOCR inference (normalize various return shapes)
    res = ocr(str(out))
    def _normalize_res(r):
        if r is None:
            return []
        if isinstance(r, (tuple, list)):
            if len(r) == 0:
                return []
            # case: (dets, scores...) where dets is a list/tuple
            if isinstance(r[0], (list, tuple)):
                return list(r[0])
            # case: flat list of detections
            if all(isinstance(x, (list, tuple)) for x in r):
                return list(r)
        # single detection fallback
        return [r]

    dets = _normalize_res(res)
    txt_path = out.with_suffix('.rapid.txt')
    with open(txt_path, 'w', encoding='utf-8') as f:
        for item in dets:
            try:
                box, text, score = item
            except Exception:
                if len(item) >= 3:
                    box, text, score = item[0], item[1], item[2]
                else:
                    continue
            f.write(str(text) + '\n')
    print('Wrote rapid txt:', txt_path)
    # Postprocess KPI
    summary = run_rule_pipeline(str(txt_path), str(out.with_suffix('.clean.txt')))
    results.append({'combo':(clip,tile,denoise),'summary':summary})

# write results
import json
with open('ops/clahe_sweep_page010_results.json','w',encoding='utf-8') as f:
    json.dump(results,f,ensure_ascii=False,indent=2)
print('WROTE ops/clahe_sweep_page010_results.json')
