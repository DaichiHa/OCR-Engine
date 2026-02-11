import collections
import os
import sys


def main():
    p = r"C:\Users\User"
    try:
        dirs = [name for name in os.listdir(p) if os.path.isdir(os.path.join(p, name))]
    except Exception as e:
        print("ERROR", e)
        return 2
    groups = collections.defaultdict(list)
    for name in dirs:
        key = name.lower()[:12]
        groups[key].append(name)
    cand = {k: v for k, v in groups.items() if len(v) > 1}
    if not cand:
        print("No top-level duplicate-prefix groups found.")
        return 0
    for k, v in sorted(cand.items(), key=lambda x: -len(x[1])):
        print(f"Prefix={k} Count={len(v)}")
        for item in v:
            print("  -", item)
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
