import subprocess
from pathlib import Path
from rapidocr_onnxruntime import RapidOCR
from postprocess_langchain import run_rule_pipeline

src = Path('C:/Users/User/Downloads/PDF/_img/page_010.png')
combos = [
    (1.5, 8, 0),
    (2.5, 8, 8),
    (4.0, 4, 8),
]
ocr = RapidOCR()
results = []
for i,(clip,tile,denoise) in enumerate(combos, start=1):
    out = Path(f'ops/page_010_clahe_{i}.png')
    cmd = [
        'C:/Users/User/Miniconda3/envs/ocr311/python.exe',
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
    # RapidOCR inference
    res = ocr(str(out))
    dets = res[0] if isinstance(res, tuple) or isinstance(res, list) else res
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
