import argparse
import os
from pathlib import Path

from PIL import Image


def set_onednn_env(disable: bool):
    if not disable:
        return
    # Best-effort disable OneDNN before importing paddle-related libs
    os.environ["FLAGS_use_mkldnn"] = "0"
    os.environ["PADDLE_WITH_ONEDNN"] = "0"
    os.environ["PADDLE_DISABLE_ONEDNN"] = "1"
    os.environ["PADDLE_WITH_MKL"] = "0"


def tile_image(im: Image.Image, tile_w: int, tile_h: int, overlap: int):
    w, h = im.size
    step_x = tile_w - overlap
    step_y = tile_h - overlap
    tiles = []
    for y in range(0, max(1, h - overlap), step_y):
        for x in range(0, max(1, w - overlap), step_x):
            x2 = min(x + tile_w, w)
            y2 = min(y + tile_h, h)
            box = (x, y, x2, y2)
            tiles.append((box, im.crop(box)))
            if x2 == w:
                break
        if y2 == h:
            break
    return tiles


def simple_merge(tile_texts):
    # tile_texts: list of (box, text)
    # sort by top (y) then left (x)
    def key(item):
        (x1, y1, x2, y2), txt = item
        return (y1, x1)

    ordered = sorted(tile_texts, key=key)
    merged = []
    for box, txt in ordered:
        merged.append(txt.strip())
    return "\n".join([s for s in merged if s])


def main():
    p = argparse.ArgumentParser(
        description="Tile an image and run PaddleOCR on each tile"
    )
    p.add_argument("--in", dest="in_path", required=True)
    p.add_argument("--out-dir", dest="out_dir", default="ops")
    p.add_argument("--tile-w", type=int, default=1024)
    p.add_argument("--tile-h", type=int, default=1024)
    p.add_argument("--overlap", type=int, default=200)
    p.add_argument(
        "--disable-onednn",
        action="store_true",
        help="Try to disable OneDNN before import",
    )
    args = p.parse_args()

    in_path = Path(args.in_path)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    set_onednn_env(args.disable_onednn)

    try:
        from paddleocr import PaddleOCR
    except Exception as e:
        raise SystemExit(f"failed to import PaddleOCR: {e}")

    pocr = PaddleOCR(use_textline_orientation=False, lang="japan")

    im = Image.open(in_path).convert("RGB")
    tiles = tile_image(im, args.tile_w, args.tile_h, args.overlap)

    tile_texts = []
    for idx, (box, tile) in enumerate(tiles):
        tile_fn = out_dir / f"{in_path.stem}.tile{idx:03d}.png"
        tile.save(tile_fn)
        print(f"Wrote tile {tile_fn} box={box}")
        try:
            res = pocr.ocr(str(tile_fn))
        except Exception as e:
            print(f"PaddleOCR failed on tile {idx}: {e}")
            res = []
        texts = []
        for line in res:
            for item in line:
                text = (
                    item[1][0] if isinstance(item[1], (list, tuple)) else str(item[1])
                )
                texts.append(text)
        txt = "\n".join(texts)
        tile_out = out_dir / f"{in_path.stem}.tile{idx:03d}.ppocr.txt"
        tile_out.write_text(txt, encoding="utf-8")
        tile_texts.append((box, txt))
        print(f"Wrote {tile_out}")

    merged = simple_merge(tile_texts)
    merged_out = out_dir / f"{in_path.stem}.ppocr.tiled.txt"
    merged_out.write_text(merged, encoding="utf-8")
    print(f"Wrote merged output {merged_out}")


if __name__ == "__main__":
    main()
