import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "local_artifacts"


def sizeof(path: Path):
    total = 0
    count = 0
    for p in path.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
                count += 1
            except OSError:
                pass
    return total, count


def human(n):
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if n < 1024.0:
            return f"{n:.1f}{unit}"
        n /= 1024.0
    return f"{n:.1f}PB"


def main():
    summary = {}
    if not ROOT.exists():
        print("No local_artifacts folder found at", ROOT)
        return 1
    for child in sorted(ROOT.iterdir()):
        if child.is_dir():
            size, count = sizeof(child)
            summary[str(child.name)] = {
                "bytes": size,
                "files": count,
                "human": human(size),
            }
    out = ROOT / "summary.json"
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print("Wrote", out)
    for k, v in summary.items():
        print(f"{k}: {v['human']} ({v['files']} files)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
