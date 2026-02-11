import json
import re
import shutil
from pathlib import Path

root = Path(__file__).parent
ops = root
outdir = root / "local_artifacts"
outdir.mkdir(exist_ok=True)


def normalize(name):
    # remove tile suffixes, rotations, resized markers, extensions
    s = name
    s = re.sub(r"\.tess\.tile\d{3}", "", s)
    s = s.replace(".resized", "").replace(".orig", "")
    s = re.sub(r"\.rot\d+", "", s)
    s = re.sub(r"\.tess(\.tiled)?", "", s)
    s = re.sub(r"\.ppocr", "", s)
    s = re.sub(r"\.psm\d+", "", s)
    # remove trailing numeric markers like .1 .2 when renamed
    s = re.sub(r"\.\d+$", "", s)
    return s


moved = []
for p in sorted(ops.iterdir()):
    if p.is_file():
        if p.suffix in [".py", ".json", ".md"]:
            continue
        if str(p).startswith(str(root / "archive")):
            continue
        # skip files we've intentionally created for config and code
        if p.name in [
            "page_010_inventory.csv",
            "page_010_cleanup_report.txt",
            "page_010_archive_summary.json",
            "page_010_archive.zip",
        ]:
            continue
        base = normalize(p.name)
        grp = outdir / base
        grp.mkdir(parents=True, exist_ok=True)
        dest = grp / p.name
        shutil.move(str(p), str(dest))
        moved.append({"src": str(p), "dest": str(dest)})

# write summary
summary = outdir / "local_artifacts_summary.json"
with open(summary, "w", encoding="utf-8") as f:
    json.dump(
        {"moved": moved, "groups": [d.name for d in outdir.iterdir() if d.is_dir()]},
        f,
        _indent=2,
        _ensure_ascii=False,
    )

print("Moved", len(moved), "files to", outdir)
print("Summary:", summary)
