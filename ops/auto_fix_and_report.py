#!/usr/bin/env python3
"""
Auto-fix and reporting for merged OCR outputs.

Reads per-page merged_post.md (or merged.md), computes simple KPIs,
applies normalization and common OCR-fix rules, writes fixed output
and a JSON report with before/after metrics.

Usage: python ops/auto_fix_and_report.py --pages page_001 page_010 page_100
"""
import argparse
import json
import re
import unicodedata
from pathlib import Path


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding='utf-8', errors='ignore')


def write_text(path: Path, s: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(s, encoding='utf-8')


def jp_noise_metrics(s: str):
    # remove whitespace for rates
    c = re.sub(r"[\s]", "", s)
    total = max(1, len(c))
    jp = len(re.findall(r'[\u3040-\u30ff\u3400-\u9fff]', c))
    non_allowed = len(re.findall(r"[^0-9A-Za-z\u3040-\u30ff\u3400-\u9fff,。.、\-\(%)]", c))
    return {
        'chars': len(c),
        'jp_rate2_fix': round(jp / total, 6),
        'noise_rate2_fix': round(non_allowed / total, 6),
    }


COMMON_MAP = {
    '\u2019': "'",
    '\u201c': '"',
    '\u201d': '"',
}


def normalize_text(s: str) -> str:
    # Unicode normalization
    s = unicodedata.normalize('NFKC', s)
    # map common characters
    for k, v in COMMON_MAP.items():
        s = s.replace(k, v)
    # fix repeated spaces and stray control chars
    s = re.sub(r'[\x00-\x1f\x7f]+', '', s)
    s = re.sub(r'[ \t]+', ' ', s)
    # collapse multiple punctuation
    s = re.sub(r'([。.,、\-]){2,}', r'\1', s)
    return s.strip()


def numeric_corrections_linewise(s: str) -> str:
    lines = s.splitlines()
    out = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            out.append(line)
            continue
        # If the line looks like a numeric table or pure number, apply fixes
        if re.fullmatch(r'[\dOIl\s,\.\%\-\+()]+', stripped):
            # common OCR confusions: O->0, I or l -> 1 when adjacent to digits
            t = re.sub(r'O', '0', stripped)
            t = re.sub(r'(?<=\d)[Il](?=\d)', '1', t)
            # normalize multiple spaces and fix comma placements (simple)
            t = re.sub(r'\s+', ' ', t)
            out.append(t)
        else:
            out.append(line)
    return '\n'.join(out)


def auto_fix(s: str) -> str:
    s1 = normalize_text(s)
    s2 = numeric_corrections_linewise(s1)
    # small heuristics: fix isolated O as 0 inside digit clusters
    s3 = re.sub(r'(?<=\d)O(?=\d)', '0', s2)
    return s3


def process_page(page_tag: str, out_dir: Path):
    # locate merged_post.md or merged.md
    merged_post = Path('ops') / f'merge_{page_tag}' / 'merged_post.md'
    if not merged_post.exists():
        merged_post = Path('ops') / f'merge_{page_tag}' / 'merged.md'
    if not merged_post.exists():
        # try baseline folder
        merged_post = Path('ops') / f'baseline_{page_tag}' / 'mini_page_{page_tag.replace("page_","")}_r1-1_ink0p010.md'
    text = read_text(merged_post)
    before = jp_noise_metrics(text)
    fixed = auto_fix(text)
    after = jp_noise_metrics(fixed)

    out_base = out_dir / f'{page_tag}'
    out_base.mkdir(parents=True, exist_ok=True)
    write_text(out_base / 'merged_auto.md', fixed)
    write_text(out_base / 'merged_auto_raw.md', text)

    return {
        'page': page_tag,
        'source': str(merged_post),
        'before': before,
        'after': after,
        'out_fixed': str(out_base / 'merged_auto.md')
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--pages', nargs='+', required=True)
    p.add_argument('--out', default='ops/auto_fix_reports')
    args = p.parse_args()
    out_dir = Path(args.out)
    report = {'pages': []}
    for page in args.pages:
        res = process_page(page, out_dir)
        report['pages'].append(res)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Wrote report to', out_dir / 'report.json')


if __name__ == '__main__':
    main()
