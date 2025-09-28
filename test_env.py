import cv2
import torch
from easyocr import Reader

print("OpenCV:", cv2.__version__)
print("Torch:", torch.__version__)
r = Reader(['pt', 'en'])
print("EasyOCR OK")
