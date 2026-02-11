import importlib
import sys

print("invoked python:", sys.executable)
try:
    m = importlib.import_module("onnxocr_ppocrv5")
    print("onnxocr_ppocrv5 module file:", getattr(m, "__file__", None))
except Exception as e:
    print("import error:", e)
