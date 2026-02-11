import sys
print('python_executable:', sys.executable)
# check cv2
try:
    import cv2
    print('cv2: found', getattr(cv2, '__version__', 'unknown'), cv2.__file__)
except Exception as e:
    print('cv2: missing', type(e).__name__, str(e))
# check PIL
try:
    import PIL
    print('PIL: found', PIL.__version__, PIL.__file__)
except Exception as e:
    print('PIL: missing', type(e).__name__, str(e))
