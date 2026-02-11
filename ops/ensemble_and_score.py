import subprocess
import sys
from pathlib import Path


def simple_ensemble(rapid_path: Path, tess_path: Path) -> str:
    rtxt = rapid_path.read_text(encoding="utf-8").splitlines()
    ttxt = tess_path.read_text(encoding="utf-8").splitlines()
    out_lines = []
    maxl = max(len(rtxt), len(ttxt))
    for i in range(maxl):
        r = rtxt[i].strip() if i < len(rtxt) else ""
        t = ttxt[i].strip() if i < len(ttxt) else ""
        if r and t:
            # prefer the longer non-empty line (heuristic)
            out = r if len(r) >= len(t) else t
        elif r:
            out = r
        else:
            out = t
        out_lines.append(out)
    return "\n".join([line for line in out_lines if line])


def main():
    if len(sys.argv) < 3:
        print("Usage: ensemble_and_score.py rapid.normalized.txt tess.normalized.txt")
        sys.exit(1)
    rapid = Path(sys.argv[1])
    tess = Path(sys.argv[2])
    merged_text = simple_ensemble(rapid, tess)
    out = rapid.with_name(rapid.stem + ".ensemble.txt")
    out.write_text(merged_text, encoding="utf-8")
    print("Wrote ensemble:", out)
    # score via existing pipeline script
    cmd = [sys.executable, "ops/postprocess_and_score.py", str(out)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        print(r.stdout)
        if r.returncode != 0:
            print("postprocess_and_score failed:", r.stderr)
    except subprocess.TimeoutExpired:
        print("postprocess_and_score timed out for", out)
    except Exception as e:
        print("postprocess_and_score error:", e)


if __name__ == "__main__":
    main()
