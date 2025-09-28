import os
import time
import cv2
import numpy as np
from easyocr import Reader

# ==============================
# CONFIGURAÇÕES DE ROI
# ==============================
ROI_X = 250   # deslocamento horizontal da ROI
ROI_Y = 750   # deslocamento vertical da ROI
ROI_W = 750   # largura da ROI
ROI_H = 400   # altura da ROI

# Diretórios de entrada e saída
FOTOS_DIR = "fotos"
ROI_DIR = "roi"
RESULT_DIR = "result"
os.makedirs(ROI_DIR, exist_ok=True)
os.makedirs(RESULT_DIR, exist_ok=True)

# Configuração otimizada para OCR
config_otimizada = {
    "text_threshold": 0.8,
    "low_text": 0.5,
    "link_threshold": 0.5,
    "mag_ratio": 2.0,
    "slope_ths": 0.1,
    "height_ths": 0.3,
    "width_ths": 0.3,
    "decoder": "beamsearch",
    "beamWidth": 10,
    "batch_size": 1,
    "contrast_ths": 0.3,
}

# ==============================
# FUNÇÕES
# ==============================
def preprocessar_placa(img):
    """Pré-processa a ROI para melhorar OCR."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Aumenta contraste
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    # Binarização
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Morfologia para fechar falhas
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=1)

    # Corrige inversão (placa clara ou escura)
    black_pixels = np.sum(morph == 0)
    white_pixels = np.sum(morph == 255)
    if black_pixels < white_pixels:
        morph = cv2.bitwise_not(morph)

    return morph


def corrigir_placa(texto):
    """Corrige confusões comuns no OCR de placas brasileiras."""
    if not texto:
        return texto

    texto = "".join([c for c in texto if c.isalnum()])

    # Substituições comuns
    texto = texto.replace("0", "O", 3)   # primeiros chars tendem a ser letras
    texto = texto.replace("O", "0", 4)   # depois do 4º tende a ser número
    texto = texto.replace("I", "1")
    texto = texto.replace("Z", "2")
    texto = texto.replace("B", "8")

    if len(texto) == 7:
        texto = texto[:3] + "-" + texto[3:]

    return texto


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

    # Salvar ROI original e processada
    cv2.imwrite(os.path.join(ROI_DIR, f"roi_{idx}.jpg"), roi)
    cv2.imwrite(os.path.join(ROI_DIR, f"roi_proc_{idx}.jpg"), roi_proc)

    # Executar OCR
    t3 = time.time()
    resultados = reader.readtext(roi_proc, **config_otimizada, allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    tempos["ocr"] = time.time() - t3

    # Processar resultados
    t4 = time.time()
    melhor_texto = ""
    melhor_conf = 0.0
    melhor_caixa = None

    for caixa, texto, prob in resultados:
        texto_limpo = corrigir_placa(texto.upper())
        if 6 <= len(texto_limpo) <= 8 and prob > melhor_conf:
            melhor_texto = texto_limpo
            melhor_conf = prob
            melhor_caixa = caixa

    # Se encontrou algo relevante, salvar resultado com bounding box
    if melhor_caixa:
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

    # Tempos detalhados
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
    reader = Reader(["en"], gpu=False)  # use gpu=True se tiver CUDA
    print(f"✅ Modelo carregado em {time.time() - t0:.2f} segundos\n")

    imagens = [
        os.path.join(FOTOS_DIR, f)
        for f in os.listdir(FOTOS_DIR)
        if f.lower().endswith((".jpg", ".png", ".jpeg"))
    ]

    for i, img_path in enumerate(imagens, 1):
        processar_imagem(img_path, i, reader)

    print("✅ Processamento concluído.")
