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
    # Converte para cinza
    if len(img.shape) == 3: gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else: gray = img
    
    # 1. MELHORIA DE CONTRASTE (CLAHE) - Segredo para ler marcas fracas
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    gray = clahe.apply(gray)
    
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    # Threshold agressivo para achar âncoras pretas
    _, thresh_ancoras = cv2.threshold(blurred, 80, 255, cv2.THRESH_BINARY_INV)
    
    rect = encontrar_ancoras_globais(thresh_ancoras)
    W_FINAL, H_FINAL = conf.REF_W, conf.REF_H
    
    if rect is not None:
        m = int(W_FINAL * conf.MARGIN_PCT)
        dst = np.array([[m, m], [W_FINAL-m, m], [W_FINAL-m, H_FINAL-m], [m, H_FINAL-m]], dtype="float32")
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(gray, M, (W_FINAL, H_FINAL)) # Usa a imagem cinza melhorada
        
        # Threshold adaptativo na imagem alinhada para ler as bolinhas
        warped_thresh = cv2.adaptiveThreshold(warped, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                              cv2.THRESH_BINARY_INV, 35, 10)
        return cv2.cvtColor(warped, cv2.COLOR_GRAY2BGR), warped_thresh, W_FINAL, H_FINAL
    
    # Fallback
    r = cv2.resize(gray, (W_FINAL, H_FINAL))
    rt = cv2.adaptiveThreshold(r, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 35, 10)
    return cv2.cvtColor(r, cv2.COLOR_GRAY2BGR), rt, W_FINAL, H_FINAL

def ler_grid(img_thresh, grid: GridConfig, w_img, h_img, img_debug):
    x1 = int(grid.x_start * w_img)
    x2 = int(grid.x_end * w_img)
    y1 = int(grid.y_start * h_img)
    y2 = int(grid.y_end * h_img)
    
    cv2.rectangle(img_debug, (x1, y1), (x2, y2), (0, 255, 0), 2)
    
    # Divisão Matemática Precisa
    centros_y = np.linspace(y1, y2, grid.rows * 2 + 1)[1::2].astype(int)
    centros_x = np.linspace(x1, x2, grid.cols * 2 + 1)[1::2].astype(int)
    
    cell_w = (x2 - x1) / grid.cols
    cell_h = (y2 - y1) / grid.rows
    raio = int(min(cell_w, cell_h) * 0.22)
    area_roi = (raio * 2) ** 2
    
    res_bloco = {}
    
    # --- FREQUÊNCIA ---
    if grid.labels == ["D", "U"]:
        freq_res = ["0", "0"]
        for c_idx, cx in enumerate(centros_x):
            votos_coluna = []
            for r_idx, cy in enumerate(centros_y):
                roi = img_thresh[cy-raio:cy+raio, cx-raio:cx+raio]
                tinta = cv2.countNonZero(roi)
                votos_coluna.append(tinta)
                cv2.circle(img_debug, (cx, cy), 3, (0, 255, 255), -1)
            
            idx_max = np.argmax(votos_coluna)
            max_tinta = max(votos_coluna)
            
            # Limiar super baixo (20%) para frequência
            if max_tinta > (area_roi * 0.20):
                freq_res[c_idx] = str(idx_max)
                cy_hit = centros_y[idx_max]
                cv2.circle(img_debug, (cx, cy_hit), int(raio), (255, 0, 0), -1)
        return "".join(freq_res), {}

    # --- QUESTÕES ---
    for r_idx, cy in enumerate(centros_y):
        tintas = []
        for cx in centros_x:
            roi = img_thresh[cy-raio:cy+raio, cx-raio:cx+raio]
            tintas.append(cv2.countNonZero(roi))
            
        max_tinta = max(tintas)
        idx_max = np.argmax(tintas)
        avg_tinta = sum(tintas) / 4
        
        # Lógica de Leitura:
        # 1. Tinta > 20% (aceita marcações fracas)
        # 2. Destaque > 25% sobre a média (diferencia da sujeira)
        marcou = False
        if max_tinta > (area_roi * 0.20) and max_tinta > (avg_tinta * 1.25):
            marcou = True
            
        if grid.questao_inicial > 0:
            letra = grid.labels[idx_max] if marcou else "."
            res_bloco[grid.questao_inicial + r_idx] = letra
            
            if marcou:
                cx_win = centros_x[idx_max]
                cv2.circle(img_debug, (cx_win, cy), int(raio), (0, 255, 0), 2)
            else:
                # Debug onde testou (cinza)
                for cx in centros_x:
                    cv2.circle(img_debug, (cx, cy), 2, (150, 150, 150), -1)

    return None, res_bloco

def processar_gabarito(img, conf: ConfiguracaoProva, gabarito=None, offset_x=0, offset_y=0):
    vis, thresh, w, h = alinhar_imagem(img, conf)
    final = {"respostas": {}, "frequencia": "00"}
    
    for g in conf.grids:
        f_val, r_dict = ler_grid(thresh, g, w, h, vis)
        if g.labels == ["D", "U"]: final["frequencia"] = f_val
        else: final["respostas"].update(r_dict)
            
    return final, vis, None
