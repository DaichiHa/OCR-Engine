# `ops/paths_config.json`

This file centralizes absolute paths and CLI forms for tools used by the `ops/` scripts (Tesseract, Ollama, etc.). The repo scripts load this at runtime via `ops.paths_loader` so CI and local runs behave consistently.

Minimal recommended structure:

```json
{
  "tesseract": "C:/Program Files/Tesseract-OCR/tesseract.exe",
  "ollama": "C:/Users/User/AppData/Local/Programs/Ollama/ollama.exe",
  "python": "C:/path/to/python.exe"
}
```

Notes:
- Prefer absolute paths on CI agents to avoid `PATH` differences.
- If a tool is optional in a particular environment, you may leave its value empty (scripts will fall back where implemented).
- Keep this file under `ops/` and do not expose secrets here.

Usage:
- Scripts use `from ops import paths_loader` and `paths_loader.get_path('tesseract')` to obtain values.
