import argparse
import os

import cv2
import numpy as np
from PIL import Image as PILImage


def deskew_image(bgr):
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    _, thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    coords = cv2.findNonZero(255 - thr)
    if coords is None:
        return bgr
    rect = cv2.minAreaRect(coords)
    angle = rect[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    h, w = bgr.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        bgr, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )
    return rotated


def preprocess(
    in_path: str,
    out_path: str,
    scale: int,
    clahe_clip: float,
    clahe_tile: int,
    denoise_h: int,
):
    try:
        pil = PILImage.open(in_path).convert("RGB")
        img = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
    except Exception as e:
        raise SystemExit(f"failed to read input image: {in_path}\n{e}")

    if scale != 1:
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    if denoise_h > 0:
        img = cv2.fastNlMeansDenoisingColored(img, None, denoise_h, denoise_h, 7, 21)

    # deskewing is handled by module-level helper when requested in main

    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l_channel, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clahe_clip, tileGridSize=(clahe_tile, clahe_tile))
    cl = clahe.apply(l_channel)
    limg = cv2.merge((cl, a, b))
    final = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

    # optional binarize and deskew flags will be handled by CLI args in main

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
    p.add_argument(
        "--denoise-h",
        type=int,
        default=10,
        help="h parameter for NLMeans denoising; 0 to disable",
    )
    p.add_argument("--deskew", action="store_true", help="perform deskewing")
    p.add_argument(
        "--binarize",
        action="store_true",
        help="apply Otsu binarization at end",
    )
    args = p.parse_args()
    # run preprocess
    preprocess(
        args.in_path,
        args.out_path,
        args.scale,
        args.clahe_clip,
        args.clahe_tile,
        args.denoise_h,
    )
    # post-process deskew/binarize if requested
    if args.deskew or args.binarize:
        img = cv2.imread(args.out_path)
        if img is None:
            raise SystemExit(
                f"failed to read intermediate output for postprocessing: {args.out_path}"
            )
        if args.deskew:
            img = deskew_image(img)
        if args.binarize:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, bw = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            img = cv2.cvtColor(bw, cv2.COLOR_GRAY2BGR)
        ok = cv2.imwrite(args.out_path, img)
        if not ok:
            raise SystemExit(f"failed to write final output image: {args.out_path}")


if __name__ == "__main__":
    main()
