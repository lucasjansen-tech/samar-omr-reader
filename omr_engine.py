import cv2
import numpy as np
from layout_samar import ConfiguracaoProva

def alinhar_imagem(img, conf: ConfiguracaoProva):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    ancoras = []
    
    for c in cnts:
        area = cv2.contourArea(c)
        if 200 < area < 20000:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.04 * peri, True)
            if len(approx) == 4:
                M = cv2.moments(c)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    ancoras.append([cx, cy])
    
    if len(ancoras) >= 4:
        pts = np.array(ancoras, dtype="float32")
        s = pts.sum(axis=1)
        diff = np.diff(pts, axis=1)
        rect = np.zeros((4, 2), dtype="float32")
        rect[0] = pts[np.argmin(s)]   
        rect[2] = pts[np.argmax(s)]   
        rect[1] = pts[np.argmin(diff)] 
        rect[3] = pts[np.argmax(diff)] 
        
        scale = 2.0
        w_target = int(conf.PAGE_W * scale)
        h_target = int(conf.PAGE_H * scale)
        m = conf.MARGIN * scale
        
        dst = np.array([
            [m, m],                     
            [w_target - m, m],          
            [w_target - m, h_target - m], 
            [m, h_target - m]           
        ], dtype="float32")
        
        M = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(img, M, (w_target, h_target)), scale
    
    return cv2.resize(img, (int(conf.PAGE_W*2), int(conf.PAGE_H*2))), 2.0

def refinar_centro(thresh_img, cx, cy, raio_busca=14):
    """
    ATRAÇÃO MAGNÉTICA: Procura o centro de massa de pixels pretos
    numa vizinhança para corrigir pequenos desalinhamentos.
    """
    y1 = max(0, cy - raio_busca)
    y2 = min(thresh_img.shape[0], cy + raio_busca)
    x1 = max(0, cx - raio_busca)
    x2 = min(thresh_img.shape[1], cx + raio_busca)
    
    roi = thresh_img[y1:y2, x1:x2]
    
    M = cv2.moments(roi)
    if M["m00"] > 50: # Se tem algo marcado ali
        # Calcula novo centro relativo ao ROI
        dx = int(M["m10"] / M["m00"])
        dy = int(M["m01"] / M["m00"])
        # Retorna coordenada global ajustada
        return x1 + dx, y1 + dy
    
    return cx, cy # Se vazio, mantém o original

def processar_gabarito(img, conf: ConfiguracaoProva, gabarito=None):
    warped, scale = alinhar_imagem(img, conf)
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    
    res = {"respostas": {}, "frequencia": ""}
    img_vis = warped.copy()
    
    def pdf_to_pixel(x, y_pdf):
        return int(x * scale), int((conf.PAGE_H - y_pdf) * scale)
    
    start_y = conf.GRID_START_Y
    
    # FREQUÊNCIA
    if conf.tem_frequencia:
        val_freq = ""
        box_w = 54
        box_x = conf.FREQ_X
        center_x = box_x + (box_w / 2)
        offset_x = 12
        
        for col_idx in range(2): 
            votos = []
            col_center_x = center_x - offset_x if col_idx == 0 else center_x + offset_x
            
            for i in range(10):
                y_base = start_y - 25 - (i * 18)
                cx_teorico, cy_teorico = pdf_to_pixel(col_center_x, y_base + 3)
                
                # APLICA ATRAÇÃO MAGNÉTICA
                cx, cy = refinar_centro(thresh, cx_teorico, cy_teorico)
                
                roi = thresh[cy-9:cy+9, cx-9:cx+9]
                votos.append(cv2.countNonZero(roi))
                cv2.circle(img_vis, (cx, cy), 9, (200,200,200), 1)
            
            if max(votos) > (60 * scale): # Sensibilidade ajustada
                idx = np.argmax(votos)
                val_freq += str(idx)
                y_hit = start_y - 25 - (idx * 18)
                cx_t, cy_t = pdf_to_pixel(col_center_x, y_hit + 3)
                cx, cy = refinar_centro(thresh, cx_t, cy_t)
                cv2.circle(img_vis, (cx, cy), 12, (255, 0, 0), -1)
            else:
                val_freq += "0"
        res["frequencia"] = val_freq
        
    # QUESTÕES
    current_x = conf.GRID_X_START
    for bloco in conf.blocos:
        for i in range(bloco.quantidade):
            q_num = bloco.questao_inicial + i
            y_base = start_y - 25 - (i * 20)
            
            pixels = []
            coords = []
            for j in range(4):
                bx = current_x + 20 + (j * 20)
                cx_teorico, cy_teorico = pdf_to_pixel(bx, y_base + 3)
                
                # APLICA ATRAÇÃO MAGNÉTICA
                cx, cy = refinar_centro(thresh, cx_teorico, cy_teorico)
                coords.append((cx, cy))
                
                roi = thresh[cy-9:cy+9, cx-9:cx+9]
                pixels.append(cv2.countNonZero(roi))
            
            marcou = max(pixels) > (60 * scale)
            idx = np.argmax(pixels)
            letra = ["A", "B", "C", "D"][idx] if marcou else "."
            res["respostas"][q_num] = letra
            
            cx, cy = coords[idx]
            if gabarito and q_num in gabarito:
                correta = gabarito[q_num]
                idx_c = ["A","B","C","D"].index(correta)
                # Pega coordenada já refinada (snap) se existir, senão teorica
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
