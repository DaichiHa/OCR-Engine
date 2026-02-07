import importlib.util
import sys
import runpy

spec = importlib.util.find_spec('rapidocr_onnxruntime')
if spec is None:
    print('rapidocr_onnxruntime not installed — skipping OCR run')
    sys.exit(0)
print('rapidocr_onnxruntime found — running ops/run_rapidocr_batch.py')
runpy.run_path('ops/run_rapidocr_batch.py', run_name='__main__')
