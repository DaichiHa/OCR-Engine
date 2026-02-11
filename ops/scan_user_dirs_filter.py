import os, collections, re, sys

root = r"C:\Users\User"
target_sub = r"Downloads\\OCR-Engine"

groups = collections.defaultdict(list)
for dirpath, dirnames, filenames in os.walk(root):
    for d in dirnames:
        full = os.path.join(dirpath, d)
        key = re.sub(r'[^A-Za-z0-9]', '', d.lower())[:20]
        groups[key].append(full)

found = {k:v for k,v in groups.items() if any(target_sub in p.replace('/', '\\') for p in v)}
if not found:
    print('No groups under Downloads\\OCR-Engine found')
    sys.exit(0)
for k,v in sorted(found.items(), key=lambda x: -len(x[1])):
    print(f'Norm={k} Count={len(v)}')
    for p in v:
        if target_sub in p.replace('/', '\\'):
            print('  -', p)
    print()
