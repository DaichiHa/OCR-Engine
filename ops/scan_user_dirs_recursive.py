import os
import collections
import re
import sys

def norm(name):
    s = re.sub(r'[^A-Za-z0-9]', '', name.lower())
    return s[:20]

def main():
    root = r"C:\Users\User"
    max_depth = 3
    groups = collections.defaultdict(list)
    for dirpath, dirnames, filenames in os.walk(root):
        depth = dirpath.count(os.sep) - root.count(os.sep)
        if depth > max_depth:
            # don't recurse deeper
            dirnames[:] = []
            continue
        for d in dirnames:
            k = norm(d)
            groups[k].append(os.path.join(dirpath, d))
    cand = {k: v for k, v in groups.items() if len(v) > 2}
    if not cand:
        print('No recursive duplicate-name groups found (depth<=3).')
        return 0
    for k, v in sorted(cand.items(), key=lambda x: -len(x[1])):
        print(f'Norm={k} Count={len(v)}')
        for p in v[:50]:
            print('  -', p)
        print()
    return 0

if __name__ == '__main__':
    sys.exit(main())
