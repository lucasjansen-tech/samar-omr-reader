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
    # Redimensiona para largura padrão de 1000px
    h_orig, w_orig = imagem.shape[:2]
    ratio = 1000.0 / w_orig
    img_resize = cv2.resize(imagem, (1000, int(h_orig * ratio)))
    
    # 1. VISÃO DE CONTRASTE MÁXIMO
    # Converte para cinza e aplica Threshold BRUTO (não adaptativo)
    # Isso garante que o quadrado preto seja um "bloco maciço"
    gray = cv2.cvtColor(img_resize, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)
    
    # 2. ENCONTRAR AS 4 ÂNCORAS
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    ancoras_candidatas = []
    
    img_debug = img_resize.copy() # Para você ver o que ele achou

    for c in cnts:
        area = cv2.contourArea(c)
        # Aumentei o range: 1000 a 60000 pixels (cobre baixa e alta resolução)
        if 1000 < area < 60000:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.03 * peri, True)
            
            # Aceita quadriláteros (4 a 6 vértices para tolerar distorção)
            if 4 <= len(approx) <= 6:
                (x, y, w, h) = cv2.boundingRect(approx)
                ar = w / float(h)
                # Verifica se é "quadrado" (tolerância de 0.6 a 1.4)
                if 0.6 <= ar <= 1.4:
                    M = cv2.moments(c)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                        ancoras_candidatas.append((cx, cy))
                        # Desenha em AMARELO o que ele achou
                        cv2.drawContours(img_debug, [approx], -1, (0, 255, 255), 4)

    # 3. FILTRAGEM ESPACIAL (Pega os 4 cantos mais extremos)
    if len(ancoras_candidatas) >= 4:
        pts = np.array(ancoras_candidatas, dtype="float32")
        rect = order_points(pts)
        
        # Desenha em AZUL as 4 escolhidas na imagem de debug
        for p in rect:
            cv2.circle(img_debug, (int(p[0]), int(p[1])), 20, (255, 0, 0), -1)

        # WARP (Corte de Perspectiva) - Remove cabeçalho e bordas
        # Mapeia para 1000 x 1400 (Padrão SAMAR Interno)
        dst = np.array([
            [0, 0],
            [1000 - 1, 0],
            [1000 - 1, 1400 - 1],
            [0, 1400 - 1]], dtype="float32")

        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(img_resize, M, (1000, 1400))
        return warped, img_debug

    # FALLBACK (Só redimensiona e avisa que falhou)
    print("ALERTA: Âncoras não encontradas. Verifique a imagem de diagnóstico.")
    return cv2.resize(imagem, (1000, 1400)), img_debug

def extrair_dados(img_warped, gab_oficial=None):
    # Imagem PADRONIZADA 1000x1400 (Cortada nas âncoras)
    gray = cv2.cvtColor(img_warped, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    
    res = {"respostas": {}, "frequencia": ""}
    img_mask = img_warped.copy()

    # --- 1. FREQUÊNCIA ---
    # Coordenadas calibradas para imagem cortada (sem cabeçalho)
    # X ajustado para direita
    cols_freq = [("D", 145), ("U", 192)] 
    freq_final = ""

    for nome, x in cols_freq:
        votos = []
        for i in range(10):
            # Y calibrado
            y = int(245 + (i * 35))
            roi = thresh[y-15:y+15, x-15:x+15]
            votos.append(cv2.countNonZero(roi))
            # Guia Azul Vazía
            cv2.circle(img_mask, (x, y), 15, (255, 200, 0), 1)
        
        if max(votos) > 120:
            idx = np.argmax(votos)
            freq_final += str(idx)
            cv2.circle(img_mask, (x, int(245 + (idx * 35))), 15, (255, 0, 0), -1)
        else:
            freq_final += "0"
            
    res["frequencia"] = freq_final

    # --- 2. QUESTÕES ---
    # Coordenadas X, Y dos 4 blocos
    blocos = [
        (265, 460, 1),   # Bloco 1 (Esq)
        (580, 460, 14),  # Bloco 2 (Dir)
        (265, 990, 27),  # Bloco 3 (Esq Baixo)
        (580, 990, 40)   # Bloco 4 (Dir Baixo)
    ]
    
    step_x = 50 
    step_y = 36.5 

    for (bx, by, q_start) in blocos:
        for i in range(13):
            q_num = q_start + i
            cy = int(by + (i * step_y))
            
            pixels_q = []
            for j in range(4): 
                cx = int(bx + (j * step_x))
                roi = thresh[cy-15:cy+15, cx-15:cx+15]
                pixels_q.append(cv2.countNonZero(roi))
            
            marcou = max(pixels_q) > 120
            idx_aluno = np.argmax(pixels_q)
            letra_aluno = ["A", "B", "C", "D"][idx_aluno] if marcou else "."
            res["respostas"][q_num] = letra_aluno

            # DESENHO DA MÁSCARA
            cx_aluno = int(bx + (idx_aluno * step_x))
            
            if gab_oficial and q_num in gab_oficial:
                correta = gab_oficial[q_num]
                idx_correta = ["A", "B", "C", "D"].index(correta)
                cx_correta = int(bx + (idx_correta * step_x))

                if marcou:
                    if letra_aluno == correta:
                        cv2.circle(img_mask, (cx_aluno, cy), 15, (0, 255, 0), -1) # Verde
                    else:
                        cv2.circle(img_mask, (cx_aluno, cy), 15, (0, 0, 255), -1) # Vermelho
                        cv2.circle(img_mask, (cx_correta, cy), 15, (0, 255, 0), 3) # Anel
                else:
                    cv2.circle(img_mask, (cx_correta, cy), 10, (0, 255, 255), 2)
            elif marcou:
                 cv2.circle(img_mask, (cx_aluno, cy), 12, (100, 100, 100), -1)

    return res, img_mask
