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
    
    # Pré-processamento
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh_ancoras = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                           cv2.THRESH_BINARY_INV, 51, 15)
    
    rect = encontrar_ancoras_globais(thresh_ancoras)
    W_FINAL, H_FINAL = conf.REF_W, conf.REF_H
    
    if rect is not None:
        m = int(W_FINAL * conf.MARGIN_PCT)
        dst = np.array([[m, m], [W_FINAL-m, m], [W_FINAL-m, H_FINAL-m], [m, H_FINAL-m]], dtype="float32")
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(gray, M, (W_FINAL, H_FINAL))
    else:
        warped = cv2.resize(gray, (W_FINAL, H_FINAL))

    # --- A GRANDE MUDANÇA: OTSU BINARIZATION ---
    # Isso cria uma imagem preto e branco pura, ideal para contar pixels de tinta
    blur_warp = cv2.GaussianBlur(warped, (3, 3), 0)
    _, binaria = cv2.threshold(blur_warp, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    
    # Retorna colorido para debug visual e binário para o cálculo
    return cv2.cvtColor(warped, cv2.COLOR_GRAY2BGR), binaria, W_FINAL, H_FINAL

def ler_grid(img_binaria, grid: GridConfig, w_img, h_img, img_debug):
    x1 = int(grid.x_start * w_img)
    x2 = int(grid.x_end * w_img)
    y1 = int(grid.y_start * h_img)
    y2 = int(grid.y_end * h_img)
    
    # Caixa Verde (Debug)
    cv2.rectangle(img_debug, (x1, y1), (x2, y2), (0, 255, 0), 2)
    
    # Centros Matemáticos
    centros_y = np.linspace(y1, y2, grid.rows * 2 + 1)[1::2].astype(int)
    centros_x = np.linspace(x1, x2, grid.cols * 2 + 1)[1::2].astype(int)
    
    # Raio pequeno (18%) para focar no miolo e ignorar bordas/grids
    cell_w = (x2 - x1) / grid.cols
    cell_h = (y2 - y1) / grid.rows
    raio = int(min(cell_w, cell_h) * 0.18) 
    area_roi = (raio * 2) ** 2
    
    res_bloco = {}
    
    # --- FREQUÊNCIA ---
    if grid.labels == ["D", "U"]:
        freq_res = ["0", "0"]
        centros_x.sort() # Garante Esquerda -> Direita
        
        for c_idx, cx in enumerate(centros_x):
            votos = []
            for r_idx, cy in enumerate(centros_y):
                roi = img_binaria[cy-raio:cy+raio, cx-raio:cx+raio]
                votos.append(cv2.countNonZero(roi))
                cv2.circle(img_debug, (cx, cy), 2, (0, 255, 255), -1)
            
            idx_max = np.argmax(votos)
            val_max = max(votos)
            
            # Com OTSU, a tinta é sólida. 30% é um bom corte.
            if val_max > (area_roi * 0.30):
                freq_res[c_idx] = str(idx_max)
                cv2.circle(img_debug, (cx, centros_y[idx_max]), int(raio), (255, 0, 0), -1)
                
        return "".join(freq_res), {}

    # --- QUESTÕES ---
    for r_idx, cy in enumerate(centros_y):
        tintas = []
        for cx in centros_x:
            roi = img_binaria[cy-raio:cy+raio, cx-raio:cx+raio]
            tintas.append(cv2.countNonZero(roi))
            
        max_tinta = max(tintas)
        idx_max = np.argmax(tintas)
        avg_tinta = sum(tintas) / 4
        
        marcou = False
        # Lógica OTSU:
        # 1. Tinta > 30% da área
        # 2. Destaque > 50% sobre a média (muito mais preto que o resto)
        if max_tinta > (area_roi * 0.30) and max_tinta > (avg_tinta * 1.5):
            marcou = True
            
        if grid.questao_inicial > 0:
            letra = grid.labels[idx_max] if marcou else "."
            res_bloco[grid.questao_inicial + r_idx] = letra
            
            if marcou:
                cv2.circle(img_debug, (centros_x[idx_max], cy), int(raio), (0, 255, 0), 2)
            else:
                for cx in centros_x: cv2.circle(img_debug, (cx, cy), 2, (150, 150, 150), -1)

    return None, res_bloco

def processar_gabarito(img, conf: ConfiguracaoProva, gabarito=None, offset_x=0, offset_y=0):
    vis, binaria, w, h = alinhar_imagem(img, conf)
    final = {"respostas": {}, "frequencia": "00"}
    
    for g in conf.grids:
        f_val, r_dict = ler_grid(binaria, g, w, h, vis)
        if g.labels == ["D", "U"]: final["frequencia"] = f_val
        else: final["respostas"].update(r_dict)
            
    return final, vis, None
