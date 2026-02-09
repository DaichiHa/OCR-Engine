#!/usr/bin/env python3
import json
from pathlib import Path

def score_text(text: str) -> float:
    # simple readability: fraction of lines with >=3 alpha chars
    lines = [l for l in text.splitlines() if l.strip()]
    if not lines:
        return 0.0
    good = 0
    for l in lines:
        alpha = sum(1 for ch in l if ch.isalpha())
        if alpha >= 3:
            good += 1
    return good/len(lines)

def main():
    ms = Path('ops/local_artifacts/merged_summary.json')
    if not ms.exists():
        print('missing merged_summary.json')
        return 2
    data = json.loads(ms.read_text(encoding='utf-8'))
    results = []
    for item in data:
        merged = item.get('merged')
        if not merged:
            continue
        p = Path(merged)
        if not p.exists():
            continue
        try:
            txt = p.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        s = score_text(txt)
        results.append((s, p, item.get('group')))
    results.sort(reverse=True)
    out = Path('ops/local_artifacts/readability_ranking.txt')
    with out.open('w', encoding='utf-8') as f:
        for s,p,g in results[:50]:
            f.write(f"{s:.3f}\t{g}\t{p}\n")
    print('Wrote', out)
    if results:
        best = results[0]
        print('Best:', best[0], best[2], best[1])
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
