from pathlib import Path
import re


def process_file(p: Path):
    text = p.read_text(encoding='utf-8', errors='ignore')
    orig = text
    lines = text.splitlines()
    changed = False

    # Fix lambdas that rename param to 'line' but still use 'l'
    for i, ln in enumerate(lines):
        if 'lambda line' in ln:
            new = re.sub(r"\bl\b", 'line', ln)
            if new != ln:
                lines[i] = new
                changed = True

    # Fix for-line cases where 'for line in' but body still uses 'l'
    for i, ln in enumerate(lines):
        if re.search(r'for\s+line\s+in\b', ln):
            # scan next 10 lines for uses of 'line'
            for j in range(i+1, min(i+11, len(lines))):
                if re.search(r"\bl\.strip\(|\bl\b", lines[j]):
                    lines[j] = re.sub(r"\bl\b", 'line', lines[j])
                    changed = True

    # Fix comprehension patterns: if line.strip() -> line.strip()
    text2 = '\n'.join(lines)
    text3 = re.sub(r"(for\s+line\s+in[^\n]*if\s*)l\.strip\(\)", r"\1line.strip()", text2)
    if text3 != text2:
        text2 = text3
        changed = True

    # Fix total_words generator using wrong var
    text4 = re.sub(r"re\.findall\([^\)]*,\s*l\)\s*for\s+line\s+in", lambda m: m.group(0).replace(', l)', ', line)'), text2)
    if text4 != text2:
        text2 = text4
        changed = True

    # Fix lines.append(line) when for line in used
    text5 = re.sub(r"for\s+line\s+in[\s\S]*?lines\.append\(line\)", lambda m: m.group(0).replace('append(line)', 'append(line)'), text2)
    if text5 != text2:
        text2 = text5
        changed = True

    # Fix box = [line, t, line + w, ...] when line is numeric coordinate
    if 'line = int(' in text2 and 'box = [line,' in text2:
        text6 = text2.replace('box = [line,', 'box = [line,')
        if text6 != text2:
            text2 = text6
            changed = True

    if changed and text2 != orig:
        bak = p.with_suffix(p.suffix + '.bak-rename')
        p.write_text(text2, encoding='utf-8')
        bak.write_text(orig, encoding='utf-8')
        return True
    return False


def main():
    root = Path('.')
    py_files = list(root.rglob('*.py'))
    modified = []
    for p in py_files:
        # skip venv and hidden folders
        if any(part.startswith('.') or part in ('venv', '__pycache__') for part in p.parts):
            continue
        try:
            if process_file(p):
                modified.append(str(p))
        except Exception:
            continue
    if modified:
        print('Modified files:\n - ' + '\n - '.join(modified))
    else:
        print('No files modified')


if __name__ == '__main__':
    main()