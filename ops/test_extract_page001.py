import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from table_extractor_v4 import extract_table_structure_v4

img = r"C:\Users\User\Downloads\PDF\_img\page_001.png"
out_debug_dir = os.path.abspath(".")

if not os.path.exists(img):
    print("MISSING_IMAGE", img)
    sys.exit(2)

try:
    cells, debug = extract_table_structure_v4(img, out_debug_dir)
    print("CELL_COUNT", len(cells))
    for i, c in enumerate(cells[:200]):
        print(i, c)
    print("DEBUG_PATH", debug)
except Exception as e:
    import traceback

    traceback.print_exc()
    print("ERROR", e)
    sys.exit(1)
