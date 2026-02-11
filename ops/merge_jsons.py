import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "local_artifacts"
OUTDIR = ROOT / "merged_jsons"
OUTDIR.mkdir(parents=True, exist_ok=True)


def load_json_file(p: Path):
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data
    except Exception:
        # try jsonlines
        res = []
        try:
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                res.append(json.loads(line))
            return res
        except Exception:
            return None


def main():
    all_items = []
    files = list(ROOT.rglob("*.json")) + list(ROOT.rglob("*.jsonl"))
    files = sorted(set(files))
    meta = {"count_files": len(files), "files": []}
    for f in files:
        data = load_json_file(f)
        meta["files"].append(str(f.relative_to(ROOT)))
        if data is None:
            continue
        if isinstance(data, list):
            all_items.extend(data)
        else:
            all_items.append(data)

    combined = OUTDIR / "combined.json"
    combined.write_text(
        json.dumps(all_items, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    combinedl = OUTDIR / "combined.jsonl"
    with combinedl.open("w", encoding="utf-8") as fh:
        for item in all_items:
            fh.write(json.dumps(item, ensure_ascii=False) + "\n")

    metafile = OUTDIR / "merge_meta.json"
    meta["out_json"] = str(combined.relative_to(ROOT))
    meta["out_jsonl"] = str(combinedl.relative_to(ROOT))
    metafile.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Wrote", combined, "and", combinedl)
    print("Files processed:", meta["count_files"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
