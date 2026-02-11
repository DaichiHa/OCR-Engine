#!/usr/bin/env python3
"""
Lightweight CLI to send OCR text to local Ollama for suggested corrections.

Usage: python ops/assist_with_ollama.py --in some.clean.txt

The script reads the input text, selects candidate lines (heuristic), and asks
the local Ollama instance (CLI or HTTP) to propose corrections. Outputs a
`.ollama.suggested.txt` alongside the input file.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from pathlib import Path as _P

# ensure `ops` package modules are importable when running script directly
sys.path.insert(0, str(_P(__file__).resolve().parent))
from ollama_helper import generate, load_config


def noisy_score(s: str) -> float:
    # higher means noisier
    if not s.strip():
        return 0.0
    non_alnum = sum(1 for ch in s if not (ch.isalnum() or ch.isspace()))
    return non_alnum / max(1, len(s))


def build_prompt(lines):
    # Ask for line-by-line correction. Keep instructions short and local-only.
    inst = (
        "You are a local OCR postprocessor. Given noisy OCR outputs, correct them "
        "into readable modern text. Preserve numbers and punctuation meaning; fix obvious OCR mistakes. "
        "Return only the corrected lines, in the same order, with no extra commentary."
    )
    body = "\n".join(lines)
    return inst + "\n\n" + body


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="infile", required=True)
    p.add_argument("--threshold", type=float, default=0.02)
    args = p.parse_args()

    infile = Path(args.infile)
    if not infile.exists():
        print(json.dumps({"error": "missing input", "in": str(infile)}))
        return 2

    txt = infile.read_text(encoding="utf-8", errors="ignore").splitlines()
    candidates = [
        ln for ln in txt if noisy_score(ln) >= args.threshold and len(ln.strip()) > 6
    ]

    if not candidates:
        print(json.dumps({"status": "no_candidates", "candidates": 0}))
        return 0

    cfg = load_config()
    # If LM usage is disabled in config, skip invocation and write a note file.
    if not cfg.get("use_cli", True) and not cfg.get("host"):
        out_path = infile.with_suffix(infile.suffix + ".ollama.suggested.txt")
        note = (
            "[LM disabled] Ollama CLI/HTTP disabled via ops/ollama_config.json.\n"
            "No suggestions applied.\n"
        )
        out_path.write_text(note, encoding="utf-8")
        print(
            json.dumps(
                {
                    "status": "skipped",
                    "out": str(out_path),
                    "candidates": len(candidates),
                }
            )
        )
        return 0

    prompt = build_prompt(candidates)
    res = generate(prompt, cfg)
    if not res:
        # capture failure to dedicated err file for visibility
        err_path = infile.with_suffix(infile.suffix + ".ollama.err.txt")
        err_path.write_text("No response from Ollama (CLI or HTTP)\n", encoding="utf-8")
        print(
            json.dumps(
                {
                    "error": "no_ollama",
                    "message": "Ollama not available (CLI or HTTP)",
                    "err": str(err_path),
                }
            )
        )
        return 3

    # if the CLI returned an error message string (e.g. "Error: unknown flag: --prompt"),
    # write it to an .ollama.err.txt and produce a small user-facing note as the suggested output.
    if isinstance(res, str) and re.search(r"error:|unknown flag|traceback", res, re.I):
        err_path = infile.with_suffix(infile.suffix + ".ollama.err.txt")
        err_path.write_text(res, encoding="utf-8")
        note = (
            f"[LM invocation failed] See {err_path.name} for raw output.\n"
            "No suggestions were applied. Please check local Ollama CLI/API compatibility."
        )
        out_path = infile.with_suffix(infile.suffix + ".ollama.suggested.txt")
        out_path.write_text(note, encoding="utf-8")
        print(
            json.dumps(
                {"status": "lm_error", "err": str(err_path), "out": str(out_path)}
            )
        )
        return 4

    # naive split by lines — user can review
    out_lines = [line.strip() for line in res.splitlines() if l.strip()]
    # merge back: replace candidate lines in original with suggestions by order
    out = []
    ci = 0
    for ln in txt:
        if noisy_score(ln) >= args.threshold and len(ln.strip()) > 6:
            if ci < len(out_lines):
                out.append(out_lines[ci])
            else:
                out.append(ln)
            ci += 1
        else:
            out.append(ln)

    out_path = infile.with_suffix(infile.suffix + ".ollama.suggested.txt")
    out_path.write_text("\n".join(out), encoding="utf-8")
    print(
        json.dumps(
            {"status": "ok", "out": str(out_path), "candidates": len(candidates)}
        )
    )


if __name__ == "__main__":
    main()
