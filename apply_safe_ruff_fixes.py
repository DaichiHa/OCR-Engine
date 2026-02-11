#!/usr/bin/env python3
"""
Safe automated fixes for common ruff/flake8 issues.

Currently implements a conservative rule:
- convert bare `except:` to `except Exception:` (preserves comments)

Usage:
  python apply_safe_ruff_fixes.py [--commit] [--message "commit msg"]

The script creates a `.bak-applysafe` backup for each modified file.
"""
import argparse
import re
import subprocess
from pathlib import Path


SKIP_DIRS = {".git", "__pycache__", "venv", ".venv", "env", ".env"}
_PY_EXT = ".py"


def should_skip(path: Path) -> bool:
    for part in path.parts:
        if part in SKIP_DIRS:
            return True
    return False


def fix_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    # Match bare except: but not except Exception, except BaseException, or except (something) as e
    pattern = re.compile(r"(^\s*)except\s*:(?=\s*(#|$))", re.MULTILINE)
    if not pattern.search(text):
        return False
    new_text = pattern.sub(r"\1except Exception:", text)
    # backup
    bak = path.with_suffix(path.suffix + ".bak-applysafe")
    bak.write_text(text, encoding="utf-8")
    path.write_text(new_text, encoding="utf-8")
    return True


def find_py_files(root: Path):
    for p in root.rglob("*.py"):
        if should_skip(p):
            continue
        yield p


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", action="store_true", help="git add + commit modified files")
    parser.add_argument("--message", default="chore(lint): convert bare except to except Exception",
                        help="commit message when using --commit")
    args = parser.parse_args()

    root = Path.cwd()
    modified = []
    for p in find_py_files(root):
        try:
            if fix_file(p):
                modified.append(str(p.relative_to(root)))
        except Exception as e:
            print(f"Skipping {p}: {e}")

    if not modified:
        print("No files modified.")
        return

    print("Modified files:")
    for f in modified:
        print(" -", f)

    if args.commit:
        try:
            subprocess.run(["git", "add", "-A"], check=True)
            subprocess.run(["git", "commit", "-m", args.message], check=True)
            print("Committed changes.")
        except subprocess.CalledProcessError as e:
            print("Git commit failed:", e)


if __name__ == "__main__":
    main()
