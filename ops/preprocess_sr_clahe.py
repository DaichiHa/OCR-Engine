import argparse
import os
import cv2
import numpy as np
from PIL import Image as PILImage


def preprocess(in_path: str, out_path: str, scale: int, clahe_clip: float, clahe_tile: int, denoise_h: int):
    try:
        pil = PILImage.open(in_path).convert("RGB")
        img = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    except Exception as e:
        raise SystemExit(f"failed to read input image: {in_path}\n{e}")

    if scale != 1:
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    if denoise_h > 0:
        img = cv2.fastNlMeansDenoisingColored(img, None, denoise_h, denoise_h, 7, 21)

    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clahe_clip, tileGridSize=(clahe_tile, clahe_tile))
    cl = clahe.apply(l)
    limg = cv2.merge((cl, a, b))
    final = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    ok = cv2.imwrite(out_path, final)
    if not ok:
        raise SystemExit(f"failed to write output image: {out_path}")
    print(f"wrote: {out_path}")


def main():
    p = argparse.ArgumentParser(description="Simple SR + CLAHE preprocessing")
    p.add_argument("--in", dest="in_path", required=True)
    p.add_argument("--out", dest="out_path", required=True)
    p.add_argument("--scale", type=int, default=2, help="upscale factor (integer)")
    p.add_argument("--clahe-clip", type=float, default=2.0)
    p.add_argument("--clahe-tile", type=int, default=8)
    p.add_argument("--denoise-h", type=int, default=10, help="h parameter for NLMeans denoising; 0 to disable")
    args = p.parse_args()
    preprocess(args.in_path, args.out_path, args.scale, args.clahe_clip, args.clahe_tile, args.denoise_h)


if __name__ == "__main__":
    main()
