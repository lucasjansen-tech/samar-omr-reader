import cv2
import numpy as np
from layout_samar import ConfiguracaoProva, GridConfig

def encontrar_ancoras_globais(thresh):
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidatos = []
    h, w = thresh.shape
    for c in cnts:
        area = cv2.contourArea(c)
        if area < 100 or area > (w*h*0.1): continue
        approx = cv2.approxPolyDP(c, 0.04 * cv2.arcLength(c, True), True)
        if len(approx) == 4:
            _, _, bw, bh = cv2.boundingRect(approx)
            ar = bw / float(bh)
            if 0.7 <= ar <= 1.3:
                M = cv2.moments(c)
                if M["m00"] != 0:
                    candidatos.append([int(M["m10"]/M["m00"]), int(M["m01"]/M["m00"])])
    if len(candidatos) < 4: return None
    pts = np.array(candidatos, dtype="float32")
    s = pts.sum(axis=1); d = np.diff(pts, axis=1)
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]], dtype="float32")

def alinhar_imagem(img, conf: ConfiguracaoProva):
    if len(img.shape) == 3: gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else: gray = img
    
    # Blur leve
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Threshold ajustado para lidar melhor com sombras
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY_INV, 31, 15)
    
    rect = encontrar_ancoras_globais(thresh)
    W_FINAL, H_FINAL = conf.REF_W, conf.REF_H
    
    if rect is not None:
        m = int(W_FINAL * conf.MARGIN_PCT)
        dst = np.array([[m, m], [W_FINAL-m, m], [W_FINAL-m, H_FINAL-m], [m, H_FINAL-m]], dtype="float32")
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(img, M, (W_FINAL, H_FINAL))
        # Retorna também o threshold da imagem warpada para leitura limpa
        warped_gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
        warped_thresh = cv2.adaptiveThreshold(warped_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                              cv2.THRESH_BINARY_INV, 31, 15)
        return warped, warped_thresh, W_FINAL, H_FINAL
        
    # Fallback
    resized = cv2.resize(img, (W_FINAL, H_FINAL))
    resized_gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY) if len(resized.shape) == 3 else resized
    resized_thresh = cv2.adaptiveThreshold(resized_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                           cv2.THRESH_BINARY_INV, 31, 15)
    return resized, resized_thresh, W_FINAL, H_FINAL

def ler_grid(img_thresh, grid: GridConfig, w_img, h_img, img_debug):
    x1 = int(grid.x_start * w_img)
    x2 = int(grid.x_end * w_img)
    y1 = int(grid.y_start * h_img)
    y2 = int(grid.y_end * h_img)
    
    # Visualização da área do Grid (Verde)
    cv2.rectangle(img_debug, (x1, y1), (x2, y2), (0, 255, 0), 2)
    
    cell_h = (y2 - y1) / grid.rows
    cell_w = (x2 - x1) / grid.cols
    res_bloco = {}
    
    # --- FREQUÊNCIA ---
    if grid.labels == ["D", "U"]:
        freq_res = ["0", "0"]
        for c in range(grid.cols):
            col_votos = []
            for r in range(grid.rows):
                cx = int(x1 + (c * cell_w) + (cell_w/2))
                cy = int(y1 + (r * cell_h) + (cell_h/2))
                
                # Raio de 22% da célula (equilibrio entre pegar tudo e evitar borda)
                raio = int(min(cell_h, cell_w) * 0.22) 
                
                roi = img_thresh[cy-raio:cy+raio, cx-raio:cx+raio]
                pixels = cv2.countNonZero(roi)
                col_votos.append(pixels)
                
                # Debug onde leu
                cv2.circle(img_debug, (cx, cy), 2, (0, 255, 255), -1)
            
            idx_max = np.argmax(col_votos)
            max_val = max(col_votos)
            area_roi = (raio*2)**2
            
            # Sensibilidade: 35% de preenchimento (mais permissivo)
            if max_val > (area_roi * 0.35):
                freq_res[c] = str(idx_max)
                cy_hit = int(y1 + (idx_max * cell_h) + (cell_h/2))
                cx_hit = int(x1 + (c * cell_w) + (cell_w/2))
                cv2.circle(img_debug, (cx_hit, cy_hit), int(raio*1.2), (255, 0, 0), -1)
        
        return "".join(freq_res), {}

    # --- QUESTÕES ---
    for r in range(grid.rows):
        cy = int(y1 + (r * cell_h) + (cell_h/2))
        densidades = []
        centros = []
        
        for c in range(grid.cols):
            cx = int(x1 + (c * cell_w) + (cell_w/2))
            centros.append((cx, cy))
            
            raio = int(min(cell_h, cell_w) * 0.22)
            
            roi = img_thresh[cy-raio:cy+raio, cx-raio:cx+raio]
            densidades.append(cv2.countNonZero(roi))
            
        max_v = max(densidades)
        idx_max = np.argmax(densidades)
        avg_v = sum(densidades)/4
        area_roi = (raio*2)**2
        
        marcou = False
        letra = "."
        
        # Lógica calibrada: 
        # Precisa ter 35% de preenchimento E ser 25% maior que a média (destaque)
        if max_v > (area_roi * 0.35) and max_v > (avg_v * 1.25):
            marcou = True
            letra = grid.labels[idx_max]
            
        if grid.questao_inicial > 0:
            res_bloco[grid.questao_inicial + r] = letra
            if marcou:
                cv2.circle(img_debug, centros[idx_max], int(raio*1.2), (0, 255, 0), 2)
            else:
                cv2.circle(img_debug, centros[idx_max], 2, (150, 150, 150), -1)

    return None, res_bloco

def processar_gabarito(img, conf: ConfiguracaoProva, gabarito=None, offset_x=0, offset_y=0):
    # Obtém imagem alinhada E imagem binarizada limpa
    warped, thresh, w, h = alinhar_imagem(img, conf)
    
    vis = warped.copy()
    final = {"respostas": {}, "frequencia": "00"}
    
    for g in conf.grids:
        f_val, r_dict = ler_grid(thresh, g, w, h, vis)
        if g.labels == ["D", "U"]: final["frequencia"] = f_val
        else: final["respostas"].update(r_dict)
            
    return final, vis, None
