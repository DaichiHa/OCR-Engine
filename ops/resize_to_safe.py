#!/usr/bin/env python3
"""
Resize an image so its pixel count is below Pillow's MAX_IMAGE_PIXELS safety limit.

Usage: python ops/resize_to_safe.py --in INPUT.png [--out OUT.png] [--max-pixels 178956970]
Prints a JSON summary with output path and new dimensions.
"""

import argparse
import json
from pathlib import Path

from PIL import Image

# Temporarily allow large images so we can resize them programmatically.
Image.MAX_IMAGE_PIXELS = None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--in", dest="infile", required=True)
    p.add_argument("--out", dest="outfile")
    p.add_argument("--max-pixels", type=int, default=178956970)
    args = p.parse_args()

    infile = Path(args.infile)
    if not infile.exists():
        print(json.dumps({"error": "missing input", "in": str(infile)}))
        return 2

    out = (
        Path(args.outfile)
        if args.outfile
        else infile.with_name(infile.stem + ".resized" + infile.suffix)
    )

    with Image.open(infile) as im:
        w, h = im.size
        pixels = w * h
        if pixels <= args.max_pixels:
            im.save(out)
            print(
                json.dumps({"out": str(out), "w": w, "h": h, "pixels": pixels})
            )
            return 0

        scale = (args.max_pixels / float(pixels)) ** 0.5
        scale = scale * 0.95
        nw = max(1, int(w * scale))
        nh = max(1, int(h * scale))
        rim = im.resize((nw, nh), Image.LANCZOS)
        rim.save(out)
        print(
            json.dumps({"out": str(out), "w": nw, "h": nh, "pixels": nw * nh})
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
