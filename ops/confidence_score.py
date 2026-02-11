import json
import re
from pathlib import Path

BASE = Path(__file__).parent / "local_artifacts"


def readability_score(text: str) -> float:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return 0.0
    total_words = sum(len(re.findall(r"\w+", line)) for line in lines)
    avg_words = total_words / len(lines)
    # normalize: 0 words ->0, 1-20 words -> map to 0-1 (cap at 20)
    val = min(avg_words, 20) / 20.0
    return val


def detect_provenance(name: str) -> float:
    name = name.lower()
    if "ensemble" in name or "rapid" in name or "best" in name:
        return 1.0
    if "tess" in name or "ppocr" in name or "clahe" in name:
        return 0.6
    return 0.5


def base_ocr_confidence(name: str) -> float:
    n = name.lower()
    if "ensemble" in n:
        return 0.75
    if "rapid" in n:
        return 0.6
    if "tess" in n or "pytess" in n:
        return 0.5
    if "ppocr" in n or "paddle" in n:
        return 0.7
    return 0.55


def gather_candidates(base: Path):
    candidates = []
    if not base.exists():
        return candidates
    for p in base.rglob("*"):
        if p.is_file() and p.suffix.lower().endswith(".txt"):
            # consider files with .clean.txt, .normalized.txt, .ppocr.txt, .ollama.suggested.txt
            s = str(p.name)
            if any(
                k in s for k in (".clean", ".normalized", ".ppocr", ".tess", "ollama")
            ):
                candidates.append(p)
    return candidates


def score_file(p: Path, group_counts: dict) -> dict:
    name = p.name
    text = ""
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        pass
    rd = readability_score(text)
    prov = detect_provenance(name)
    ocr_conf = base_ocr_confidence(name)
    # consensus proxy: how many siblings share same base prefix
    prefix = re.sub(
        r"\.(clean|normalized|ppocr|tess|txt|ollama|suggested).*",
        "",
        name,
        flags=re.I,
    )
    consensus = min(1.0, group_counts.get(prefix.lower(), 1) / 3.0)
    lm_agreement = (
        1.0
        if ".ollama.suggested" in name
        or (p.with_suffix(".ollama.suggested.txt").exists())
        else 0.0
    )

    weights = {
        "ocr_conf": 0.4,
        "consensus": 0.25,
        "lm_agreement": 0.2,
        "readability": 0.1,
        "provenance": 0.05,
    }

    final = (
        weights["ocr_conf"] * ocr_conf
        + weights["consensus"] * consensus
        + weights["lm_agreement"] * lm_agreement
        + weights["readability"] * rd
        + weights["provenance"] * prov
    )
    return {
        "path": str(p),
        "name": name,
        "ocr_conf": round(ocr_conf, 3),
        "consensus": round(consensus, 3),
        "lm_agreement": lm_agreement,
        "readability": round(rd, 3),
        "provenance": round(prov, 3),
        "score": round(final, 4),
    }


def main():
    out = []
    cand = gather_candidates(BASE)
    # build prefix counts
    group_counts = {}
    for p in cand:
        name = p.name
        prefix = re.sub(
            r"\.(clean|normalized|ppocr|tess|txt|ollama|suggested).*",
            "",
            name,
            flags=re.I,
        ).lower()
        group_counts[prefix] = group_counts.get(prefix, 0) + 1

    for p in cand:
        out.append(score_file(p, group_counts))

    # sort by score desc
    out_sorted = sorted(out, key=lambda x: x["score"], reverse=True)
    summary = {
        "count": len(out_sorted),
        "top": out_sorted[:10],
        "all": out_sorted,
    }
    target = Path(__file__).parent / "confidence_summary.json"
    target.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Wrote", target, "entries=", len(out_sorted))


if __name__ == "__main__":
    main()
