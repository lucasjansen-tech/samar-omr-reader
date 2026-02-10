import cv2
import numpy as np
from layout_samar import ConfiguracaoProva

def order_points(pts):
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)] # TL
    rect[2] = pts[np.argmax(s)] # BR
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)] # TR
    rect[3] = pts[np.argmax(diff)] # BL
    return rect

def alinhar_imagem(img, conf: ConfiguracaoProva):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Binarização forte para pegar preto puro
    _, thresh = cv2.threshold(gray, 80, 255, cv2.THRESH_BINARY_INV)
    
    h, w = img.shape[:2]
    
    # ESTRATÉGIA DE QUADRANTES (INFALÍVEL PARA SCANNER)
    # Divide a imagem em 4 pedaços e pega o maior objeto preto de cada canto.
    # Isso evita ter que achar um "quadrado perfeito".
    
    centros = []
    # Margens de busca (ignora borda suja e foca no canto)
    sectores = [
        (0, 0, w//2, h//2),         # Top-Left
        (w//2, 0, w, h//2),         # Top-Right
        (w//2, h//2, w, h),         # Bottom-Right
        (0, h//2, w//2, h)          # Bottom-Left
    ]
    
    for (x1, y1, x2, y2) in sectores:
        roi = thresh[y1:y2, x1:x2]
        cnts, _ = cv2.findContours(roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if cnts:
            # Pega o maior contorno (a âncora)
            c = max(cnts, key=cv2.contourArea)
            if cv2.contourArea(c) > 100: # Filtro de ruído
                M = cv2.moments(c)
                if M["m00"] != 0:
                    cx = int((M["m10"] / M["m00"]) + x1)
                    cy = int((M["m01"] / M["m00"]) + y1)
                    centros.append([cx, cy])

    if len(centros) == 4:
        pts = np.array(centros, dtype="float32")
        rect = order_points(pts)
        
        # Warp para tamanho 2x (Alta definição)
        scale = 2.0
        w_final = int(conf.PAGE_W * scale)
        h_final = int(conf.PAGE_H * scale)
        
        # Onde as âncoras DEVEM estar (baseado no layout.py)
        m = conf.MARGIN * scale
        
        dst = np.array([
            [m, m],                     
            [w_final - m, m],           
            [w_final - m, h_final - m], 
            [m, h_final - m]            
        ], dtype="float32")
        
        M = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(img, M, (w_final, h_final)), scale
    
    # Fallback
    return cv2.resize(img, (int(conf.PAGE_W*2), int(conf.PAGE_H*2))), 2.0

def processar_gabarito(img, conf: ConfiguracaoProva, gabarito=None):
    warped, scale = alinhar_imagem(img, conf)
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    
    res = {"respostas": {}, "frequencia": ""}
    img_vis = warped.copy()
    
    # Conversão PDF (Y sobe) -> Imagem (Y desce)
    def pdf_to_pixel(x, y_pdf):
        return int(x * scale), int((conf.PAGE_H - y_pdf) * scale)
    
    start_y = conf.GRID_START_Y
    
    # FREQUÊNCIA
    if conf.tem_frequencia:
        val_freq = ""
        box_x = conf.FREQ_X
        # O gerador usa largura 54
        center_x = box_x + 27 
        offset_x = 12
        
        for col_idx in range(2): 
            votos = []
            col_center_x = center_x - offset_x if col_idx == 0 else center_x + offset_x
            
            for i in range(10):
                y_base = start_y - 25 - (i * 18)
                cx, cy = pdf_to_pixel(col_center_x, y_base + 3)
                
                # ROI de Leitura
                roi = thresh[cy-9:cy+9, cx-9:cx+9]
                votos.append(cv2.countNonZero(roi))
                
                # Visualização Cinza (Onde procurou)
                cv2.circle(img_vis, (cx, cy), 9, (200,200,200), 1)
            
            if max(votos) > (50 * scale):
                idx = np.argmax(votos)
                val_freq += str(idx)
                # Visualização Azul (O que achou)
                y_hit = start_y - 25 - (idx * 18)
                cx, cy = pdf_to_pixel(col_center_x, y_hit + 3)
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
                cx, cy = pdf_to_pixel(bx, y_base + 3)
                coords.append((cx, cy))
                
                roi = thresh[cy-9:cy+9, cx-9:cx+9]
                pixels.append(cv2.countNonZero(roi))
            
            marcou = max(pixels) > (50 * scale)
            idx = np.argmax(pixels)
            letra = ["A", "B", "C", "D"][idx] if marcou else "."
            res["respostas"][q_num] = letra
            
            # Máscara de Correção
            cx, cy = coords[idx]
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
