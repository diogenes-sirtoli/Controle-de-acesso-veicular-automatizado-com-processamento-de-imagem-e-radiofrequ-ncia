import os
os.environ['KMP_DUPLICATE_LIB_OK']='True'
import yolov5
import cv2
from easyocr import Reader
import time
import warnings
import torch
warnings.filterwarnings("ignore", category=UserWarning) 


# Model
#model = torch.hub.load("ultralytics/yolov5", 'custom', path='lastX.pt')
#model = torch.hub.load('./yolov5', 'custom', path='bestS.pt', source='local' )
#model = torch.hub.load('ultralytics/yolov5', 'yolov5s')  # or yolov5n - yolov5x6, custom
#model = yolov5.load('bestS.pt')
# Images
model = torch.hub.load("ultralytics/yolov5", 'custom', path='lastX.pt') #0.29 1.78
#model = yolov5.load('lastX.onnx') #0.27 #1.50
img = 'teste1.jpg'  # or file, Path, PIL, OpenCV, numpy, list
 
# parse results
#predictions = results.pred[0]
#boxes = predictions[:, :4] # x1, y1, x2, y2
#scores = predictions[:, 4]
#categories = predictions[:, 5]

lista_idiomas = "en"
idiomas = lista_idiomas.split(",")
gpu = False #@param {type:"boolean"}
fonte = '/content/fontes/calibri.ttf' #@param {type:"string"}
reader = Reader(idiomas, gpu=gpu)

tempo1 = time.time()
# Inference
results = model(img)
tempo = time.time() - tempo1
print("Tempo decorrido para encontrar placa: ")
print(tempo)
cv2.imwrite('ResultadoPlaca.jpg', results.save())
predictions = results.pred[0]
x1 = int(predictions[0][0].numpy())
y1 = int(predictions[0][1].numpy())
x2 = int(predictions[0][2].numpy())
y2 = int(predictions[0][3].numpy())
confiancaPlaca = float(predictions[0][4].numpy())

imgOriginal = cv2.imread("teste1.jpg")
#tempo1 = time.time()
#resultados = reader.readtext(imgOriginal)
#tempo = time.time() - tempo1
#print("Tempo decorrido: ")
#print(tempo)
#for r in resultados:
#print(r)
    
    
#placaRecordata = imgOriginal[int(y1*0.995):int(y2*1.005), int(x1*0.995):int(x2*1.005)]
placaRecordata = imgOriginal[y1:y2, x1:x2] 
#cv2.imshow("Resized image", placaRecordata)
cv2.imwrite('placaRecortada.jpg', placaRecordata)
# Results
results.show()  # or .show(), .save(), .crop(), .pandas(), etc.

placa = cv2.imread("placaRecortada.jpg")
#text = pytesseract.image_to_string(placa)


tempo1 = time.time()
resultados = reader.readtext(placa, allowlist = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
tempo = time.time() - tempo1
print("Tempo decorrido reconhecer texto: ")
print(tempo)
for r in resultados:
    print(r)
print(time.time())
