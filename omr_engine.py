import cv2
import numpy as np
from PIL import Image, ImageOps

def tratar_entrada(img_pil):
    img_pil = ImageOps.exif_transpose(img_pil)
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

def order_points(pts):
    # Ordena: Top-Esq, Top-Dir, Inf-Dir, Inf-Esq
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def alinhar_gabarito(imagem):
    # Redimensiona apenas para a detecção (ganho de performance e padrão)
    h_orig, w_orig = imagem.shape[:2]
    ratio = 1000.0 / w_orig
    img_resize = cv2.resize(imagem, (1000, int(h_orig * ratio)))
    
    gray = cv2.cvtColor(img_resize, cv2.COLOR_BGR2GRAY)
    # Blur para reduzir ruído do papel
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    # Adaptive Threshold é melhor para iluminação irregular
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
    
    # Estratégia de Quadrantes: Divide a imagem em 4 setores
    # e encontra o maior contorno (blob preto) em cada um.
    h, w = img_resize.shape[:2]
    centers = []
    
    # Definição dos setores (margens de segurança para não pegar sujeira da borda)
    sectores = [
        (0, 0, w//2, h//2),       # Top-Left
        (w//2, 0, w, h//2),       # Top-Right
        (w//2, h//2, w, h),       # Bottom-Right
        (0, h//2, w//2, h)        # Bottom-Left
    ]
    
    for (startX, startY, endX, endY) in sectores:
        roi = thresh[startY:endY, startX:endX]
        cnts, _ = cv2.findContours(roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Pega o maior contorno da região (provavelmente a âncora)
        if cnts:
            c = max(cnts, key=cv2.contourArea)
            area = cv2.contourArea(c)
            
            # Filtro de segurança: Âncora deve ter tamanho razoável
            if area > 200: 
                M = cv2.moments(c)
                if M["m00"] != 0:
                    cX = int((M["m10"] / M["m00"]) + startX)
                    cY = int((M["m01"] / M["m00"]) + startY)
                    centers.append([cX, cY])

    # Se achou os 4 cantos, faz a mágica
    if len(centers) == 4:
        pts = np.array(centers, dtype="float32")
        rect = order_points(pts)
        
        # Mapeia para 1000x1450 (Proporção A4 alongada para o SAMAR)
        dst = np.array([
            [0, 0],
            [1000 - 1, 0],
            [1000 - 1, 1450 - 1],
            [0, 1450 - 1]], dtype="float32")

        M = cv2.getPerspectiveTransform(rect, dst)
        # Aplica a transformação na imagem original redimensionada
        warped = cv2.warpPerspective(img_resize, M, (1000, 1450))
        return warped

    # FALLBACK SEGURO: Se falhar, retorna a imagem resized centralizada
    print("Falha na detecção de âncoras. Usando imagem bruta.")
    return cv2.resize(imagem, (1000, 1450))

def extrair_dados(img_warped, gab_oficial=None):
    # Imagem PADRONIZADA em 1000 x 1450 px
    gray = cv2.cvtColor(img_warped, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    
    res = {"respostas": {}, "frequencia": ""}
    img_mask = img_warped.copy()

    # --- 1. FREQUÊNCIA (Ajustado para a direita) ---
    # Coordenadas X recalibradas com base no seu print (estavam muito à esquerda)
    cols_freq = [("D", 125), ("U", 170)] 
    
    freq_final = ""
    for nome, x in cols_freq:
        votos = []
        for i in range(10):
            # Y inicial = 195, Passo = 34
            y = int(195 + (i * 34)) 
            roi = thresh[y-12:y+12, x-12:x+12]
            votos.append(cv2.countNonZero(roi))
        
        # Sensibilidade ajustada
        if max(votos) > 120:
            idx = np.argmax(votos)
            freq_final += str(idx)
            # Bola Azul Cheia na Frequência Detectada
            cv2.circle(img_mask, (x, int(195 + (idx * 34))), 13, (255, 0, 0), -1)
        else:
            freq_final += "0" # Assume 0 se vazio
            # Marca visual vazia no 0 para indicar que assumiu zero
            cv2.circle(img_mask, (x, 195), 13, (255, 100, 100), 2)
            
    res["frequencia"] = freq_final

    # --- 2. QUESTÕES (Grade Ajustada) ---
    # Coordenadas X deslocadas +15px para a direita com base no erro anterior
    blocos = [
        (235, 450, 1),   # Bloco 1 (Esq)
        (550, 450, 14),  # Bloco 2 (Dir)
        (235, 980, 27),  # Bloco 3 (Esq Baixo)
        (550, 980, 40)   # Bloco 4 (Dir Baixo)
    ]
    
    step_x = 49 # Passo Horizontal
    step_y = 36 # Passo Vertical

    for (bx, by, q_start) in blocos:
        for i in range(13):
            q_num = q_start + i
            cy = int(by + (i * step_y))
            
            pixels_q = []
            for j in range(4): # A, B, C, D
                cx = int(bx + (j * step_x))
                roi = thresh[cy-14:cy+14, cx-14:cx+14]
                pixels_q.append(cv2.countNonZero(roi))
            
            marcou = max(pixels_q) > 120
            idx_aluno = np.argmax(pixels_q)
            letra_aluno = ["A", "B", "C", "D"][idx_aluno] if marcou else "."
            res["respostas"][q_num] = letra_aluno

            # --- VISUALIZAÇÃO DA MÁSCARA ---
            # Coordenadas do aluno
            cx_aluno = int(bx + (idx_aluno * step_x))

            # Verifica Gabarito
            if gab_oficial and q_num in gab_oficial:
                correta = gab_oficial[q_num]
                idx_correta = ["A", "B", "C", "D"].index(correta)
                cx_correta = int(bx + (idx_correta * step_x))

                if marcou:
                    if letra_aluno == correta:
                        # ACERTO (Verde Cheio)
                        cv2.circle(img_mask, (cx_aluno, cy), 15, (0, 255, 0), -1)
                    else:
                        # ERRO (Vermelho Cheio no erro)
                        cv2.circle(img_mask, (cx_aluno, cy), 15, (0, 0, 255), -1)
                        # MOSTRA CORRETA (Anel Verde na certa)
                        cv2.circle(img_mask, (cx_correta, cy), 15, (0, 255, 0), 3)
                else:
                    # EM BRANCO (Amarelo na correta)
                    cv2.circle(img_mask, (cx_correta, cy), 10, (0, 255, 255), 2)
            
            elif marcou:
                 # Sem gabarito: Marca Cinza Cheio
                 cv2.circle(img_mask, (cx_aluno, cy), 12, (100, 100, 100), -1)

    return res, img_mask
