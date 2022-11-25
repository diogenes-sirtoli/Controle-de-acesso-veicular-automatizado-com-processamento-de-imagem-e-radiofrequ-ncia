import os
os.environ['KMP_DUPLICATE_LIB_OK']='True'
from easyocr import Reader
import cv2
from PIL import ImageFont, ImageDraw, Image
import numpy as np
import time
import warnings
warnings.filterwarnings("ignore", category=UserWarning) 

def fundo_texto(texto, x, y, img, fonte, tamanho=32, cor_fundo=(200, 255, 0)):
  fundo = np.full((img.shape), (0,0,0), dtype=np.uint8)
  texto_fundo = escreve_texto(texto, x, y, fundo, fonte, (255,255,255), tamanho=tamanho)
  texto_fundo = cv2.dilate(texto_fundo,(np.ones((3,5),np.uint8)))
  fx,fy,fw,fh = cv2.boundingRect(texto_fundo[:,:,2])
  cv2.rectangle(img, (fx, fy), (fx + fw, fy + fh), cor_fundo, -1)

  return img

def escreve_texto(texto, x, y, img, fonte, cor=(50, 50, 255), tamanho=22):
  fonte = ImageFont.truetype(fonte, tamanho)
  img_pil = Image.fromarray(img) 
  draw = ImageDraw.Draw(img_pil) 
  draw.text((x, y-tamanho), texto, font = fonte, fill = cor) 
  img = np.array(img_pil) 

  return img


lista_idiomas = "en,pt"
idiomas = lista_idiomas.split(",")
print(idiomas)

gpu = False #@param {type:"boolean"}
fonte = '/content/fontes/calibri.ttf' #@param {type:"string"}


 

def coord_caixa(caixa):
  (te, td, bd, be) = caixa
  te = (int(te[0]), int(te[1]))
  td = (int(td[0]), int(td[1]))
  bd = (int(bd[0]), int(bd[1]))
  be = (int(be[0]), int(be[1]))
  return te, td, bd, be

def desenha_caixa(img, te, bd, cor_caixa=(200, 255, 0), espessura=2): 
  cv2.rectangle(img, te, bd, cor_caixa, espessura)
  return img


amostras_exibir = 20
amostra_atual = 0
cor_fonte = (0,0,0)
cor_fundo = (200,255,0)
cor_caixa = (200,255,0)
tam_fonte = 20

kernel = np.ones((2, 2), np.uint8) 
reader = Reader(idiomas, gpu=gpu)
numeroFotos = 1
emLoop = 1 
tempo1 = time.time()   
while(emLoop <= numeroFotos):
    arquivo_imagem = cv2.imread('recortePlacaDiaMaior/placaRecortada'+str(emLoop)+'.jpg')
    
    gray = cv2.cvtColor(arquivo_imagem, cv2.COLOR_BGR2GRAY)
    (T, threshInv) = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    dilatada = cv2.dilate(threshInv,kernel,iterations = 2)
    medianBlur = cv2.medianBlur(dilatada,1)
    #threshInv = cv2.erode(arquivo_imagem, kernel, iterations=1)
    
    
    resultados = reader.readtext(dilatada, allowlist = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
    rgb = cv2.cvtColor(dilatada, cv2.COLOR_BGR2RGB)
    for (caixa, texto, prob) in resultados:
        te, td, bd, be = coord_caixa(caixa)
        imagem = desenha_caixa(rgb, te, bd)
        imagem = fundo_texto(texto, te[0], te[1], imagem, fonte, tam_fonte, cor_fundo)
        imagem = escreve_texto(texto, te[0], te[1], imagem, fonte, cor_fonte, tam_fonte)
        print(texto)
    #cv2.imwrite('aplicandoFiltros_Easyocr/resultado'+str(emLoop)+'.jpg',imagem)
    emLoop += 1

print()
print("Terminou!")
tempo = time.time() - tempo1
print("Tempo decorrido: ",tempo,"segundos")
print("Total de placas lidas: ",numeroFotos)
print("Tempo médio: ",(tempo/numeroFotos))

cv2.destroyAllWindows()
    
    

