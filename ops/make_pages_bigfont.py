from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

pages = range(0, 4)
# try several common fonts
candidates = ["arial.ttf", "seguiemj.ttf", "meiryo.ttc", "YuGothM.ttc"]
font = None
for f in candidates:
    try:
        font = ImageFont.truetype(f, 48)
        break
    except Exception:
        font = None

if font is None:
    # fallback to default but bigger size
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None

for i in pages:
    name = f"page_{i:03d}_big_sample.png"
    im = Image.new("RGB", (1200, 1600), "white")
    d = ImageDraw.Draw(im)
    lines = [
        f"Page {i:03d} - Sample OCR test line {j+1}: The quick brown fox jumps over 13 lazy dogs." for j in range(12)
    ]
    y = 60
    for line in lines:
        if font:
            d.text((50, y), line, fill="black", font=font)
        else:
            d.text((50, y), line, fill="black")
        y += 64
    out = Path("ops") / name
    im.save(out)
    print("WROTE", out)
