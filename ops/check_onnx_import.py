import importlib
modules = ['onnxocr','onnxocr_ppocrv5','onnxocr_ppocrv5','onnxocr.ppocrv5']
for m in modules:
    try:
        mod = importlib.import_module(m)
        print(m, 'OK ->', getattr(mod,'__file__', 'built-in'))
    except Exception as e:
        print(m, 'ERROR ->', e)
