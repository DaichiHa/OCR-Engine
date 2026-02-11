#!/usr/bin/env python3
"""
Conservative auto-fixes for ruff warnings:

- Rename lambda/comprehension variable `l` to `line` (reduces E741)
- Prefix obviously-unused local assignments with `_` when the name is never used elsewhere in the file (reduces F841)

This script is intentionally conservative and creates a `.bak-safe` backup for each file modified.
"""

import re
import subprocess
from pathlib import Path

SKIP_DIRS = {".git", "__pycache__", "venv", ".venv", "env", ".env"}


def should_skip(path: Path) -> bool:
    for part in path.parts:
        if part in SKIP_DIRS:
            return True
    return False


def transform_text(text: str) -> (str, bool):
    changed = False

    # 1) Rename lambda parameter `l` -> `line` (simple pattern)
    new = re.sub(r"\blambda\s+line\s*:", "lambda line:", text)
    if new != text:
        text = new
        changed = True

    # 2) Rename comprehension/for variable `for line in` -> `for line in`
    new = re.sub(r"\bfor\s+line\s+in\b", "for line in", text)
    if new != text:
        text = new
        changed = True

    # 3) Replace common comprehension targets like `[line.strip() for line in ...]` occurrences
    new = re.sub(r"\[\s*line\b", "[line", text)
    if new != text:
        text = new
        changed = True

    # 4) Prefix obviously-unused assignment targets with _ if name not used elsewhere
    # Find simple assignments at line start: name = ...
    assigns = re.findall(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", text, flags=re.MULTILINE)
    for name in set(assigns):
        # ignore common magic or single-underscore names
        if name.startswith("_") or name in ("__all__",):
            continue
        # count occurrences of name in the file
        occurrences = len(re.findall(r"\b" + re.escape(name) + r"\b", text))
        # if only occurrence is the assignment (occurrences == 1), prefix it
        if occurrences <= 1:
            # replace the first assignment occurrence
            pattern = r"(^\s*)\b" + re.escape(name) + r"\b(\s*=)"
            new_text, nsub = re.subn(
                pattern,
                r"\1_" + name + r"\2",
                text,
                count=1,
                flags=re.MULTILINE,
            )
            if nsub:
                text = new_text
                changed = True

    return text, changed


def process_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    new_text, changed = transform_text(text)
    if not changed:
        return False
    bak = path.with_suffix(path.suffix + ".bak-safe")
    bak.write_text(text, encoding="utf-8")
    path.write_text(new_text, encoding="utf-8")
    return True


def find_py_files(root: Path):
    for p in root.rglob("*.py"):
        if should_skip(p):
            continue
        yield p


def main():
    root = Path.cwd()
    modified = []
    for p in find_py_files(root):
        try:
            if process_file(p):
                modified.append(str(p.relative_to(root)))
        except Exception as e:
            print(f"Skipping {p}: {e}")

    if not modified:
        print("No files modified.")
        return

    print("Modified files:")
    for f in modified:
        print(" -", f)

    # commit
    try:
        subprocess.run(["git", "add", "-A"], check=True)
        subprocess.run(
            [
                "git",
                "commit",
                "-m",
                "chore(lint): auto-fix safe issues (rename 'l' -> 'line', prefix unused locals)",
            ],
            check=True,
        )
        print("Committed changes.")
    except subprocess.CalledProcessError as e:
        print("Git commit failed:", e)


if __name__ == "__main__":
    main()
