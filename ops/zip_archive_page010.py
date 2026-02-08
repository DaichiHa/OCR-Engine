import zipfile
from pathlib import Path
root = Path(__file__).parent
archive_dir = root / 'archive' / 'page_010'
out = root / 'archive' / 'page_010_archive.zip'
with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as z:
    for p in sorted(archive_dir.rglob('*')):
        z.write(p, p.relative_to(archive_dir.parent))
print('Wrote', out)
