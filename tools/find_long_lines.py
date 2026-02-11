from pathlib import Path

p = Path("table_extractor_v4.py")
for i, l in enumerate(p.read_text(encoding="utf-8").splitlines(), start=1):
    if len(l) > 79:
        print(i, len(l), l)
