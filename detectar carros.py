import yolov5
import torch
import time
import cv2

# Model
model = yolov5.load('yolov5s.pt') 

# Images
img = ('D:/Imagens/placas/fotos26/1.jpg')  # or file, Path, PIL, OpenCV, numpy, list
#img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

tempo1 = time.time()
# Inference
results = model(img)
#results = model(img,size=256)
tempo = time.time() - tempo1
print("Tempo decorrido: ")
print(tempo)

# Results
#results.show()  # or .show(), .save(), .crop(), .pandas(), etc.
print(results.xyxy[0][0])
print(len(results.xyxy[0][0])) #número de colunas
print(len(results.xyxy[0])) #número de linhas
cv2.imwrite('D:/Imagens/placas/fotos26/Resultado.jpg', results.save())

   
cont = 0
if (len(results.xyxy[0]) >= 0):
    while(cont < (len(results.xyxy[0]))):
        __,__,__,__,confianca,classe = results.xyxy[0][cont].numpy() #salva valores de % e tipo de objeto
        numeroClasse = int(classe) #pega o número do tipo da classe
        print("Numero da classe: ",numeroClasse)
        nomeClasse = results.names[int(classe)] #pega o tipo da classe
        print("Nome da classe: "+nomeClasse+" | Confiança: "+str(confianca))
        if nomeClasse == "car":
            print("############# Tem carro! #############")
        else:
            print("############# Não tem carro! #############")
        cont += 1
else:
    print("############# Não tem carro! #############")
