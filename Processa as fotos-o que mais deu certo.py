import os
os.environ['KMP_DUPLICATE_LIB_OK']='True'
from easyocr import Reader
import cv2
from PIL import ImageFont, ImageDraw, Image
import numpy as np

def fundo_texto(texto, x, y, img, fonte, tamanho, cor_fundo):
    fundo = np.full((img.shape), (0,0,0), dtype=np.uint8)
    texto_fundo = escreve_texto(texto, x, y, fundo, fonte, (255,255,255), tamanho=tamanho)
    texto_fundo = cv2.dilate(texto_fundo,(np.ones((3,5),np.uint8)))
    fx,fy,fw,fh = cv2.boundingRect(texto_fundo[:,:,2])
    cv2.rectangle(img, (fx, fy), (fx + fw, fy + fh), cor_fundo, -1)
    return img

def escreve_texto(texto, x, y, img, fonte, cor_fonte, tamanho=22):
    fonte = ImageFont.truetype(fonte, tamanho)
    img_pil = Image.fromarray(img) 
    draw = ImageDraw.Draw(img_pil) 
    draw.text((x, y-tamanho), texto, font = fonte, fill = cor_fonte) 
    img = np.array(img_pil) 
    return img

def coord_caixa(caixa):
    (te, td, bd, be) = caixa
    te = (int(te[0]), int(te[1]))
    td = (int(td[0]), int(td[1]))
    bd = (int(bd[0]), int(bd[1]))
    be = (int(be[0]), int(be[1]))
    return te, td, bd, be

def desenha_caixa(img, te, bd, cor_caixa, espessura=2):
    cv2.rectangle(img, te, bd, cor_caixa, espessura)
    return img

# Configurações
lista_idiomas = "en,pt"
idiomas = lista_idiomas.split(",")
gpu = False
fonte = '/content/fontes/calibri.ttf'

# Configurações de exibição
cor_fonte = (0,0,0)
cor_fundo = (200,255,0)
cor_caixa = (200,255,0)
tam_fonte = 20

# CONFIGURAÇÃO QUE FUNCIONOU MELHOR (Config Restrita - Pré-proc 3)
config_otimizada = {
    'text_threshold': 0.8,      # MUITO ALTO - só texto claro
    'low_text': 0.5,           # Alto limiar inferior
    'link_threshold': 0.5,     # Conexões fortes apenas
    'mag_ratio': 2.0,          # Máximo aumento
    'slope_ths': 0.1,          # Pouca tolerância a inclinação
    'height_ths': 0.3,         # Apenas texto de altura similar
    'width_ths': 0.3,          # Apenas texto de largura similar
    'decoder': 'beamsearch',
    'beamWidth': 10,           # Busca mais abrangente
    'batch_size': 1,
    'contrast_ths': 0.3,
}

numeroFotos = 1
emLoop = 1

while(emLoop <= numeroFotos):
    arquivo_imagem = cv2.imread('D:/Imagens/placas/fotos26/fiesta.jpg')
    frame = arquivo_imagem.copy()
    
    # Reajustar o tamanho da imagem
    scale_percent = 100  # Manter 100% da resolução
    width = int(frame.shape[1] * scale_percent / 100)
    height = int(frame.shape[0] * scale_percent / 100)
    dim = (width, height)  
    resized_Frame = cv2.resize(frame, dim, interpolation = cv2.INTER_CUBIC)
 
    print('Dimensões da imagem : ', resized_Frame.shape)
    
    # USAR APENAS A IMAGEM ORIGINAL (Pré-proc 3 que funcionou melhor)
    print("Usando imagem original (sem pré-processamento)...")
    processed_frame = resized_Frame.copy()  # Sem pré-processamento!
    
    reader = Reader(idiomas, gpu=gpu)
    
    # Usar APENAS a configuração que funcionou melhor
    print("Processando com Configuração Restrita...")
    resultados = reader.readtext(processed_frame, **config_otimizada)
    
    melhor_resultado = None
    melhor_confianca = 0
    
    # Processar resultados
    for caixa, texto, prob in resultados:
        # Filtrar apenas texto que parece placa
        texto_limpo = ''.join(filter(str.isalnum, texto.upper()))
        
        if 6 <= len(texto_limpo) <= 8:  # Placas geralmente têm 7 caracteres
            print(f"Texto detectado: '{texto_limpo}' - Confiança: {prob:.3f}")
            
            if prob > melhor_confianca:
                melhor_confianca = prob
                melhor_resultado = (caixa, texto_limpo, prob)
    
    # Processar o melhor resultado encontrado
    if melhor_resultado:
        caixa, texto, prob = melhor_resultado
        print(f"\n🎯 RESULTADO FINAL: '{texto}'")
        print(f"📊 Confiança: {prob:.3f}")
        
        te, td, bd, be = coord_caixa(caixa)
        resized_Frame = desenha_caixa(resized_Frame, te, bd, (0, 255, 0))  # Verde
        resized_Frame = fundo_texto(f"{texto} ({prob:.3f})", te[0], te[1], resized_Frame, fonte, tam_fonte, (0, 255, 0))
        resized_Frame = escreve_texto(f"{texto} ({prob:.3f})", te[0], te[1], resized_Frame, fonte, (255, 255, 255), tam_fonte)
    else:
        print("❌ Nenhum texto de placa detectado")
        # Mostrar todos os textos detectados para debug
        print("Textos detectados (sem filtro):")
        for caixa, texto, prob in resultados:
            print(f"  '{texto}' - Conf: {prob:.3f}")
    
    cv2.imwrite('D:/Imagens/placas/fotos26/result'+str(emLoop)+'.jpg', resized_Frame)
    emLoop += 1

print("Processamento concluído")
cv2.destroyAllWindows()