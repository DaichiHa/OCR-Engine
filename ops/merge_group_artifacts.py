import json
from pathlib import Path

root = Path(__file__).parent
la = root / "local_artifacts"
merged_summary = []

TEXT_EXTS = [
    ".txt",
    ".tess.txt",
    ".ppocr.txt",
    ".rapid.txt",
    ".clean.txt",
    ".normalized.txt",
    ".ollama.suggested.txt",
    ".json",
]


def is_text(p: Path):
    return p.suffix.lower() in TEXT_EXTS or any(
        str(p).endswith(ext) for ext in TEXT_EXTS
    )


for group in sorted([d for d in la.iterdir() if d.is_dir()]):
    files = sorted([p for p in group.iterdir() if p.is_file() and is_text(p)])
    if not files:
        continue
    # naive merge: pick canonical by priority of suffix, else longest file
    priority = [
        ".clean.txt",
        ".normalized.txt",
        ".tess.tiled.psm11.txt",
        ".tess.txt",
        ".rapid.txt",
        ".ppocr.txt",
        ".ollama.suggested.txt",
        ".txt",
        ".json",
    ]

    def score(p):
        name = p.name.lower()
        for i, suf in enumerate(priority):
            if suf in name:
                return (0, i, -p.stat().st_size)
        return (1, 999, -p.stat().st_size)

    files_sorted = sorted(files, key=score)
    canonical = files_sorted[0]
    merged_path = group / (group.name + "_merged.txt")
    # merge unique lines from all text files, preserve order preferring canonical
    lines = []
    seen = set()

    def add_lines(p):
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return
        for line in txt.splitlines():
            s = line.strip()
            if not s:
                continue
            if s in seen:
                continue
            seen.add(s)
            lines.append(line)

    # start with canonical
    add_lines(canonical)
    for p in files_sorted[1:]:
        add_lines(p)

    merged_path.write_text("\n".join(lines), encoding="utf-8")
    merged_summary.append(
        {
            "group": group.name,
            "canonical": canonical.name,
            "merged": str(merged_path),
            "count_files": len(files),
        }
    )

summary_path = la / "merged_summary.json"
summary_path.write_text(
    json.dumps(merged_summary, indent=2, ensure_ascii=False), encoding="utf-8"
)
print("Wrote", summary_path)