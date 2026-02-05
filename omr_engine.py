import cv2
import numpy as np
from PIL import Image, ImageOps

def tratar_entrada(img_pil):
    img_pil = ImageOps.exif_transpose(img_pil)
    # Converte para BGR (OpenCV)
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

def alinhar_gabarito(imagem):
    # Padronizamos a largura para 1000px para garantir que as coordenadas batam
    altura_orig, largura_orig = imagem.shape[:2]
    proporcao = 1000 / float(largura_orig)
    novo_tamanho = (1000, int(altura_orig * proporcao))
    imagem_resized = cv2.resize(imagem, novo_tamanho)
    
    gray = cv2.cvtColor(imagem_resized, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 80, 255, cv2.THRESH_BINARY_INV)
    
    # 1. Tenta achar as 4 âncoras (Quadrados Pretos)
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    ancoras = []

    for c in cnts:
        area = cv2.contourArea(c)
        if 400 < area < 10000: # Filtro de tamanho
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.04 * peri, True)
            if len(approx) == 4:
                (x, y, w, h) = cv2.boundingRect(approx)
                ar = w / float(h)
                if 0.8 <= ar <= 1.2: # É quadrado?
                    M = cv2.moments(c)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                        ancoras.append((cx, cy))

    # Se achou as 4 âncoras, faz o corte de perspectiva
    if len(ancoras) == 4:
        pts = np.array(ancoras, dtype="float32")
        s = pts.sum(axis=1)
        diff = np.diff(pts, axis=1)
        
        tl = pts[np.argmin(s)]
        br = pts[np.argmax(s)]
        tr = pts[np.argmin(diff)]
        bl = pts[np.argmax(diff)]
        
        rect = np.array([tl, tr, br, bl], dtype="float32")
        # Warp para tamanho fixo de trabalho (1000x1400)
        dst = np.array([[0, 0], [1000-1, 0], [1000-1, 1400-1], [0, 1400-1]], dtype="float32")
        M = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(imagem_resized, M, (1000, 1400))
    
    # 2. FALLBACK: Se não achou âncoras, assume que a imagem É a página
    # Apenas redimensiona para 1000x1400 (Padrão de coordenadas)
    # Isso resolve o erro "Falha ao reconhecer âncoras" em PDFs digitais
    return cv2.resize(imagem, (1000, 1400))

def extrair_dados(img_warped, gab_oficial=None):
    # Imagem deve ter 1000x1400 neste ponto
    gray = cv2.cvtColor(img_warped, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    
    res = {"respostas": {}, "frequencia": ""}
    # Cria a "Máscara" visual sobre a imagem original
    img_mask = img_warped.copy()

    # --- FREQUÊNCIA ---
    # Coordenadas baseadas na largura 1000px
    # Ajuste aqui se a bolinha estiver desencontrada
    cols_freq = [("D", 108), ("U", 155)] 
    freq_final = ""

    for nome, x in cols_freq:
        votos = []
        for i in range(10):
            # y inicial + passo
            y = int(180 + (i * 33)) 
            roi = thresh[y-10:y+10, x-10:x+10]
            votos.append(cv2.countNonZero(roi))
        
        if max(votos) > 100:
            idx = np.argmax(votos)
            freq_final += str(idx)
            # Desenha bolinha Azul na frequência detectada
            cv2.circle(img_mask, (x, int(180 + (idx * 33))), 12, (255, 0, 0), -1)
        else:
            freq_final += "0"
            
    res["frequencia"] = freq_final

    # --- QUESTÕES ---
    # Coordenadas dos blocos (X, Y, Questão Inicial)
    # Calibrado para imagem 1000x1400
    blocos = [
        (220, 425, 1),   # Bloco 1
        (535, 425, 14),  # Bloco 2
        (220, 950, 27),  # Bloco 3
        (535, 950, 40)   # Bloco 4
    ]
    
    step_x = 48 # Distância entre A e B
    step_y = 35 # Distância entre Q1 e Q2

    for (bx, by, q_start) in blocos:
        for i in range(13):
            q_num = q_start + i
            cy = int(by + (i * step_y))
            
            pixels_q = []
            for j in range(4): # A, B, C, D
                cx = int(bx + (j * step_x))
                roi = thresh[cy-12:cy+12, cx-12:cx+12]
                pixels_q.append(cv2.countNonZero(roi))
            
            marcou = max(pixels_q) > 100
            idx_aluno = np.argmax(pixels_q)
            letra_aluno = ["A", "B", "C", "D"][idx_aluno] if marcou else "."
            res["respostas"][q_num] = letra_aluno

            # --- DESENHO DA MÁSCARA ---
            cx_aluno = int(bx + (idx_aluno * step_x))
            
            if gab_oficial and q_num in gab_oficial:
                correta = gab_oficial[q_num]
                idx_correta = ["A", "B", "C", "D"].index(correta)
                cx_correta = int(bx + (idx_correta * step_x))

                if marcou:
                    if letra_aluno == correta:
                        # ACERTOU: Bola VERDE cheia
                        cv2.circle(img_mask, (cx_aluno, cy), 14, (0, 255, 0), -1)
                    else:
                        # ERROU: Bola VERMELHA cheia (na marcação do aluno)
                        cv2.circle(img_mask, (cx_aluno, cy), 14, (0, 0, 255), -1)
                        # MOSTRA CORRETA: Anel VERDE (na resposta certa)
                        cv2.circle(img_mask, (cx_correta, cy), 14, (0, 255, 0), 3)
                else:
                    # EM BRANCO: Mostra qual era a correta com anel AMARELO
                    cv2.circle(img_mask, (cx_correta, cy), 10, (0, 255, 255), 2)
            
            elif marcou:
                # Sem gabarito: Apenas marca o que foi lido em Cinza
                cv2.circle(img_mask, (cx_aluno, cy), 10, (100, 100, 100), -1)

    return res, img_mask
