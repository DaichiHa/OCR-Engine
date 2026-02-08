import json
import os
from pathlib import Path
import shutil
import subprocess

root = Path(__file__).parent
tools_json = root / 'tools_paths.json'
paths_config = root / 'paths_config.json'
inventory_csv = root / 'page_010_inventory.csv'
report_txt = root / 'page_010_cleanup_report.txt'
archive_dir = root / 'archive' / 'page_010'

common_tesseract = [
    Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
    Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
]

with open(tools_json, 'r', encoding='utf-8') as f:
    tools = json.load(f)

# Try common tesseract locations if not detected
if not tools['executables'].get('tesseract', {}).get('path'):
    for p in common_tesseract:
        if p.exists():
            tools['executables']['tesseract'] = {'path': str(p)}
            try:
                proc = subprocess.run([str(p), '--version'], capture_output=True, text=True, timeout=10)
                ver = proc.stdout.strip() or proc.stderr.strip()
                tools['executables']['tesseract']['version_probe'] = ver.splitlines()[0] if ver else ''
            except Exception:
                tools['executables']['tesseract']['version_probe'] = ''
            break

# Save updated tools JSON
with open(tools_json, 'w', encoding='utf-8') as f:
    json.dump(tools, f, indent=2, ensure_ascii=False)

# Create a simple paths_config.json used by scripts
paths = {k: v.get('path') for k, v in tools['executables'].items()}
with open(paths_config, 'w', encoding='utf-8') as f:
    json.dump(paths, f, indent=2, ensure_ascii=False)

# Prepare archive dir
archive_dir.mkdir(parents=True, exist_ok=True)

# Read inventory and decide keep list
keep = set()
if report_txt.exists():
    with open(report_txt, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip().startswith('- '):
                name = line.strip()[2:]
                # if line looks like ' - filename' and likely a kept suggestion
                if any(k in name for k in ['normalized','ensemble','.clean.txt','ollama.suggested','sample','resized','orig']):
                    keep.add(name)

# fallback: also keep any normalized/ensemble/clean/ollama.suggested files found in inventory csv
if inventory_csv.exists():
    import csv
    with open(inventory_csv, 'r', encoding='utf-8') as cf:
        reader = csv.DictReader(cf)
        for r in reader:
            fn = r['filename']
            if any(k in fn for k in ['normalized','ensemble','.clean.txt','ollama.suggested','sample','resized','orig']):
                keep.add(fn)

# Archive files starting with page_010 that are not in keep
moved = []
for p in root.iterdir():
    if p.name.startswith('page_010') and p.is_file():
        if p.name in keep:
            continue
        target = archive_dir / p.name
        # If target exists, add suffix
        if target.exists():
            i = 1
            while True:
                alt = archive_dir / f"{p.stem}.{i}{p.suffix}"
                if not alt.exists():
                    target = alt
                    break
                i += 1
        shutil.move(str(p), str(target))
        moved.append({'src': str(p), 'dest': str(target)})

# Write summary
summary = root / 'archive' / 'page_010_archive_summary.json'
with open(summary, 'w', encoding='utf-8') as f:
    json.dump({'moved': moved, 'kept': sorted(list(keep))}, f, indent=2, ensure_ascii=False)

print('Updated', tools_json)
print('Wrote', paths_config)
print('Archived', len(moved), 'files to', archive_dir)
print('Summary written to', summary)
