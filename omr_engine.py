import cv2
import numpy as np
from PIL import Image, ImageOps

def tratar_entrada(img_pil):
    img_pil = ImageOps.exif_transpose(img_pil)
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

def alinhar_gabarito(imagem):
    gray = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
    # Binarização agressiva para pegar apenas o que é PRETO PURO (âncoras)
    _, thresh = cv2.threshold(gray, 80, 255, cv2.THRESH_BINARY_INV)
    
    # Encontra contornos
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    ancoras_candidatas = []

    img_debug = imagem.copy()

    for c in cnts:
        area = cv2.contourArea(c)
        # Filtra quadrados pretos (Tamanho médio esperado no SAMAR)
        if 300 < area < 5000: 
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.04 * peri, True)
            if len(approx) == 4: # É um quadrado?
                M = cv2.moments(c)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    ancoras_candidatas.append((cx, cy))
                    # Marca em vermelho para você ver se ele achou
                    cv2.drawContours(img_debug, [approx], -1, (0, 0, 255), 5)

    # Precisamos de exatamente 4 âncoras
    if len(ancoras_candidatas) >= 4:
        # Ordena os pontos (Top-Esq, Top-Dir, Inf-Dir, Inf-Esq)
        pts = np.array(ancoras_candidatas[:4], dtype="float32")
        
        # Lógica de ordenação robusta
        s = pts.sum(axis=1)
        diff = np.diff(pts, axis=1)
        
        tl = pts[np.argmin(s)]       # Menor soma = Top-Left
        br = pts[np.argmax(s)]       # Maior soma = Bottom-Right
        tr = pts[np.argmin(diff)]    # Menor diferença = Top-Right
        bl = pts[np.argmax(diff)]    # Maior diferença = Bottom-Left
        
        rect = np.array([tl, tr, br, bl], dtype="float32")

        # Dimensões fixas para onde vamos esticar a imagem (Padronização)
        width, height = 800, 1000
        dst = np.array([
            [0, 0],
            [width - 1, 0],
            [width - 1, height - 1],
            [0, height - 1]], dtype="float32")

        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(imagem, M, (width, height))
        
        return warped, img_debug

    return None, img_debug

def extrair_dados(img_warped, gab_oficial=None):
    # Agora trabalhamos na imagem recortada (800x1000)
    # O (0,0) é o centro da âncora superior esquerda
    
    gray = cv2.cvtColor(img_warped, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    
    res = {"respostas": {}, "frequencia": ""}
    vis = img_warped.copy()

    # --- 1. FREQUÊNCIA (Baseada no Topo Esquerdo) ---
    # Ajuste de coordenadas relativo à âncora superior esquerda (0,0)
    start_y_freq = 110  # Distância vertical da âncora até a primeira bolinha (0)
    step_y = 24.5       # Distância entre bolinhas
    
    cols_freq = [
        ("D", 85),  # Coluna D está ~85px para a direita da âncora
        ("U", 125)  # Coluna U está ~125px para a direita
    ]
    
    f_code = ""
    for nome, x in cols_freq:
        pixels_col = []
        for i in range(10):
            y = int(start_y_freq + (i * step_y))
            # Desenha onde está procurando (Círculo Azul Vazio)
            cv2.circle(vis, (x, y), 5, (255, 100, 0), 1)
            
            roi = thresh[y-8:y+8, x-8:x+8]
            pixels_col.append(cv2.countNonZero(roi))
        
        # Verifica qual está marcado
        if max(pixels_col) > 60:
            idx = np.argmax(pixels_col)
            f_code += str(idx)
            # Marca o encontrado (Azul Preenchido)
            y_hit = int(start_y_freq + (idx * step_y))
            cv2.circle(vis, (x, y_hit), 9, (255, 0, 0), -1)
        else:
            f_code += "0"
            
    res["frequencia"] = f_code

    # --- 2. QUESTÕES (Grade de 4 Blocos) ---
    # Coordenadas medidas a partir das âncoras cortadas
    # Bloco 1 (Q1) começa mais abaixo
    
    y_start_blocos = 290
    step_x_questions = 38  # Distância entre A e B
    
    blocos = [
        (175, y_start_blocos, 1),   # Bloco 1 (Esq)
        (430, y_start_blocos, 14),  # Bloco 2 (Dir)
        (175, 670, 27),             # Bloco 3 (Esq Baixo)
        (430, 670, 40)              # Bloco 4 (Dir Baixo)
    ]
    
    for (bx, by, q_start) in blocos:
        for i in range(13): # 13 questões por bloco
            q_num = q_start + i
            cy = int(by + (i * 25.2)) # Passo vertical das questões
            
            votos_q = []
            for j in range(4): # A, B, C, D
                cx = int(bx + (j * step_x_questions))
                # Guia visual (onde o robô olha)
                cv2.circle(vis, (cx, cy), 4, (0, 255, 0), 1)
                
                roi = thresh[cy-9:cy+9, cx-9:cx+9]
                votos_q.append(cv2.countNonZero(roi))
            
            # Análise
            marcou = max(votos_q) > 65
            idx_max = np.argmax(votos_q)
            letra = ["A", "B", "C", "D"][idx_max] if marcou else "."
            res["respostas"][q_num] = letra
            
            if marcou:
                # Marcação do Aluno (Verde Preenchido)
                cx_hit = int(bx + (idx_max * step_x_questions))
                cv2.circle(vis, (cx_hit, cy), 10, (0, 255, 0), -1)
            
            # Correção Visual (Gabarito)
            if gab_oficial and gab_oficial.get(q_num):
                correta_idx = ["A", "B", "C", "D"].index(gab_oficial[q_num])
                cx_corr = int(bx + (correta_idx * step_x_questions))
                # Ponto vermelho no centro da correta
                cv2.circle(vis, (cx_corr, cy), 4, (0, 0, 255), -1)

    return res, vis
