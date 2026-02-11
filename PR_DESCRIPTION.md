This PR includes: 

- Short subprocess timeouts and fail-fast behavior across `ops/` OCR scripts.
- Robust import fallbacks for optional LM-assisted postprocessing.
- Safer atomic archive/move logic.
- Helper scripts for environment checks and synthetic-page generation (no generated artifacts committed).

Note: Generated artifacts (images, tessdata, temp outputs) have been removed from tracking and are ignored via `.gitignore`. CI should be configured to upload artifacts to job storage rather than committing them to the repo.

Testing:
- Local smoke tests ran in `ocr-eng` conda environment.

Please review only code and docs in this branch; data/artifacts are intentionally excluded.