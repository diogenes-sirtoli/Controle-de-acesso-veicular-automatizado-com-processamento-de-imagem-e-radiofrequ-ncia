import os
os.environ['KMP_DUPLICATE_LIB_OK']='True'
from easyocr import Reader
import cv2
from PIL import ImageFont, ImageDraw, Image
import numpy as np

def fundo_texto(texto, x, y, img, fonte, tamanho, cor_fundo):  #desenha uma caixa no fundo do texto
  fundo = np.full((img.shape), (0,0,0), dtype=np.uint8)
  texto_fundo = escreve_texto(texto, x, y, fundo, fonte, (255,255,255), tamanho=tamanho)
  texto_fundo = cv2.dilate(texto_fundo,(np.ones((3,5),np.uint8)))
  fx,fy,fw,fh = cv2.boundingRect(texto_fundo[:,:,2])
  cv2.rectangle(img, (fx, fy), (fx + fw, fy + fh), cor_fundo, -1)
  return img

def escreve_texto(texto, x, y, img, fonte, cor_fonte, tamanho=22): #escreve o texto encontrado e processado
  fonte = ImageFont.truetype(fonte, tamanho)
  img_pil = Image.fromarray(img) 
  draw = ImageDraw.Draw(img_pil) 
  draw.text((x, y-tamanho), texto, font = fonte, fill = cor_fonte) 
  img = np.array(img_pil) 
  return img


def coord_caixa(caixa):  #pega todas coodenadas ao redor do texto para desenhar uma caixa
  (te, td, bd, be) = caixa
  te = (int(te[0]), int(te[1]))
  td = (int(td[0]), int(td[1]))
  bd = (int(bd[0]), int(bd[1]))
  be = (int(be[0]), int(be[1]))
  return te, td, bd, be

def desenha_caixa(img, te, bd, cor_caixa, espessura=2): 
  cv2.rectangle(img, te, bd, cor_caixa, espessura) #desenha um retângulo ao redor dos textos encontrados
  return img


lista_idiomas = "en,pt"
idiomas = lista_idiomas.split(",")
print(idiomas)
 
gpu = False #@param {type:"boolean"}
fonte = '/content/fontes/calibri.ttf' #@param {type:"string"}


#CONFIGURAÇÕES DA ESCRITA DO RESULTADO
amostras_exibir = 20
amostra_atual = 0
cor_fonte = (0,0,0)
cor_fundo = (200,255,0)
cor_caixa = (200,255,0)
tam_fonte = 20


numeroFotos = 1   #numero de fotos que você quer processar
emLoop = 1  #contador para fazer loop 
while(emLoop <= numeroFotos):
    arquivo_imagem = cv2.imread('C:/Users/Marlon/Desktop/Fotos/teste'+str(emLoop)+'.jpg') #abre a foto do diretório
    frame = arquivo_imagem.copy()  #faz uma cópia da imagem original
    
    #Reajustar o tamanho da imagem
    scale_percent = 60 # percent of original size
    width = int(frame.shape[1] * scale_percent / 100)
    height = int(frame.shape[0] * scale_percent / 100)
    dim = (width, height)  
    # resize image
    resized_Frame = cv2.resize(frame, dim, interpolation = cv2.INTER_AREA)
 
    print('Resized Dimensions : ', resized_Frame.shape)
 
    cv2.imshow("Resized image", resized_Frame) #mostra imagem com tamanho novo
    cv2.waitKey(0)  #espera o usuário apertar algo para fechar a imagem da tela
    cv2.destroyAllWindows()
    
    reader = Reader(idiomas, gpu=gpu)
    resultados = reader.readtext(resized_Frame) #identifica todos caracteres da imagem
     
    for (caixa, texto, prob) in resultados: #em cada resultado de texto encontrado
        te, td, bd, be = coord_caixa(caixa)  #pega as coordenadas
        resized_Frame = desenha_caixa(resized_Frame, te, bd, cor_caixa) #desenha uma caixa ao redor
        resized_Frame = fundo_texto(texto, te[0], te[1], resized_Frame, fonte, tam_fonte, cor_fundo)  #destaca o fundo da caixa
        resized_Frame = escreve_texto(texto, te[0], te[1], resized_Frame, fonte, cor_fonte, tam_fonte) #escreve o texto no meio
    
    cv2.imwrite('C:/Users/Marlon/Desktop/Fotos/resultado'+str(emLoop)+'.jpg',resized_Frame) #salva foto no diretório
    emLoop += 1
  
print("Terminou")
cv2.destroyAllWindows()  #fecha todas janelas abertas
    
    
