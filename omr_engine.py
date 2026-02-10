import cv2
import numpy as np
from layout_samar import ConfiguracaoProva

def order_points(pts):
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def alinhar_imagem(img, conf: ConfiguracaoProva):
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
        
    _, thresh = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    ancoras = []
    
    for c in cnts:
        area = cv2.contourArea(c)
        if 200 < area < 20000:
            x, y, w, h = cv2.boundingRect(c)
            ar = w / float(h)
            if 0.6 <= ar <= 1.4:
                M = cv2.moments(c)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    ancoras.append([cx, cy])
    
    if len(ancoras) >= 4:
        pts = np.array(ancoras, dtype="float32")
        rect = order_points(pts)
        
        scale = 2.0
        w_final = int(conf.PAGE_W * scale)
        h_final = int(conf.PAGE_H * scale)
        m = conf.MARGIN * scale
        
        dst = np.array([
            [m, m],
            [w_final - m, m],
            [w_final - m, h_final - m],
            [m, h_final - m]
        ], dtype="float32")
        
        M = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(img, M, (w_final, h_final)), scale
    
    return cv2.resize(img, (int(conf.PAGE_W*2), int(conf.PAGE_H*2))), 2.0

def processar_gabarito(img, conf: ConfiguracaoProva, gabarito=None, offset_x=0, offset_y=0):
    warped, scale = alinhar_imagem(img, conf)
    
    # Converter para cinza e aplicar threshold adaptativo (melhor para scanners variados)
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY_INV, 51, 10)
    
    res = {"respostas": {}, "frequencia": ""}
    img_vis = warped.copy()
    
    def pdf_to_pixel(x, y_pdf):
        px = int(x * scale) + offset_x
        py = int((conf.PAGE_H - y_pdf) * scale) + offset_y
        return px, py
    
    start_y = conf.GRID_START_Y
    
    # 1. FREQUÊNCIA (Lógica do Vencedor)
    if conf.tem_frequencia:
        val_freq = ""
        center_x = conf.FREQ_X + 27
        offset_col = 12
        
        for col_idx in range(2): 
            votos = []
            col_cx = center_x - offset_col if col_idx == 0 else center_x + offset_col
            
            for i in range(10):
                y_pos = start_y - 25 - (i * 18)
                cx, cy = pdf_to_pixel(col_cx, y_pos + 3)
                
                # Leitura mais ampla
                roi = thresh[cy-10:cy+10, cx-10:cx+10]
                votos.append(cv2.countNonZero(roi))
                cv2.circle(img_vis, (cx, cy), 10, (200,200,200), 1)
            
            # Compara as 10 bolinhas da coluna
            max_votos = max(votos)
            # Mínimo absoluto para considerar marcado (evita sujeira)
            if max_votos > (60 * scale): 
                idx = np.argmax(votos)
                val_freq += str(idx)
                
                y_hit = start_y - 25 - (idx * 18)
                cx, cy = pdf_to_pixel(col_cx, y_hit + 3)
                cv2.circle(img_vis, (cx, cy), 12, (255, 0, 0), -1)
            else:
                val_freq += "0"
        res["frequencia"] = val_freq
        
    # 2. QUESTÕES (Lógica do Vencedor: Comparativo)
    current_x = conf.GRID_X_START
    for bloco in conf.blocos:
        for i in range(bloco.quantidade):
            q_num = bloco.questao_inicial + i
            y_pos = start_y - 25 - (i * 20)
            
            densidade = []
            coords = []
            
            # Coleta dados das 4 alternativas
            for j in range(4): # A, B, C, D
                bx = current_x + 20 + (j * 20)
                cx, cy = pdf_to_pixel(bx, y_pos + 3)
                coords.append((cx, cy))
                
                roi = thresh[cy-10:cy+10, cx-10:cx+10]
                densidade.append(cv2.countNonZero(roi))
            
            # ANÁLISE COMPARATIVA
            # A letra impressa (A, B...) gera um pouco de preto (~40px).
            # A marcação do aluno gera muito preto (~200px).
            # O código vê quem tem MAIS preto.
            
            max_val = max(densidade)
            avg_val = sum(densidade) / 4
            idx_max = np.argmax(densidade)
            
            # Critérios para marcar:
            # 1. Tem que ter tinta suficiente (>80)
            # 2. Tem que ser bem maior que a média (para não confundir com as letras)
            if max_val > 80 and max_val > (avg_val * 1.4):
                marcou = True
                letra = ["A", "B", "C", "D"][idx_max]
                res["respostas"][q_num] = letra
            else:
                marcou = False
                letra = "."
                res["respostas"][q_num] = "."
                idx_max = 0 # Só para não quebrar o visual
            
            # Visualização
            cx, cy = coords[idx_max]
            if gabarito and q_num in gabarito:
                correta = gabarito[q_num]
                idx_c = ["A","B","C","D"].index(correta)
                cx_c, cy_c = coords[idx_c]
                
                if marcou:
                    if letra == correta:
                        cv2.circle(img_vis, (cx, cy), 13, (0, 255, 0), -1)
                    else:
                        cv2.circle(img_vis, (cx, cy), 13, (0, 0, 255), -1)
                        cv2.circle(img_vis, (cx_c, cy_c), 13, (0, 255, 0), 3)
                else:
                    cv2.circle(img_vis, (cx_c, cy_c), 10, (0, 255, 255), 2)
            elif marcou:
                cv2.circle(img_vis, (cx, cy), 10, (100, 100, 100), -1)

        current_x += conf.GRID_COL_W
        
    return res, img_vis
