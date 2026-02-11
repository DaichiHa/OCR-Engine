from PIL import Image
im=Image.open(r'C:\Users\User\Downloads\PDF\_img\page_001.png').convert('L')
im.resize((im.width*2, im.height*2), Image.LANCZOS).save(r'.\ops\debug_page001_res2x.png')
im.resize((im.width*3, im.height*3), Image.LANCZOS).save(r'.\ops\debug_page001_res3x.png')
print('saved')
