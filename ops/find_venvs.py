import os
from pathlib import Path

roots = [Path(r"C:/Users/User/Downloads/OCR-Engine"), Path.home()]
# also check common subfolders under home
subdirs = [
    ".virtualenvs",
    "Envs",
    "venvs",
    ".venv",
    "Projects",
    "Documents",
    "source",
    "repos",
]
found = []


def scan(path, maxdepth=4):
    path = Path(path)
    try:
        for root, dirs, files in os.walk(path):
            depth = len(Path(root).relative_to(path).parts)
            if "pyvenv.cfg" in files:
                found.append(root)
            if depth >= maxdepth:
                # don't recurse deeper
                dirs[:] = []
    except Exception:
        pass


print("Scanning workspace and common user locations for virtualenvs...")
# scan workspace root shallow
scan(roots[0], maxdepth=6)
# scan specific candidate dirs under home
for sd in subdirs:
    p = Path.home() / sd
    if p.exists():
        scan(p, maxdepth=6)
# also scan top-level home children shallow
for child in Path.home().iterdir():
    if child.is_dir():
        scan(child, maxdepth=2)

found = sorted(set(found))
if not found:
    print("No virtualenvs (pyvenv.cfg) found in scanned locations.")
else:
    print("Found virtualenv roots:")
    for f in found:
        print(f)
