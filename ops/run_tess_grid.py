import itertools
import json
import subprocess
import sys
from pathlib import Path

COMBOS = {
    'scale': [2, 3],
    'clahe_clip': [1.5, 2.0],
    'clahe_tile': [4, 8],
    'denoise_h': [0, 8],
    'deskew': [False, True],
    'binarize': [False, True],
}


def run(cmd):
    print('RUN:', ' '.join(cmd))
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if r.returncode != 0:
            print('ERR:', r.stderr)
        return r
    except subprocess.TimeoutExpired as e:
        print('TIMEOUT:', ' '.join(cmd))
        class _R:
            returncode = -1
            stdout = ''
            stderr = f'TimeoutExpired after {e.timeout}s'
        return _R()
    except Exception as e:
        print('RUN ERROR:', e)
        class _R2:
            returncode = -2
            stdout = ''
            stderr = str(e)
        return _R2()


def main(smoke=False, assist=False):
    out_dir = Path('ops')
    out_dir.mkdir(exist_ok=True)
    keys = list(COMBOS.keys())
    values = [COMBOS[k] for k in keys]
    combos = list(itertools.product(*values))
    if smoke:
        combos = combos[:6]

    results = []
    for idx, combo in enumerate(combos, start=1):
        params = dict(zip(keys, combo))
        name = f'page_010_clahe_{idx}'
        out_img = out_dir / f'{name}.png'
        # build preprocess command
        cmd = [sys.executable, 'ops/preprocess_sr_clahe.py', '--in', 'ops/page_010_sample.png', '--out', str(out_img), '--scale', str(params['scale']), '--clahe-clip', str(params['clahe_clip']), '--clahe-tile', str(params['clahe_tile']), '--denoise-h', str(params['denoise_h'])]
        if params['deskew']:
            cmd.append('--deskew')
        if params['binarize']:
            cmd.append('--binarize')
        run(cmd)

        # run tiled tesseract
        cmd_t = [sys.executable, 'ops/tile_and_run_tesseract.py', '--in', str(out_img), '--out-dir', 'ops', '--tile-w', '1024', '--tile-h', '1024', '--overlap', '200', '--psm', '11']
        run(cmd_t)

        tess_txt = out_dir / f'{name}.tess.tiled.psm11.txt'
        # score tesseract output
        cmd_score = [sys.executable, 'ops/postprocess_and_score.py', str(tess_txt)]
        r = run(cmd_score)
        summary = None
        if r.returncode == 0:
            # parse last JSON-ish block from stdout
            out = r.stdout
            try:
                # find first '{' and parse JSON
                j = out[out.find('{'):]
                summary = json.loads(j)
            except Exception:
                summary = {'error': 'parse_failed', 'raw': out}

        entry = {'idx': idx, 'name': name, 'params': params, 'tesseract': summary}

        # if rapid normalized exists for this name, ensemble and score
        rapid_norm = out_dir / f'{name}.rapid.normalized.txt'
        tess_norm = out_dir / f'{name}.tess.tiled.psm11.normalized.txt'
        if rapid_norm.exists() and tess_norm.exists():
            cmd_ens = [sys.executable, 'ops/ensemble_and_score.py', str(rapid_norm), str(tess_norm)]
            r2 = run(cmd_ens)
            # attempt to parse JSON from stdout
            ens_summary = None
            if r2.returncode == 0:
                txt = r2.stdout
                try:
                    ens_json = txt[txt.find('{'):]
                    ens_summary = json.loads(ens_json)
                except Exception:
                    ens_summary = {'raw': txt}
            entry['ensemble'] = ens_summary

        # optional Ollama assist step: run assist CLI on best available cleaned text
        if assist:
            assist_in = None
            # prefer ensemble clean if present
            ensemble_clean = out_dir / f'{name}.rapid.normalized.ensemble.clean.txt'
            if ensemble_clean.exists():
                assist_in = ensemble_clean
            elif tess_norm.exists():
                assist_in = tess_norm
            elif rapid_norm.exists():
                assist_in = rapid_norm

            if assist_in:
                cmd_assist = [sys.executable, 'ops/assist_with_ollama.py', '--in', str(assist_in)]
                r3 = run(cmd_assist)
                assist_summary = None
                if r3.returncode == 0:
                    try:
                        assist_summary = json.loads(r3.stdout)
                    except Exception:
                        assist_summary = {'raw': r3.stdout}
                else:
                    try:
                        assist_summary = json.loads(r3.stdout)
                    except Exception:
                        assist_summary = {'error': 'assist_failed', 'rc': r3.returncode, 'out': r3.stdout}
                entry['assist'] = assist_summary

        results.append(entry)

    (out_dir / 'clahe_grid_tess_results.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
    print('WROTE ops/clahe_grid_tess_results.json')


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--smoke', action='store_true')
    p.add_argument('--assist', action='store_true', help='Run Ollama assist on cleaned outputs when available')
    args = p.parse_args()
    main(smoke=args.smoke, assist=args.assist)
