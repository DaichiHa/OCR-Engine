import pkgutil
pkgs=[m.name for m in pkgutil.iter_modules() if ('ppocr' in m.name) or ('onnxocr' in m.name) or ('ppocrv5' in m.name) or ('onnx' in m.name and 'ocr' in m.name)]
print('candidate pkgs:', pkgs)

import sys, importlib
for name in pkgs:
    try:
        m=importlib.import_module(name)
        print(name, '->', getattr(m, '__file__', 'built-in'))
    except Exception as e:
        print('import', name, 'failed:', e)
