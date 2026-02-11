import json
from pathlib import Path

p = Path("ops/local_refine_report_page010.json")
if not p.exists():
    print("missing", p)
    raise SystemExit(1)

r = json.loads(p.read_text(encoding="utf-8"))

total = len(r)
rap_non = sum(1 for e in r if e.get("rapid") and e["rapid"].get("text"))
pp_non = sum(1 for e in r if e.get("ppocr") and e["ppocr"].get("text"))
rap_better = 0
pp_better = 0
for e in r:
    orig = e.get("orig_score")
    if orig is None:
        continue
    if e.get("rapid") and isinstance(e["rapid"].get("score"), (int, float)):
        if e["rapid"]["score"] > orig:
            rap_better += 1
    if e.get("ppocr") and isinstance(e["ppocr"].get("score"), (int, float)):
        if e["ppocr"]["score"] > orig:
            pp_better += 1

print("total", total)
print("rapid produced:", rap_non)
print("ppocr produced:", pp_non)
print("rapid improved score count:", rap_better)
print("ppocr improved score count:", pp_better)
print("\nSample entries:")
for e in r[:8]:
    print(
        e.get("idx"),
        e.get("orig_text"),
        e.get("orig_score"),
        "-> rapid",
        e.get("rapid"),
        "ppocr",
        e.get("ppocr"),
    )
