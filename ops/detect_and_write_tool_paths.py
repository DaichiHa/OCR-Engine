import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

root = Path(__file__).parent
out = root / "tools_paths.json"

executables = [
    "tesseract",
    "ollama",
    "conda",
    "python",
    "pip",
    "git",
    "docker",
]
packages = [
    "paddleocr",
    "paddle",
    "onnxruntime",
    "pytesseract",
    "rapidfuzz",
    "transformers",
]

results = {"executables": {}, "packages": {}}

for exe in executables:
    path = shutil.which(exe)
    info = {"path": path}
    if path:
        try:
            proc = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=10)
            ver = proc.stdout.strip() or proc.stderr.strip()
            info["version_probe"] = ver.splitlines()[0] if ver else ""
        except Exception:
            info["version_probe"] = ""
    results["executables"][exe] = info

for pkg in packages:
    spec = importlib.util.find_spec(pkg)
    if spec is None:
        results["packages"][pkg] = {"installed": False}
    else:
        info = {"installed": True}
        try:
            mod = __import__(pkg)
            ver = getattr(mod, "__version__", "")
            if not ver and hasattr(mod, "version"):
                ver = getattr(mod, "version")
            info["version"] = str(ver)
        except Exception:
            info["version"] = ""
        results["packages"][pkg] = info

with open(out, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("Wrote", out)
