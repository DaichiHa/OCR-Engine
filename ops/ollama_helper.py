import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from .paths_loader import get_path


def load_config(path: str = 'ops/ollama_config.json') -> dict:
    cfgp = Path(path)
    if not cfgp.exists():
        return { 'host': 'http://127.0.0.1:11434', 'model': 'llama2-mini', 'timeout': 15, 'use_cli': True }
    return json.loads(cfgp.read_text(encoding='utf-8'))


def has_ollama_cli(cli_path: str = None) -> bool:
    # prefer configured path if available
    if not cli_path:
        cli_path = get_path('ollama')
    if cli_path:
        return Path(cli_path).exists()
    return shutil.which('ollama') is not None


def call_ollama_cli(model: str, prompt: str, timeout: int = 15, cli_path: str = None) -> Optional[str]:
    # Try several plausible ollama CLI invocation patterns until one works.
    exe = cli_path if cli_path else 'ollama'
    candidate_cmds = [
        [exe, 'generate', model, '--prompt', prompt],
        [exe, 'run', model, '--prompt', prompt],
        [exe, 'chat', '--model', model, '--prompt', prompt],
        [exe, 'run', model, '--stdin']
    ]
    for cmd in candidate_cmds:
        try:
            out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=timeout, universal_newlines=True)
            if out:
                return out
        except subprocess.CalledProcessError as e:
            # capture output for debugging but try next form
            out = e.output
            if out and out.strip():
                return out
        except FileNotFoundError:
            return None
        except subprocess.TimeoutExpired:
            continue
    return None


def call_ollama_http(model: str, prompt: str, host: str, timeout: int = 15) -> Optional[str]:
    try:
        import requests
    except Exception:
        return None
    url = host.rstrip('/') + f'/api/generate'
    payload = {
        'model': model,
        'prompt': prompt,
        'max_tokens': 256
    }
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        if r.status_code == 200:
            try:
                return r.json().get('text') or r.text
            except Exception:
                return r.text
        return None
    except Exception:
        return None


def generate(prompt: str, cfg: dict) -> Optional[str]:
    # Prefer CLI if configured and available, else HTTP if requests is present.
    cli_path = cfg.get('cli_path') or get_path('ollama')
    if cfg.get('use_cli', True) and has_ollama_cli(cli_path):
           # detect best CLI invocation form
           form = detect_cli_form(cli_path)
           return call_ollama_cli_with_form(cfg.get('model', 'llama2:latest'), prompt, form, timeout=cfg.get('timeout', 15), cli_path=cli_path)
    # try http
    http_host = cfg.get('host')
    if http_host:
        res = call_ollama_http(cfg.get('model', 'llama2-mini'), prompt, http_host, timeout=cfg.get('timeout', 15))
        if res:
            return res
    return None


def detect_cli_form(cli_path: str = None) -> str:
    """Return one of: 'generate', 'run', 'chat', or 'run-stdin' based on help text."""
    exe = cli_path if cli_path else 'ollama'
    try:
        out = subprocess.check_output([exe, '--help'], stderr=subprocess.STDOUT, universal_newlines=True, timeout=5)
    except Exception:
        return 'run'
    low = out.lower()
    if 'generate' in low:
        return 'generate'
    if '\n  run\t' in out or '\n  run ' in out or '\n  run\n' in out:
        return 'run'
    if '\n  chat\t' in out or '\n  chat ' in out:
        return 'chat'
    return 'run'


def call_ollama_cli_with_form(model: str, prompt: str, form: str, timeout: int = 15, cli_path: str = None) -> Optional[str]:
    exe = cli_path if cli_path else 'ollama'
    if form == 'generate':
        cmd = [exe, 'generate', model, '--prompt', prompt]
    elif form == 'run-stdin':
        cmd = [exe, 'run', model, '--stdin']
    elif form == 'chat':
        cmd = [exe, 'chat', '--model', model, '--prompt', prompt]
    else:
        # default run form
        cmd = [exe, 'run', model, '--prompt', prompt]

    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=timeout, universal_newlines=True)
        return out
    except subprocess.CalledProcessError as e:
        # return stdout/stderr text for debugging
        return e.output
    except FileNotFoundError:
        return None
    except subprocess.TimeoutExpired:
        return None


if __name__ == '__main__':
    print('ollama_helper: run as library')
