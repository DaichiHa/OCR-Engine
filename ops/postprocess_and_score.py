import re
from pathlib import Path

try:
    from postprocess_langchain import run_rule_pipeline
except Exception:
    # when executed as a package (python -m ops.postprocess_and_score)
    # the module may be available under the ops package
    from ops.postprocess_langchain import run_rule_pipeline

# simple normalization helpers
FW_TO_HW = str.maketrans(
    {
        "０": "0",
        "１": "1",
        "２": "2",
        "３": "3",
        "４": "4",
        "５": "5",
        "６": "6",
        "７": "7",
        "８": "8",
        "９": "9",
        "：": ":",
        "－": "-",
        "，": ",",
        "．": ".",
        "（": "(",
        "）": ")",
        "、": ",",
        "。": ".",
    }
)


def normalize_text(s):
    # fullwidth to halfwidth for digits/punct
    s = s.translate(FW_TO_HW)
    # collapse multiple spaces and strip
    s = re.sub(r"\s+", " ", s)
    s = s.strip()
    return s


def process_and_score(in_path):
    in_path = Path(in_path)
    text = in_path.read_text(encoding="utf-8")
    norm = "\n".join(normalize_text(line) for line in text.splitlines() if line.strip())
    out_path = in_path.with_name(in_path.stem + ".normalized.txt")
    out_path.write_text(norm, encoding="utf-8")
    clean_out = in_path.with_suffix(".clean.txt")
    # reuse existing pipeline to compute KPIs
    summary = run_rule_pipeline(str(out_path), str(clean_out))
    return out_path, summary


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: postprocess_and_score.py <rapid.txt> [<rapid2> ...]")
        sys.exit(1)
    for p in sys.argv[1:]:
        out, summary = process_and_score(p)
        print(p, "-> normalized:", out)
        print("summary:", summary)
