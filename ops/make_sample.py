from PIL import Image

im = Image.new("RGB", (1200, 1600), "white")
im.save("ops/page_010_sample.png")
print("WROTE ops/page_010_sample.png")
