from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

pages = range(0, 4)
for i in pages:
    name = f"page_{i:03d}_sample.png"
    im = Image.new("RGB", (1200, 1600), "white")
    d = ImageDraw.Draw(im)
    try:
        fnt = ImageFont.load_default()
    except Exception:
        fnt = None
    lines = [
        f"Page {i:03d} - Sample OCR test line {j+1}: The quick brown fox jumps over 13 lazy dogs." for j in range(20)
    ]
    y = 50
    for line in lines:
        d.text((50, y), line, fill="black", font=fnt)
        y += 32
    out = Path("ops") / name
    im.save(out)
    print("WROTE", out)
