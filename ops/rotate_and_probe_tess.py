#!/usr/bin/env python3
"""
Rotate an input image (0/90/180/270), run tiled Tesseract + postprocess/score for each
rotation, and pick the best rotation by `after_noise_rate2_fix` (or fallback heuristic).

Usage: python ops/rotate_and_probe_tess.py --in INPUT.png [--psm 11] [--tmpdir ops/tmp]

Produces: INPUT.best_rotation.txt and prints a brief JSON summary to stdout.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from PIL import Image

# Allow large images for programmatic rotation/tiling in this probe script.
Image.MAX_IMAGE_PIXELS = None

def run_cmd(cmd, timeout=90):
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=timeout, universal_newlines=True)
        return out
    except subprocess.CalledProcessError as e:
        return e.output
    except subprocess.TimeoutExpired:
        return ''

def parse_json_from_stdout(s):
    m = re.search(r"\{.*\}", s, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--in', dest='infile', required=True)
    p.add_argument('--psm', type=int, default=11)
    p.add_argument('--tmpdir', default='ops/tmp')
    p.add_argument('--timeout', type=int, default=90)
    args = p.parse_args()

    infile = Path(args.infile)
    tmpdir = Path(args.tmpdir)
    tmpdir.mkdir(parents=True, exist_ok=True)

    if not infile.exists():
        print(json.dumps({'error':'input missing', 'in': str(infile)}))
        sys.exit(2)

    rotations = [0, 90, 180, 270]
    results = []

    for rot in rotations:
        stem = infile.stem + f'.rot{rot}'
        tmp_img = tmpdir / (stem + infile.suffix)
        with Image.open(infile) as im:
            rim = im.rotate(rot, expand=True)
            rim.save(tmp_img)

        # run tiled tesseract helper (keeps naming consistent with existing pipeline)
        cmd = [sys.executable, 'ops/tile_and_run_tesseract.py', '--in', str(tmp_img), '--psm', str(args.psm), '--out-dir', str(tmpdir)]
        out = run_cmd(cmd, timeout=args.timeout)
        tess_out = str(tmpdir / (tmp_img.stem + f'.tess.tiled.psm{args.psm}.txt'))
        score = None
        post_out = ''
        if Path(tess_out).exists():
            # run postprocess_and_score on the tess output to get KPIs
            cmd2 = [sys.executable, 'ops/postprocess_and_score.py', tess_out]
            post_out = run_cmd(cmd2, timeout=args.timeout)
            j = parse_json_from_stdout(post_out)
            if j and 'after_noise_rate2_fix' in j:
                score = j['after_noise_rate2_fix']

        # fallback heuristics: prefer lower score, else longer text
        length = 0
        if Path(tess_out).exists():
            try:
                length = Path(tess_out).read_text(encoding='utf-8', errors='ignore').strip()
                length = len(length)
            except Exception:
                length = 0

        results.append({
            'rot': rot,
            'tess_out': tess_out,
            'score': score,
            'length': length,
            'raw_stdout': out,
            'post_stdout': post_out,
        })

    # choose best: lowest score; if all None, choose longest length
    scored = [r for r in results if r['score'] is not None]
    if scored:
        best = min(scored, key=lambda r: r['score'])
    else:
        best = max(results, key=lambda r: r['length'])

    best_rot = best['rot']
    best_tess = best['tess_out']

    out_best = infile.with_suffix('')
    out_best = Path(str(out_best) + f'.best-rot{best_rot}.tess.txt')
    if Path(best_tess).exists():
        shutil.copy(best_tess, out_best)
    else:
        out_best.write_text('', encoding='utf-8')

    summary = {
        'input': str(infile),
        'best_rot': best_rot,
        'best_tess_out': str(best_tess),
        'candidates': [{k:v for k,v in r.items() if k!='raw_stdout' and k!='post_stdout'} for r in results]
    }
    print(json.dumps(summary, ensure_ascii=False))

if __name__ == '__main__':
    main()
