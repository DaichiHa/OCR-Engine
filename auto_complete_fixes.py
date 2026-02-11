import re
import shutil
from pathlib import Path


def parse_ruff_report(report_path: Path):
    entries = []
    text = report_path.read_text(encoding="utf-8", errors="ignore")
    # Pattern: F821 ... Undefined name `l`\n  --> path:line:col
    for m in re.finditer(
        r"(F821|E722) .*?`?(\w+)`?.*?\n\s*-->\s*([^:\n]+):([0-9]+):([0-9]+)",
        text,
    ):
        code = m.group(1)
        name = m.group(2)
        path = m.group(3).strip()
        entries.append((code, name, Path(path)))
    return entries


def backup_file(p: Path):
    bak = p.with_suffix(p.suffix + ".bak-fix")
    shutil.copy2(p, bak)
    return bak


def replace_word(content: str, old: str, new: str) -> str:
    return re.sub(r"\b" + re.escape(old) + r"\b", new, content)


def fix_file_for_name(p: Path, name: str, code: str):
    src = p.read_text(encoding="utf-8", errors="ignore")
    orig = src
    modified = False

    if code == "F821":
        if name == "l":
            # if file contains lambda line or for line in, replace lone 'line' with 'line'
            if re.search(r"lambda\s+line\b|for\s+line\s+in\b", src):
                new = replace_word(src, "line", "line")
                if new != src:
                    src = new
                    modified = True
        elif name == "line":
            # if file contains numeric assignment to line, prefer keeping line for coords
            if re.search(r"\bl\s*=\s*int\(|\bl\s*=\s*", src):
                new = replace_word(src, "line", "line")
                if new != src:
                    src = new
                    modified = True

    if code == "E722":
        # convert bare except: -> except Exception:
        new = re.sub(
            r"(^\s*)except:\s*$",
            r"\1except Exception:",
            src,
            flags=re.MULTILINE,
        )
        if new != src:
            src = new
            modified = True

    if modified and src != orig:
        backup_file(p)
        p.write_text(src, encoding="utf-8")
        return True
    return False


def main():
    repo_root = Path(".")
    report = repo_root / "ruff_post.txt"
    if not report.exists():
        print("ruff_post.txt not found; run ruff and save report first.")
        return

    entries = parse_ruff_report(report)
    fixed = []
    for code, name, path in entries:
        if not path.exists():
            # maybe path is relative with backslashes
            alt = repo_root / path
            if alt.exists():
                path = alt
            else:
                print(f"skipping missing file: {path}")
                continue
        try:
            if fix_file_for_name(path, name, code):
                fixed.append(str(path))
        except Exception as e:
            print(f"error fixing {path}: {e}")

    if fixed:
        print("Modified files:\n - " + "\n - ".join(sorted(set(fixed))))
    else:
        print("No conservative fixes applied.")


if __name__ == "__main__":
    main()
