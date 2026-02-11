import collections
import os
import re
import shutil

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "ops", "local_artifacts")
EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "ops/local_artifacts",
    "node_modules",
}


def norm(name):
    return re.sub(r"[^A-Za-z0-9]", "", name.lower())[:30]


def gather():
    groups = collections.defaultdict(list)
    for dirpath, dirnames, filenames in os.walk(ROOT):
        # skip excluded paths
        rel = os.path.relpath(dirpath, ROOT)
        if rel.startswith("."):
            continue
        if any(part in EXCLUDE_DIRS for part in rel.split(os.sep)):
            dirnames[:] = []
            continue
        for d in list(dirnames):
            if d in EXCLUDE_DIRS:
                continue
            full = os.path.join(dirpath, d)
            # only consider directories directly under project or one level deep
            depth = full.count(os.sep) - ROOT.count(os.sep)
            if depth > 4:
                continue
            groups[norm(d)].append(full)
    return {k: v for k, v in groups.items() if len(v) > 1}


def ensure_out():
    os.makedirs(OUT, exist_ok=True)


def move_groups(groups):
    moved = []
    for key, paths in groups.items():
        target_group = os.path.join(OUT, key)
        os.makedirs(target_group, exist_ok=True)
        for p in paths:
            name = os.path.basename(p)
            dest = os.path.join(target_group, name)
            # if dest exists, make a unique suffix
            if os.path.exists(dest):
                i = 1
                while os.path.exists(dest + f"_{i}"):
                    i += 1
                dest = dest + f"_{i}"
            print(f"Moving: {p} -> {dest}")
            shutil.move(p, dest)
            moved.append((p, dest))
    return moved


def main():
    ensure_out()
    groups = gather()
    if not groups:
        print("No candidate groups found to consolidate.")
        return 0
    print("Found groups:")
    for k, v in groups.items():
        print(f" - {k}: {len(v)} items")
    print("\nProceeding to move all found groups into ops/local_artifacts/")
    moved = move_groups(groups)
    print(f"Completed moves: {len(moved)} items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
