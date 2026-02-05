import cv2
import numpy as np
from PIL import Image, ImageOps

def tratar_entrada(img_pil):
    img_pil = ImageOps.exif_transpose(img_pil)
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

def alinhar_gabarito(imagem):
    gray = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
    
    # Binarização focada em objetos sólidos pretos (Âncoras)
    _, thresh = cv2.threshold(gray, 80, 255, cv2.THRESH_BINARY_INV)
    
    # Encontra contornos
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    ancoras = []

    for c in cnts:
        area = cv2.contourArea(c)
        # Filtro de tamanho para pegar apenas os quadrados das âncoras
        if 400 < area < 8000: 
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.04 * peri, True)
            
            # Verifica se é um quadrado (4 vértices)
            if len(approx) == 4:
                (x, y, w, h) = cv2.boundingRect(approx)
                aspect_ratio = w / float(h)
                # Verifica se é "quadrado" (proporção próxima de 1)
                if 0.8 <= aspect_ratio <= 1.2:
                    M = cv2.moments(c)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                        ancoras.append((cx, cy))

    # Precisamos de exatamente 4 âncoras
    if len(ancoras) == 4:
        pts = np.array(ancoras, dtype="float32")
        
        # Ordenação: Top-Esq, Top-Dir, Inf-Dir, Inf-Esq
        s = pts.sum(axis=1)
        diff = np.diff(pts, axis=1)
        
        tl = pts[np.argmin(s)]
        br = pts[np.argmax(s)]
        tr = pts[np.argmin(diff)]
        bl = pts[np.argmax(diff)]
        
        rect = np.array([tl, tr, br, bl], dtype="float32")

        # Warp para tamanho fixo PADRÃO (800x1100)
        # Isso garante que as coordenadas das bolinhas sejam sempre as mesmas
        dst = np.array([
            [0, 0],
            [800 - 1, 0],
            [800 - 1, 1100 - 1],
            [0, 1100 - 1]], dtype="float32")

        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(imagem, M, (800, 1100))
        return warped
    
    return None

def extrair_dados(img_warped, gab_oficial=None):
    gray = cv2.cvtColor(img_warped, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    
    res = {"respostas": {}, "frequencia": ""}
    # Cria uma cópia da imagem para desenhar a "Máscara"
    img_mask = img_warped.copy() 

    # --- 1. FREQUÊNCIA (Colunas D e U) ---
    # Coordenadas ajustadas para o warp de 800x1100
    cols_freq = [("D", 85), ("U", 125)]
    freq_result = ""

    for nome, x in cols_freq:
        votos = []
        for i in range(10):
            y = int(140 + (i * 26.5)) # Ajuste fino vertical
            roi = thresh[y-8:y+8, x-8:x+8]
            votos.append(cv2.countNonZero(roi))
        
        # Se marcou algo
        if max(votos) > 60:
            idx = np.argmax(votos)
            freq_result += str(idx)
            # Desenha na máscara (Azul para dados cadastrais)
            cv2.circle(img_mask, (x, int(140 + (idx * 26.5))), 10, (255, 0, 0), -1)
        else:
            freq_result += "0" # Padrão: Se não marcou, é 0
            
    res["frequencia"] = freq_result

    # --- 2. QUESTÕES (Grade Completa) ---
    # Coordenadas dos blocos
    blocos = [
        (175, 335, 1),   # Bloco 1 (Esq)
        (430, 335, 14),  # Bloco 2 (Dir)
        (175, 755, 27),  # Bloco 3 (Esq Baixo)
        (430, 755, 40)   # Bloco 4 (Dir Baixo)
    ]
    
    step_x = 39 # Distância horizontal entre bolinhas
    step_y = 28 # Distância vertical entre questões

    for (bx, by, q_start) in blocos:
        for i in range(13):
            q_num = q_start + i
            cy = int(by + (i * step_y))
            
            pixels_q = []
            for j in range(4): # A, B, C, D
                cx = int(bx + (j * step_x))
                roi = thresh[cy-10:cy+10, cx-10:cx+10]
                pixels_q.append(cv2.countNonZero(roi))
            
            marcou = max(pixels_q) > 65
            idx_aluno = np.argmax(pixels_q)
            letra_aluno = ["A", "B", "C", "D"][idx_aluno] if marcou else "."
            res["respostas"][q_num] = letra_aluno

            # --- LÓGICA DA MÁSCARA VISUAL ---
            if gab_oficial and q_num in gab_oficial:
                correta = gab_oficial[q_num]
                idx_correta = ["A", "B", "C", "D"].index(correta)
                cx_correta = int(bx + (idx_correta * step_x))

                if letra_aluno == correta:
                    # ACERTOU: Pinta a bolinha do aluno de VERDE
                    cx_aluno = int(bx + (idx_aluno * step_x))
                    cv2.circle(img_mask, (cx_aluno, cy), 12, (0, 255, 0), -1) 
                else:
                    if marcou:
                        # ERROU: Pinta a bolinha do aluno de VERMELHO
                        cx_aluno = int(bx + (idx_aluno * step_x))
                        cv2.circle(img_mask, (cx_aluno, cy), 12, (0, 0, 255), -1)
                    
                    # MOSTRA A CORRETA: Desenha um anel VERDE na resposta certa
                    cv2.circle(img_mask, (cx_correta, cy), 12, (0, 255, 0), 2)
            
            elif marcou:
                # Se não tem gabarito, apenas marca o que o aluno fez em amarelo (neutro)
                cx_aluno = int(bx + (idx_aluno * step_x))
                cv2.circle(img_mask, (cx_aluno, cy), 10, (0, 255, 255), -1)

    return res, img_mask
