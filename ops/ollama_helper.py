import json
import shutil
import subprocess
from pathlib import Path
from typing import Optional

# robust import: try relative first, fall back to top-level import
try:
    from .paths_loader import get_path
except Exception:
    try:
        from paths_loader import get_path
    except Exception:

        def get_path(name):
            return None


def load_config(path: str = "ops/ollama_config.json") -> dict:
    cfgp = Path(path)
    if not cfgp.exists():
        return {
            "host": None,
            "model": "llama2:latest",
            "timeout": 10,
            "use_cli": False,
        }
    try:
        return json.loads(cfgp.read_text(encoding="utf-8"))
    except Exception:
        return {
            "host": None,
            "model": "llama2:latest",
            "timeout": 10,
            "use_cli": False,
        }


def has_ollama_cli(cli_path: str = None) -> bool:
    if not cli_path:
        try:
            cli_path = get_path("ollama")
        except Exception:
            cli_path = None
    if cli_path:
        return Path(cli_path).exists()
    return shutil.which("ollama") is not None


def call_ollama_cli(
    model: str, prompt: str, timeout: int = 15, cli_path: str = None
) -> Optional[str]:
    exe = cli_path if cli_path else "ollama"
    base_cmds = [
        [exe, "run", model],
        [exe, "generate", model],
        [exe, "run", model, "--stdin"],
        [exe, "run", model, "--prompt", prompt],
        [exe, "generate", model, "--prompt", prompt],
        [exe, "chat", "--model", model, "--prompt", prompt],
        [exe, "run", model, "-p", prompt],
        [exe, "generate", model, "-p", prompt],
    ]

    import tempfile

    for base in base_cmds:
        trials = []
        if not any(x in base for x in ("--prompt", "-p", "--stdin")):
            trials.append((base, "stdin"))
        trials.append((base, "direct"))

        tmp = None
        try:
            tmpf = tempfile.NamedTemporaryFile(
                delete=False, mode="w", encoding="utf-8"
            )
            tmpf.write(prompt)
            tmpf.close()
            tmp = tmpf.name
            trials.append((base + ["--prompt-file", tmp], "direct"))
            trials.append((base + [tmp], "direct"))
            trials.append((base + ["-f", tmp], "direct"))
            trials.append((base + ["-i", tmp], "direct"))
        except Exception:
            tmp = None

        if prompt not in base:
            trials.append((base + [prompt], "direct"))

        for cmd, mode in trials:
            try:
                if mode == "stdin":
                    out_b = subprocess.check_output(
                        cmd,
                        input=prompt.encode("utf-8"),
                        stderr=subprocess.STDOUT,
                        timeout=timeout,
                        universal_newlines=False,
                    )
                    out = out_b.decode("utf-8", errors="replace")
                else:
                    out_b = subprocess.check_output(
                        cmd,
                        stderr=subprocess.STDOUT,
                        timeout=timeout,
                        universal_newlines=False,
                    )
                    out = out_b.decode("utf-8", errors="replace")
                if out:
                    if tmp:
                        try:
                            Path(tmp).unlink()
                        except Exception:
                            pass
                    return out
            except subprocess.CalledProcessError as e:
                out = e.output
                if isinstance(out, bytes):
                    out = out.decode("utf-8", errors="replace")
                if out and str(out).strip():
                    if tmp:
                        try:
                            Path(tmp).unlink()
                        except Exception:
                            pass
                    return out
            except FileNotFoundError:
                if tmp:
                    try:
                        Path(tmp).unlink()
                    except Exception:
                        pass
                return None
            except subprocess.TimeoutExpired:
                continue

        if tmp:
            try:
                Path(tmp).unlink()
            except Exception:
                pass
    return None


def call_ollama_http(
    model: str, prompt: str, host: str, timeout: int = 15
) -> Optional[str]:
    try:
        import requests
    except Exception:
        return None
    url = host.rstrip("/") + "/api/generate"
    payload = {"model": model, "prompt": prompt, "max_tokens": 256}
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        if r.status_code == 200:
            try:
                return r.json().get("text") or r.text
            except Exception:
                return r.text
        return None
    except Exception:
        return None


def generate(prompt: str, cfg: dict) -> Optional[str]:
    cli_path = (
        cfg.get("cli_path") or get_path("ollama")
        if isinstance(cfg, dict)
        else None
    )
    if cfg.get("use_cli", True) and has_ollama_cli(cli_path):
        # Try CLI invocations (prefer stdin first)
        res = call_ollama_cli(
            cfg.get("model", "llama2:latest"),
            prompt,
            timeout=cfg.get("timeout", 15),
            cli_path=cli_path,
        )
        if res:
            return res
    # try http
    http_host = cfg.get("host")
    if http_host:
        res = call_ollama_http(
            cfg.get("model", "llama2-mini"),
            prompt,
            http_host,
            timeout=cfg.get("timeout", 15),
        )
        if res:
            return res
    return None


def detect_cli_form(cli_path: str = None) -> str:
    """Return one of: 'generate', 'run', 'chat', or 'run-stdin' based on help text."""
    exe = cli_path if cli_path else "ollama"
    try:
        out = subprocess.check_output(
            [exe, "--help"],
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            timeout=5,
        )
    except Exception:
        return "run"
    low = out.lower()
    # prefer forms that explicitly mention stdin support
    if "--stdin" in low or "stdin" in low:
        return "run-stdin"
    if "generate" in low:
        return "generate"
    # detect explicit subcommands
    if "\n  chat\t" in out or "\n  chat " in out:
        return "chat"
    if "\n  run\t" in out or "\n  run " in out or "\n  run\n" in out:
        return "run"
    return "run"


def call_ollama_cli_with_form(
    model: str, prompt: str, form: str, timeout: int = 15, cli_path: str = None
) -> Optional[str]:
    exe = cli_path if cli_path else "ollama"
    if form == "generate":
        cmd = [exe, "generate", model, "--prompt", prompt]
    elif form == "run-stdin":
        cmd = [exe, "run", model, "--stdin"]
    elif form == "chat":
        cmd = [exe, "chat", "--model", model, "--prompt", prompt]
    else:
        # default run form
        cmd = [exe, "run", model, "--prompt", prompt]

    try:
        # if form expects stdin, pass prompt via input
        if "--stdin" in cmd:
            out_b = subprocess.check_output(
                cmd,
                input=prompt.encode("utf-8"),
                stderr=subprocess.STDOUT,
                timeout=timeout,
                universal_newlines=False,
            )
            out = out_b.decode("utf-8", errors="replace")
        else:
            out = subprocess.check_output(
                cmd,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                universal_newlines=True,
            )
        return out
    except subprocess.CalledProcessError as e:
        out = e.output
        if isinstance(out, bytes):
            out = out.decode("utf-8", errors="replace")
        return out
    except FileNotFoundError:
        return None
    except subprocess.TimeoutExpired:
        return None


if __name__ == "__main__":
    print("ollama_helper: run as library")
