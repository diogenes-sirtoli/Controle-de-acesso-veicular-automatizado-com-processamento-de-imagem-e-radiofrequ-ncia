import yolov5
import torch
import time
import cv2

# Model
#model = torch.hub.load('ultralytics/yolov5', 'yolov5x')  # or yolov5n - yolov5x6, custom
#model = yolov5.load('yolov5s.pt') #2.08 0.66  #0.49
model = yolov5.load('yolov5x.pt') #0,49

# Images
img = 'test.jpg'  # or file, Path, PIL, OpenCV, numpy, list

#img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


tempo1 = time.time()
# Inference
results = model(img)
#results = model(img,size=256)
tempo = time.time() - tempo1
print("Tempo decorrido: ")
print(tempo)

# Results
results.show()  # or .show(), .save(), .crop(), .pandas(), etc.
print(results.xyxy[0][0])
print(len(results.xyxy[0][0])) #número de colunas
print(len(results.xyxy[0])) #número de linhas
cv2.imwrite('Resultado2.jpg', results.save())

#objetos = len(results.xyxy) #quantos objetos achados : carros, person etc
#print(objetos)
#for results in range(objetos):
#    quantidade = len(results.xyxy[0]) #quanto de cada objeto em cada posição
#    print(quantidade)
    
    
   #for quantidadeObjeto in results
   #     __,__,__,__,confianca,classe = results.xyxy[objetos][1].numpy() #salva valores de % e tipo de objeto
   #     nomeClasse = results.names[int(classe)] #pega o tipo da classe
   #     if nomeClasse == "car"