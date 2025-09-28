import os
import time
import cv2
import numpy as np
from easyocr import Reader

# ==============================
# CONFIGURAÇÕES DE ROI
# ==============================
ROI_X = 250
ROI_Y = 550
ROI_W = 750
ROI_H = 500

# Diretórios
FOTOS_DIR = "fotos"
ROI_DIR = "roi"
RESULT_DIR = "result"
os.makedirs(ROI_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)

# Configuração otimizada para OCR
config_otimizada = {
    "text_threshold": 0.7,  # Reduzido para capturar mais texto
    "low_text": 0.4,
    "link_threshold": 0.4,
    "mag_ratio": 1.8,  # Reduzido ligeiramente
    "slope_ths": 0.1,
    "height_ths": 0.3,
    "width_ths": 0.4,  # Aumentado para tolerar mais variação
    "decoder": "beamsearch",
    "beamWidth": 8,    # Reduzido para velocidade
    "batch_size": 1,
    "contrast_ths": 0.2,
}

# ==============================
# FUNÇÕES OTIMIZADAS
# ==============================
def preprocessar_placa(img):
    """Pré-processa a ROI com foco em preservar detalhes dos caracteres."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # CLAHE mais suave
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    
    # Filtro bilateral para preservar bordas
    gray = cv2.bilateralFilter(gray, 5, 75, 75)
    
    # Binarização adaptativa para lidar com iluminação variável
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY, 11, 2)
    
    # Operação morfológica mínima para não distorcer caracteres
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
    morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=1)
    
    # Corrige inversão baseado na área central (onde geralmente está a placa)
    height, width = morph.shape
    center_roi = morph[height//4:3*height//4, width//4:3*width//4]
    black_center = np.sum(center_roi == 0)
    white_center = np.sum(center_roi == 255)
    
    if black_center < white_center:
        morph = cv2.bitwise_not(morph)
    
    return morph

def validar_formato_placa(texto):
    """Valida se o texto segue os padrões brasileiros/mercosul."""
    if len(texto) != 7:
        return False
    
    # Padrão antigo: LLL-NNNN (3 letras + 4 números)
    # Padrão mercosul: LLLNLNN (3 letras + 1 número + 1 letra + 2 números)
    
    letras = texto[:3]
    resto = texto[3:]
    
    # Verifica se os 3 primeiros são letras
    if not all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' for c in letras):
        return False
    
    # Verifica padrões válidos
    if texto[3] == '-':  # Padrão com traço: LLL-NNNN
        return all(c in '0123456789' for c in resto[1:]) and len(resto) == 5
    else:  # Padrão mercosul: LLLNLNN
        if len(resto) != 4:
            return False
        # Verifica: número, letra, número, número
        return (resto[0] in '0123456789' and 
                resto[1] in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' and 
                resto[2] in '0123456789' and 
                resto[3] in '0123456789')

def corrigir_caracteres_placa(texto):
    """Correção inteligente baseada na posição do caractere na placa."""
    if len(texto) < 4:
        return texto
    
    texto = "".join([c for c in texto if c.isalnum()])
    texto = texto.upper()
    
    # Mapeamento de correções baseado em confusões comuns
    confusoes = {
        '0': 'O', '1': 'I', '2': 'Z', '3': '8', '4': 'A', 
        '5': 'S', '6': 'G', '7': 'T', '8': 'B', '9': 'G',
        'O': '0', 'I': '1', 'Z': '2', 'B': '8', 'S': '5',
        'G': '6', 'T': '7', 'A': '4', 'D': '0', 'Q': '0'
    }
    
    resultado = []
    
    for i, char in enumerate(texto):
        if i < 3:  # Primeiros 3 caracteres: DEVEM ser letras
            if char in '0123456789':
                # Converte números problemáticos para letras
                if char == '0': resultado.append('O')
                elif char == '1': resultado.append('I')
                elif char == '8': resultado.append('B')
                else: resultado.append('I')  # Default para confusão número->letra
            elif char in confusoes and confusoes[char] in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                resultado.append(confusoes[char])
            else:
                resultado.append(char)
                
        elif i >= 3 and len(texto) >= 7:  # Restante: principalmente números
            if i == 3 and len(texto) == 7:  # 4º caractere em placa mercosul pode ser número
                if char in 'OIZBATGSD':
                    if char == 'O': resultado.append('0')
                    elif char == 'I': resultado.append('1')
                    elif char == 'Z': resultado.append('2')
                    elif char == 'B': resultado.append('8')
                    elif char == 'A': resultado.append('4')
                    elif char == 'T': resultado.append('7')
                    elif char == 'G': resultado.append('6')
                    elif char == 'S': resultado.append('5')
                    elif char == 'D': resultado.append('0')
                    else: resultado.append(char)
                else:
                    resultado.append(char)
                    
            elif i == 4 and len(texto) == 7:  # 5º caractere em placa mercosul pode ser letra
                if char in '0123456789':
                    # Converte números problemáticos para letras
                    if char == '0': resultado.append('O')
                    elif char == '1': resultado.append('I')
                    elif char == '8': resultado.append('B')
                    else: resultado.append(char)
                else:
                    resultado.append(char)
                    
            else:  # Últimos caracteres: DEVEM ser números
                if char in 'OIZBATGSD':
                    if char == 'O': resultado.append('0')
                    elif char == 'I': resultado.append('1')
                    elif char == 'Z': resultado.append('2')
                    elif char == 'B': resultado.append('8')
                    elif char == 'A': resultado.append('4')
                    elif char == 'T': resultado.append('7')
                    elif char == 'G': resultado.append('9')  # 6 ou 9? Vamos com 9
                    elif char == 'S': resultado.append('5')
                    elif char == 'D': resultado.append('0')
                    else: resultado.append(char)
                else:
                    resultado.append(char)
        else:
            resultado.append(char)
    
    texto_corrigido = "".join(resultado)
    
    # Formatação final
    if len(texto_corrigido) == 7 and texto_corrigido[3] != '-':
        # Insere traço para padrão antigo se necessário
        if (texto_corrigido[3] in '0123456789' and 
            texto_corrigido[4] in '0123456789' and
            texto_corrigido[5] in '0123456789' and
            texto_corrigido[6] in '0123456789'):
            texto_corrigido = texto_corrigido[:3] + "-" + texto_corrigido[3:]
    
    return texto_corrigido

def processar_imagem(path_img, idx, reader):
    print(f"📸 Processando imagem {idx}...")
    tempos = {}

    # Carregar imagem
    t1 = time.time()
    img = cv2.imread(path_img)
    tempos["carregamento"] = time.time() - t1

    if img is None:
        print("❌ Erro: imagem não encontrada.")
        return

    print("Dimensões da imagem:", img.shape)

    # Recorte ROI
    t2 = time.time()
    roi = img[ROI_Y:ROI_Y + ROI_H, ROI_X:ROI_X + ROI_W]
    roi_proc = preprocessar_placa(roi)
    tempos["preprocess"] = time.time() - t2

    # Salvar ROI processada
    cv2.imwrite(os.path.join(ROI_DIR, f"roi_proc_{idx}.jpg"), roi_proc)

    # Executar OCR
    t3 = time.time()
    resultados = reader.readtext(roi_proc, **config_otimizada, 
                               allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    tempos["ocr"] = time.time() - t3

    # Processar resultados
    t4 = time.time()
    melhor_texto = ""
    melhor_conf = 0.0
    melhor_caixa = None

    for caixa, texto, prob in resultados:
        texto_limpo = "".join([c for c in texto.upper() if c.isalnum()])
        
        # Aplica correção
        texto_corrigido = corrigir_caracteres_placa(texto_limpo)
        
        # Valida o formato
        if validar_formato_placa(texto_corrigido) and prob > melhor_conf:
            melhor_texto = texto_corrigido
            melhor_conf = prob
            melhor_caixa = caixa

    # Se não encontrou com validação estrita, pega o melhor candidato
    if not melhor_texto and resultados:
        for caixa, texto, prob in resultados:
            texto_limpo = "".join([c for c in texto.upper() if c.isalnum()])
            texto_corrigido = corrigir_caracteres_placa(texto_limpo)
            
            if 6 <= len(texto_corrigido) <= 8 and prob > melhor_conf:
                melhor_texto = texto_corrigido
                melhor_conf = prob
                melhor_caixa = caixa

    # Salvar resultado com bounding box
    if melhor_caixa and melhor_texto:
        (top_left, top_right, bottom_right, bottom_left) = melhor_caixa
        pts = np.array([top_left, top_right, bottom_right, bottom_left], np.int32)
        pts = pts.reshape((-1, 1, 2))
        cv2.polylines(roi, [pts], True, (0, 255, 0), 2)
        cv2.putText(
            roi,
            f"{melhor_texto} ({melhor_conf:.2f})",
            (int(top_left[0]), int(top_left[1]) - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )
        result_filename = os.path.join(RESULT_DIR, f"result_{idx}.jpg")
        cv2.imwrite(result_filename, roi)

    tempos["pos_process"] = time.time() - t4
    tempo_total = sum(tempos.values())

    # Exibir resultado
    if melhor_texto:
        print(f"\n🎯 RESULTADO FINAL: '{melhor_texto}'")
        print(f"📊 Confiança: {melhor_conf:.3f}")
    else:
        print("❌ Nenhum texto de placa válido detectado")

    print("\n⏱️ Tempos da execução:")
    print(f"  - Carregamento da imagem : {tempos['carregamento']:.2f}s")
    print(f"  - Recorte ROI / Preproc. : {tempos['preprocess']:.2f}s")
    print(f"  - OCR (readtext)         : {tempos['ocr']:.2f}s")
    print(f"  - Processamento result.  : {tempos['pos_process']:.2f}s")
    print(f"  - Tempo total imagem     : {tempo_total:.2f}s\n")

    return melhor_texto, melhor_conf

# ==============================
# MAIN
# ==============================
if __name__ == "__main__":
    print("Carregando modelo OCR...")
    t0 = time.time()
    reader = Reader(["en"], gpu=False)
    print(f"✅ Modelo carregado em {time.time() - t0:.2f} segundos\n")

    imagens = [
        os.path.join(FOTOS_DIR, f)
        for f in os.listdir(FOTOS_DIR)
        if f.lower().endswith((".jpg", ".png", ".jpeg"))
    ]

    for i, img_path in enumerate(imagens, 1):
        processar_imagem(img_path, i, reader)

    print("✅ Processamento concluído.")