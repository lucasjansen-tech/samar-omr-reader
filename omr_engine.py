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
        if 200 < area < 15000:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.04 * peri, True)
            if len(approx) == 4:
                M = cv2.moments(c)
                if M["m00"] != 0:
                    cx, cy = int(M["m10"]/M["m00"]), int(M["m01"]/M["m00"])
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
        
        # AQUI ESTÁ A CORREÇÃO DE SIMETRIA NO ALINHAMENTO
        # Usamos conf.MARGIN para todos os cantos
        m = conf.MARGIN * scale
        
        dst = np.array([
            [m, m],                     # Top-Left
            [w_target - m, m],          # Top-Right
            [w_target - m, h_target - m], # Bottom-Right (subiu conforme MARGIN)
            [m, h_target - m]           # Bottom-Left  (subiu conforme MARGIN)
        ], dtype="float32")
        
        M = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(img, M, (w_target, h_target)), scale
    
    return cv2.resize(img, (int(conf.PAGE_W*2), int(conf.PAGE_H*2))), 2.0

def processar_gabarito(img, conf: ConfiguracaoProva, gabarito=None):
    warped, scale = alinhar_imagem(img, conf)
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    
    res = {"respostas": {}, "frequencia": ""}
    img_vis = warped.copy()
    
    def pt_to_px(x, y_pdf):
        return int(x * scale), int((conf.PAGE_H - y_pdf) * scale)
    
    # 1. FREQUÊNCIA
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
                y_base = conf.GRID_START_Y - 25 - (i * 18)
                cx, cy = pt_to_px(col_center_x, y_base + 3)
                roi = thresh[cy-10:cy+10, cx-10:cx+10]
                votos.append(cv2.countNonZero(roi))
                cv2.circle(img_vis, (cx, cy), 10, (200,200,200), 1)
            
            if max(votos) > 100:
                idx = np.argmax(votos)
                val_freq += str(idx)
                y_hit = conf.GRID_START_Y - 25 - (idx * 18)
                cx, cy = pt_to_px(col_center_x, y_hit + 3)
                cv2.circle(img_vis, (cx, cy), 13, (255, 0, 0), -1)
            else:
                val_freq += "0"
        res["frequencia"] = val_freq
        
    # 2. QUESTÕES
    current_x = conf.GRID_X_START
    for bloco in conf.blocos:
        for i in range(bloco.quantidade):
            q_num = bloco.questao_inicial + i
            y_base = conf.GRID_START_Y - 25 - (i * 20)
            
            pixels = []
            coords = []
            for j in range(4):
                bx = current_x + 20 + (j * 20)
                cx, cy = pt_to_px(bx, y_base + 3)
                coords.append((cx, cy))
                roi = thresh[cy-10:cy+10, cx-10:cx+10]
                pixels.append(cv2.countNonZero(roi))
            
            marcou = max(pixels) > 100
            idx = np.argmax(pixels)
            letra = ["A", "B", "C", "D"][idx] if marcou else "."
            res["respostas"][q_num] = letra
            
            cx, cy = coords[idx]
            if gabarito and q_num in gabarito:
                correta = gabarito[q_num]
                idx_c = ["A","B","C","D"].index(correta)
                cx_c, cy_c = coords[idx_c]
                if marcou:
                    if letra == correta:
                        cv2.circle(img_vis, (cx, cy), 14, (0, 255, 0), -1)
                    else:
                        cv2.circle(img_vis, (cx, cy), 14, (0, 0, 255), -1)
                        cv2.circle(img_vis, (cx_c, cy_c), 14, (0, 255, 0), 3)
                else:
                    cv2.circle(img_vis, (cx_c, cy_c), 10, (0, 255, 255), 2)
            elif marcou:
                cv2.circle(img_vis, (cx, cy), 10, (100, 100, 100), -1)
                
        current_x += conf.GRID_COL_W
        
    return res, img_vis
