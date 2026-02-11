import collections
import os
import re
import sys

root = r"C:\Users\User\Downloads\OCR-Engine"
groups = collections.defaultdict(list)
for dirpath, dirnames, filenames in os.walk(root):
    for d in dirnames:
        k = re.sub(r"[^A-Za-z0-9]", "", d.lower())[:30]
        groups[k].append(os.path.join(dirpath, d))

cand = {k: v for k, v in groups.items() if len(v) > 1}
if not cand:
    print("No similar-name groups inside Downloads\\OCR-Engine found")
    sys.exit(0)
for k, v in sorted(cand.items(), key=lambda x: -len(x[1])):
    print(f"Norm={k} Count={len(v)}")
    for p in v:
        print("  -", p)
    print()
