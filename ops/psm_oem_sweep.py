#!/usr/bin/env python3
"""Run PSM/OEM sweep using the workspace Python executable and collect KPIs.

Creates `test_ocr_sweep/*` folders and writes `test_ocr_sweep/summary.csv`.
"""
import os
import sys
import subprocess
import time
import csv
import glob
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
IMG = r"C:\Users\User\Downloads\PDF\_img\page_001.png"
OUT_ROOT = os.path.join(ROOT, 'test_ocr_sweep')
PSMS = [3, 6, 7, 11]
OEMS = [0, 1, 2, 3]

os.makedirs(OUT_ROOT, exist_ok=True)

rows = []
for psm in PSMS:
    for oem in OEMS:
        outdir = os.path.join(OUT_ROOT, f'psm{psm}_oem{oem}_py')
        os.makedirs(outdir, exist_ok=True)
        env = os.environ.copy()
        env['TESS_PSM'] = str(psm)
        env['TESS_OEM'] = str(oem)
        env['TESS_TIMEOUT'] = '30'
        env['TESS_DIGIT_2PASS'] = '1'

        cmd = [sys.executable, os.path.join(ROOT, 'ops', 'mini_runner.py'), '--page', IMG, '--out', outdir, '--page-only', '--lang', 'jpn+eng']
        start = time.time()
        with open(os.path.join(outdir, 'out.txt'), 'wb') as fout, open(os.path.join(outdir, 'err.txt'), 'wb') as ferr:
            try:
                proc = subprocess.run(cmd, env=env, stdout=fout, stderr=ferr, timeout=120)
            except subprocess.TimeoutExpired:
                # record a long-running timeout and continue
                proc = None
                ferr.write(b'TimeoutExpired')
        elapsed = round(time.time() - start, 3)

        # find MD
        md_files = glob.glob(os.path.join(outdir, '**', 'mini*.md'), recursive=True)
        jp = ''
        noise = ''
        if md_files:
            with open(md_files[0], 'r', encoding='utf-8', errors='ignore') as f:
                txt = f.read()
            m = re.search(r'jp_rate2_fix=\s*([0-9.]+)', txt)
            if m:
                jp = m.group(1)
            m2 = re.search(r'noise_rate2_fix=\s*([0-9.]+)', txt)
            if m2:
                noise = m2.group(1)

        rows.append({'psm': psm, 'oem': oem, 'jp_rate': jp or '0', 'noise_rate': noise or '999', 'elapsed_s': str(elapsed), 'md': md_files[0] if md_files else ''})

summary_csv = os.path.join(OUT_ROOT, 'summary.csv')
with open(summary_csv, 'w', newline='', encoding='utf-8') as csvf:
    writer = csv.DictWriter(csvf, fieldnames=['psm', 'oem', 'jp_rate', 'noise_rate', 'elapsed_s', 'md'])
    writer.writeheader()
    for r in rows:
        writer.writerow(r)

print('WROTE:', summary_csv)

# print top 5
rows_sorted = sorted(rows, key=lambda r: (-float(r['jp_rate']), float(r['noise_rate']), float(r['elapsed_s'])))
print('\n--- Top 5 PSM/OEM ---')
for r in rows_sorted[:5]:
    print(r)

sys.exit(0)
