import argparse
from pathlib import Path
from PIL import Image
import pytesseract
from .paths_loader import get_path


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
    def key(item):
        (x1, y1, x2, y2), txt = item
        return (y1, x1)
    ordered = sorted(tile_texts, key=key)
    merged = []
    for box, txt in ordered:
        merged.append(txt.strip())
    return "\n".join([s for s in merged if s])


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--in', dest='in_path', required=True)
    p.add_argument('--out-dir', dest='out_dir', default='ops')
    p.add_argument('--tile-w', type=int, default=1024)
    p.add_argument('--tile-h', type=int, default=1024)
    p.add_argument('--overlap', type=int, default=200)
    p.add_argument('--psm', type=int, default=11)
    args = p.parse_args()

    in_path = Path(args.in_path)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    im = Image.open(in_path).convert('RGB')
    # if a tesseract binary is configured, set pytesseract path
    tpath = get_path('tesseract')
    if tpath:
        try:
            pytesseract.pytesseract.tesseract_cmd = tpath
        except Exception:
            pass
    tiles = tile_image(im, args.tile_w, args.tile_h, args.overlap)

    tile_texts = []
    for idx, (box, tile) in enumerate(tiles):
        tile_fn = out_dir / f"{in_path.stem}.tess.tile{idx:03d}.png"
        tile.save(tile_fn)
        conf = f'--psm {args.psm} --oem 3'
        try:
            txt = pytesseract.image_to_string(tile, lang='jpn', config=conf)
        except Exception as e:
            txt = ''
        tile_out = out_dir / f"{in_path.stem}.tess.tile{idx:03d}.tess.txt"
        tile_out.write_text(txt, encoding='utf-8')
        tile_texts.append((box, txt))
    merged = simple_merge(tile_texts)
    merged_out = out_dir / f"{in_path.stem}.tess.tiled.psm{args.psm}.txt"
    merged_out.write_text(merged, encoding='utf-8')
    print('Wrote', merged_out)

if __name__ == '__main__':
    main()
