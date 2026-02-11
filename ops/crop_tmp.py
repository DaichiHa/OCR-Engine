from PIL import Image

im = Image.open(r"C:\\Users\\User\\Downloads\\PDF\\_img\\page_001.png")
w, h = im.size
box = (w - 800, h - 800, w, h)  # bottom-right 800x800
im.crop(box).save(r".\\ops\\debug_page001_crop_br.png")
print("saved crop")
