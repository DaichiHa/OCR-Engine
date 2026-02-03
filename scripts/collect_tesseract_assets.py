"""Collect local Tesseract executable and tessdata into the repo's vendor folder.

Usage: run this on the machine where Tesseract is installed. It will copy
`tesseract.exe` (if found) and the `tessdata` folder files (only traineddata)
into `vendor/tesseract/` and write a `manifest.json` describing included files.

Be careful: adding binaries to git increases repo size. Review before pushing.
"""
import json
import shutil
from pathlib import Path


def find_tesseract_root() -> Path | None:
    candidates = [
        Path("C:/Program Files/Tesseract-OCR"),
        Path("C:/Program Files (x86)/Tesseract-OCR"),
    ]
    for p in candidates:
        if p.exists() and (p / "tesseract.exe").exists():
            return p
    # fallback: try PATH
    from shutil import which

    exe = which("tesseract")
    if exe:
        return Path(exe).parent
    return None


def collect(root: Path, out_root: Path):
    out_root.mkdir(parents=True, exist_ok=True)
    manifest = {"source": str(root), "files": []}

    exe = root / "tesseract.exe"
    if exe.exists():
        shutil.copy2(exe, out_root / exe.name)
        manifest["files"].append(str(out_root / exe.name))

    tess = root / "tessdata"
    if tess.exists():
        target_tess = out_root / "tessdata"
        target_tess.mkdir(exist_ok=True)
        for f in tess.glob("*.traineddata"):
            shutil.copy2(f, target_tess / f.name)
            manifest["files"].append(str(target_tess / f.name))

    # copy LICENSE and README if exists
    for nm in ("LICENSE", "README", "readme.txt"):
        p = root / nm
        if p.exists():
            shutil.copy2(p, out_root / p.name)
            manifest["files"].append(str(out_root / p.name))

    with open(out_root / "manifest.json", "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    return manifest


def main():
    root = find_tesseract_root()
    if not root:
        print("Tesseract not found on this machine.")
        return
    out_root = Path(__file__).resolve().parent.parent / "vendor" / "tesseract"
    manifest = collect(root, out_root)
    print("Collected files:")
    for f in manifest["files"]:
        print(" -", f)
    print("Written manifest to:", out_root / "manifest.json")


if __name__ == "__main__":
    main()
