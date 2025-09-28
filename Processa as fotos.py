import os
import time
import cv2
import numpy as np
from easyocr import Reader
import shutil

# ==============================
# CONFIGURAÇÕES DE ROI
# ==============================
ROI_X = 150
ROI_Y = 350
ROI_W = 850
ROI_H = 650

# Diretórios
FOTOS_AUTO_DIR = "fotoAut"
FOTOS_MANUAL_DIR = "fotoMan"
FOTOS_PROC_DIR = "fotoProc"
ROI_DIR = "roi"
RESULT_DIR = "result"

# Criar diretórios se não existirem
for dir_name in [FOTOS_AUTO_DIR, FOTOS_MANUAL_DIR, FOTOS_PROC_DIR, ROI_DIR, RESULT_DIR]:
    os.makedirs(dir_name, exist_ok=True)

# Configuração otimizada para OCR
config_otimizada = {
    "text_threshold": 0.7,
    "low_text": 0.4,
    "link_threshold": 0.4,
    "mag_ratio": 1.8,
    "slope_ths": 0.1,
    "height_ths": 0.3,
    "width_ths": 0.4,
    "decoder": "beamsearch",
    "beamWidth": 8,
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
    
    # Remove traço se existir para validação
    texto = texto.replace('-', '')
    
    if len(texto) != 7:
        return False
    
    letras = texto[:3]
    resto = texto[3:]
    
    # Verifica se os 3 primeiros são letras
    if not all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' for c in letras):
        return False
    
    # Verifica padrão mercosul: LLLNLNN (3 letras + 1 número + 1 letra + 2 números)
    # ÚLTIMAS 2 POSIÇÕES SEMPRE NÚMEROS
    if (resto[0] in '0123456789' and 
        resto[1] in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' and 
        resto[2] in '0123456789' and 
        resto[3] in '0123456789'):
        return True
    
    # Verifica padrão antigo: LLLNNNN (3 letras + 4 números)
    # TODAS AS 4 ÚLTIMAS POSIÇÕES SÃO NÚMEROS
    if all(c in '0123456789' for c in resto):
        return True
    
    return False

def converter_letra_para_numero(char):
    """Converte letras comuns confundidas com números"""
    conversoes = {
        'O': '0', 'Q': '0', 'D': '0', 'C': '0', 'U': '0',
        'I': '1', 'J': '1', 'L': '1',
        'Z': '2', 
        'A': '4', 
        'S': '5', 
        'G': '6', 
        'T': '7', 
        'B': '8',
        'P': '0', 'R': '2', 'E': '3', 'F': '3'
    }
    return conversoes.get(char, '0')  # Default para '0' se não encontrado

def forcar_numeros_ultimas_posicoes(texto):
    """FORÇA que as últimas 2 posições sejam números - MÉTODO AGGRESSIVO"""
    if len(texto) != 7:
        return texto
    
    resultado = list(texto)
    
    # POSIÇÃO 5 (penúltima) - SEMPRE NÚMERO
    if resultado[5] not in '0123456789':
        resultado[5] = converter_letra_para_numero(resultado[5])
    
    # POSIÇÃO 6 (última) - SEMPRE NÚMERO  
    if resultado[6] not in '0123456789':
        resultado[6] = converter_letra_para_numero(resultado[6])
    
    return "".join(resultado)

def corrigir_caracteres_placa(texto):
    """Correção inteligente baseada na posição do caractere na placa."""
    if len(texto) < 7:
        return texto
    
    # Remove caracteres especiais e mantém apenas 7 primeiros caracteres
    texto = "".join([c for c in texto if c.isalnum()])[:7]
    texto = texto.upper()
    
    if len(texto) != 7:
        return texto
    
    resultado = list(texto)
    
    # CORREÇÕES PARA OS PRIMEIROS 3 CARACTERES (SEMPRE LETRAS)
    for i in range(3):
        char = resultado[i]
        if char in '0123456789':
            # Converte números para letras similares
            if char == '0': resultado[i] = 'O'
            elif char == '1': resultado[i] = 'I'
            elif char == '2': resultado[i] = 'Z'
            elif char == '4': resultado[i] = 'A'
            elif char == '5': resultado[i] = 'S'
            elif char == '6': resultado[i] = 'G'
            elif char == '7': resultado[i] = 'T'
            elif char == '8': resultado[i] = 'B'
            elif char == '9': resultado[i] = 'G'
        else:
            # Garante que seja letra válida
            if char not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                resultado[i] = 'I'
    
    # CORREÇÕES PARA OS ÚLTIMOS 4 CARACTERES
    # Verifica se é padrão mercosul (LLLNLNN) ou antigo (LLLNNNN)
    is_mercosul = (resultado[3] in '0123456789' and 
                   resultado[4] in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' and 
                   resultado[5] in '0123456789' and 
                   resultado[6] in '0123456789')
    
    is_antigo = all(c in '0123456789' for c in resultado[3:7])
    
    if is_mercosul:
        # Padrão Mercosul: LLL N L NN
        # Posição 3: número
        if resultado[3] not in '0123456789':
            resultado[3] = converter_letra_para_numero(resultado[3])
        
        # Posição 4: letra (mantém como está, já foi corrigida acima)
        # Apenas garante que é letra
        if resultado[4] in '0123456789':
            if resultado[4] == '0': resultado[4] = 'O'
            elif resultado[4] == '1': resultado[4] = 'I'
            elif resultado[4] == '8': resultado[4] = 'B'
            else: resultado[4] = 'I'
        
        # FORÇA números nas últimas 2 posições
        if resultado[5] not in '0123456789':
            resultado[5] = converter_letra_para_numero(resultado[5])
            
        if resultado[6] not in '0123456789':
            resultado[6] = converter_letra_para_numero(resultado[6])
        
    elif is_antigo:
        # Padrão Antigo: LLL NNNN (todos números)
        for i in range(3, 7):
            if resultado[i] not in '0123456789':
                resultado[i] = converter_letra_para_numero(resultado[i])
    
    else:
        # Se não identificou o padrão, aplica correções gerais
        # GARANTE QUE AS ÚLTIMAS 4 POSIÇÕES SÃO NÚMEROS
        for i in range(3, 7):
            if resultado[i] not in '0123456789':
                resultado[i] = converter_letra_para_numero(resultado[i])
    
    texto_corrigido = "".join(resultado)
    
    # VALIDAÇÃO FINAL EXTRA: GARANTE ABSOLUTAMENTE QUE ÚLTIMAS 2 POSIÇÕES SÃO NÚMEROS
    texto_corrigido = forcar_numeros_ultimas_posicoes(texto_corrigido)
    
    # Formatação final - adiciona traço apenas para padrão antigo
    if (len(texto_corrigido) == 7 and 
        all(c in '0123456789' for c in texto_corrigido[3:7])):
        texto_corrigido = texto_corrigido[:3] + "-" + texto_corrigido[3:]
    
    return texto_corrigido

def processar_imagem(path_img, idx, reader, modo_auto=False):
    """Processa uma imagem e retorna o resultado do OCR"""
    tempo_inicio_imagem = time.time()
    print(f"📸 Processando imagem {idx}...")
    tempos = {}

    # Carregar imagem
    t1 = time.time()
    img = cv2.imread(path_img)
    tempos["carregamento"] = time.time() - t1

    if img is None:
        print("❌ Erro: imagem não encontrada.")
        return None, 0.0

    print("Dimensões da imagem:", img.shape)

    # Recorte ROI
    t2 = time.time()
    roi = img[ROI_Y:ROI_Y + ROI_H, ROI_X:ROI_X + ROI_W]
    roi_proc = preprocessar_placa(roi)
    tempos["preprocess"] = time.time() - t2

    # Salvar ROI processada apenas se não for modo automático
    if not modo_auto:
        cv2.imwrite(os.path.join(ROI_DIR, f"roi_proc_{idx}.jpg"), roi_proc)

    # Executar OCR
    t3 = time.time()
    resultados = reader.readtext(roi_proc, **config_otimizada)
    tempos["ocr"] = time.time() - t3

    # Processar resultados
    t4 = time.time()
    melhor_texto = ""
    melhor_conf = 0.0
    melhor_caixa = None

    for caixa, texto, prob in resultados:
        # Limpa o texto mantendo apenas alfanuméricos
        texto_limpo = "".join([c for c in texto.upper() if c.isalnum()])
        
        # SÓ PROCESSAR TEXTOS COM EXATAMENTE 7 CARACTERES
        if len(texto_limpo) == 7:
            # Aplica correção
            texto_corrigido = corrigir_caracteres_placa(texto_limpo)
            
            # Valida o formato
            if validar_formato_placa(texto_corrigido.replace('-', '')):
                if prob > melhor_conf:
                    melhor_texto = texto_corrigido
                    melhor_conf = prob
                    melhor_caixa = caixa
            elif prob > melhor_conf + 0.1:  # Dá chance para textos com alta confiança
                melhor_texto = texto_corrigido
                melhor_conf = prob
                melhor_caixa = caixa

    # Fallback: se não encontrou nada válido, pega o de maior confiança com 7 caracteres
    if not melhor_texto and resultados:
        for caixa, texto, prob in resultados:
            texto_limpo = "".join([c for c in texto.upper() if c.isalnum()])
            if len(texto_limpo) == 7 and prob > melhor_conf:
                texto_corrigido = corrigir_caracteres_placa(texto_limpo)
                melhor_texto = texto_corrigido
                melhor_conf = prob
                melhor_caixa = caixa

    # VALIDAÇÃO FINAL: Se ainda tem letras nas últimas posições, força conversão
    if melhor_texto and len(melhor_texto.replace('-', '')) == 7:
        melhor_texto_sem_traco = melhor_texto.replace('-', '')
        melhor_texto_corrigido = forcar_numeros_ultimas_posicoes(melhor_texto_sem_traco)
        
        # Re-formata se necessário
        if all(c in '0123456789' for c in melhor_texto_corrigido[3:7]):
            melhor_texto = melhor_texto_corrigido[:3] + "-" + melhor_texto_corrigido[3:]
        else:
            melhor_texto = melhor_texto_corrigido

    # Salvar resultado com bounding box apenas se não for modo automático
    if melhor_caixa and melhor_texto and not modo_auto:
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
    tempo_total_imagem = time.time() - tempo_inicio_imagem

    # Exibir resultado
    if melhor_texto:
        print(f"\n🎯 RESULTADO FINAL: '{melhor_texto}'")
        print(f"📊 Confiança: {melhor_conf:.3f}")
    else:
        print("❌ Nenhum texto de placa válido detectado")

    # SEMPRE mostrar tempo de processamento
    print(f"⏱️ Tempo total da imagem: {tempo_total_imagem:.2f}s")
    
    if not modo_auto:
        print("\n⏱️ Tempos detalhados:")
        print(f"  - Carregamento da imagem : {tempos['carregamento']:.2f}s")
        print(f"  - Recorte ROI / Preproc. : {tempos['preprocess']:.2f}s")
        print(f"  - OCR (readtext)         : {tempos['ocr']:.2f}s")
        print(f"  - Processamento result.  : {tempos['pos_process']:.2f}s")

    return melhor_texto, melhor_conf

def mostrar_configuracoes_roi():
    """Mostra uma imagem com as configurações atuais do ROI"""
    # Criar uma imagem preta
    img_exemplo = np.zeros((800, 1200, 3), dtype=np.uint8)
    
    # Desenhar o veículo simulado
    cv2.rectangle(img_exemplo, (300, 400), (900, 600), (100, 100, 100), -1)  # Carroceria
    cv2.rectangle(img_exemplo, (400, 300), (800, 400), (100, 100, 100), -1)  # Cabine
    cv2.circle(img_exemplo, (450, 650), 40, (50, 50, 50), -1)  # Roda esquerda
    cv2.circle(img_exemplo, (750, 650), 40, (50, 50, 50), -1)  # Roda direita
    
    # Desenhar a ROI
    cv2.rectangle(img_exemplo, (ROI_X, ROI_Y), (ROI_X + ROI_W, ROI_Y + ROI_H), (0, 255, 0), 2)
    
    # Adicionar texto com as configurações
    textos = [
        f"CONFIGURAÇÕES ATUAIS DO ROI",
        f"ROI_X: {ROI_X} (Horizontal)",
        f"ROI_Y: {ROI_Y} (Vertical)", 
        f"ROI_W: {ROI_W} (Largura)",
        f"ROI_H: {ROI_H} (Altura)",
        "",
        "A área verde mostra a região de detecção",
        "Pressione qualquer tecla para voltar ao menu"
    ]
    
    for i, texto in enumerate(textos):
        y_pos = 50 + i * 30
        cv2.putText(img_exemplo, texto, (50, y_pos), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # Mostrar a imagem
    cv2.imshow("Configurações ROI - Pressione qualquer tecla para voltar", img_exemplo)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

def ajustar_configuracoes_roi():
    """Permite ajustar as configurações de ROI"""
    global ROI_X, ROI_Y, ROI_W, ROI_H
    
    print("\n🔧 AJUSTAR CONFIGURAÇÕES DE ROI")
    print("=" * 40)
    
    while True:
        print(f"\nConfigurações atuais:")
        print(f"1. ROI_X (Horizontal): {ROI_X}")
        print(f"2. ROI_Y (Vertical): {ROI_Y}")
        print(f"3. ROI_W (Largura): {ROI_W}")
        print(f"4. ROI_H (Altura): {ROI_H}")
        print("5. Visualizar configurações atuais")
        print("6. Salvar e voltar ao menu")
        print("7. Voltar ao menu sem salvar")
        
        opcao = input("\nEscolha uma opção (1-7): ").strip()
        
        if opcao == '1':
            try:
                novo_valor = int(input(f"Novo valor para ROI_X (atual: {ROI_X}): "))
                ROI_X = novo_valor
                print("✅ ROI_X atualizado!")
            except ValueError:
                print("❌ Valor inválido!")
                
        elif opcao == '2':
            try:
                novo_valor = int(input(f"Novo valor para ROI_Y (atual: {ROI_Y}): "))
                ROI_Y = novo_valor
                print("✅ ROI_Y atualizado!")
            except ValueError:
                print("❌ Valor inválido!")
                
        elif opcao == '3':
            try:
                novo_valor = int(input(f"Novo valor para ROI_W (atual: {ROI_W}): "))
                ROI_W = novo_valor
                print("✅ ROI_W atualizado!")
            except ValueError:
                print("❌ Valor inválido!")
                
        elif opcao == '4':
            try:
                novo_valor = int(input(f"Novo valor para ROI_H (atual: {ROI_H}): "))
                ROI_H = novo_valor
                print("✅ ROI_H atualizado!")
            except ValueError:
                print("❌ Valor inválido!")
                
        elif opcao == '5':
            mostrar_configuracoes_roi()
            
        elif opcao == '6':
            print("✅ Configurações salvas!")
            return
            
        elif opcao == '7':
            print("⚠️ Alterações descartadas!")
            return
            
        else:
            print("❌ Opção inválida!")

def ocr_automatico(reader):
    """Processa automaticamente todas as imagens da pasta fotoAut"""
    print("\n🤖 MODO OCR AUTOMÁTICO")
    print("=" * 40)
    
    imagens = [
        os.path.join(FOTOS_AUTO_DIR, f)
        for f in os.listdir(FOTOS_AUTO_DIR)
        if f.lower().endswith((".jpg", ".png", ".jpeg"))
    ]
    
    if not imagens:
        print("❌ Nenhuma imagem encontrada na pasta 'fotoAut'")
        input("Pressione Enter para voltar ao menu...")
        return
    
    print(f"📁 Encontradas {len(imagens)} imagens para processamento automático")
    
    tempo_inicio_total = time.time()
    
    for i, img_path in enumerate(imagens, 1):
        print(f"\n--- Processando imagem {i}/{len(imagens)} ---")
        
        # Processar imagem
        texto, confianca = processar_imagem(img_path, i, reader, modo_auto=True)
        
        # Mover imagem processada
        nome_arquivo = os.path.basename(img_path)
        novo_caminho = os.path.join(FOTOS_PROC_DIR, nome_arquivo)
        shutil.move(img_path, novo_caminho)
        print(f"✅ Imagem movida para: {novo_caminho}")
        
        # Salvar resultado em arquivo de log
        if texto:
            with open(os.path.join(RESULT_DIR, "log_automatico.txt"), "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {nome_arquivo} - {texto} - {confianca:.3f}\n")
    
    tempo_total_processamento = time.time() - tempo_inicio_total
    print(f"\n✅ Processamento automático concluído!")
    print(f"⏱️ Tempo total: {tempo_total_processamento:.2f}s")
    print(f"📝 Log salvo em: {os.path.join(RESULT_DIR, 'log_automatico.txt')}")
    input("Pressione Enter para voltar ao menu...")

def ocr_manual(reader):
    """Processa manualmente imagens selecionadas da pasta fotoMan"""
    print("\n👤 MODO OCR MANUAL")
    print("=" * 40)
    
    imagens = [
        f for f in os.listdir(FOTOS_MANUAL_DIR)
        if f.lower().endswith((".jpg", ".png", ".jpeg"))
    ]
    
    if not imagens:
        print("❌ Nenhuma imagem encontrada na pasta 'fotoMan'")
        input("Pressione Enter para voltar ao menu...")
        return
    
    while True:
        print("\n📁 Imagens disponíveis:")
        for i, img in enumerate(imagens, 1):
            print(f"{i}. {img}")
        print(f"{len(imagens) + 1}. Voltar ao menu")
        
        try:
            escolha = int(input(f"\nEscolha uma imagem (1-{len(imagens) + 1}): "))
            
            if 1 <= escolha <= len(imagens):
                img_selecionada = imagens[escolha - 1]
                img_path = os.path.join(FOTOS_MANUAL_DIR, img_selecionada)
                
                print(f"\n🔄 Processando: {img_selecionada}")
                texto, confianca = processar_imagem(img_path, escolha, reader, modo_auto=False)
                
                if texto:
                    print(f"🎯 Placa detectada: {texto}")
                else:
                    print("❌ Nenhuma placa detectada")
                    
                input("\nPressione Enter para continuar...")
                
            elif escolha == len(imagens) + 1:
                return
            else:
                print("❌ Opção inválida!")
                
        except ValueError:
            print("❌ Entrada inválida!")

def mostrar_menu():
    """Exibe o menu principal"""
    print("\n" + "=" * 50)
    print("           SISTEMA DE RECONHECIMENTO DE PLACAS")
    print("=" * 50)
    print("1. 🤖 OCR Automático (pasta: fotoAut)")
    print("2. 👤 OCR Manual (pasta: fotoMan)")
    print("3. 🔧 Ajustar Configurações de ROI")
    print("4. 📊 Visualizar Configurações Atuais")
    print("5. 🚪 Sair")
    print("=" * 50)

# ==============================
# MAIN
# ==============================
if __name__ == "__main__":
    print("Carregando modelo OCR...")
    t0 = time.time()
    reader = Reader(["en"], gpu=False)
    print(f"✅ Modelo carregado em {time.time() - t0:.2f} segundos")
    
    while True:
        mostrar_menu()
        
        opcao = input("\nEscolha uma opção (1-5): ").strip()
        
        if opcao == '1':
            ocr_automatico(reader)
            
        elif opcao == '2':
            ocr_manual(reader)
            
        elif opcao == '3':
            ajustar_configuracoes_roi()
            
        elif opcao == '4':
            mostrar_configuracoes_roi()
            
        elif opcao == '5':
            print("\n👋 Obrigado por usar o sistema! Até logo!")
            break
            
        else:
            print("❌ Opção inválida! Tente novamente.")
            input("Pressione Enter para continuar...")