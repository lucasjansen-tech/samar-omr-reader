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
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY_INV, 51, 15)
    
    rect = encontrar_ancoras_globais(thresh)
    W_FINAL, H_FINAL = conf.REF_W, conf.REF_H
    
    if rect is not None:
        m = int(W_FINAL * conf.MARGIN_PCT)
        dst = np.array([[m, m], [W_FINAL-m, m], [W_FINAL-m, H_FINAL-m], [m, H_FINAL-m]], dtype="float32")
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(img, M, (W_FINAL, H_FINAL))
        
        # Threshold limpo para leitura
        warped_gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
        # Block size menor (21) para pegar detalhes finos
        warped_thresh = cv2.adaptiveThreshold(warped_gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                              cv2.THRESH_BINARY_INV, 21, 10)
        return warped, warped_thresh, W_FINAL, H_FINAL
    
    r = cv2.resize(img, (W_FINAL, H_FINAL))
    rt = cv2.adaptiveThreshold(cv2.cvtColor(r, cv2.COLOR_BGR2GRAY), 255, 
                               cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 21, 10)
    return r, rt, W_FINAL, H_FINAL

def ler_grid(img_thresh, grid: GridConfig, w_img, h_img, img_debug):
    x1 = int(grid.x_start * w_img)
    x2 = int(grid.x_end * w_img)
    y1 = int(grid.y_start * h_img)
    y2 = int(grid.y_end * h_img)
    
    # DEBUG Verde
    cv2.rectangle(img_debug, (x1, y1), (x2, y2), (0, 255, 0), 2)
    
    # Grid Matemático
    centros_y = np.linspace(y1, y2, grid.rows * 2 + 1)[1::2].astype(int)
    centros_x = np.linspace(x1, x2, grid.cols * 2 + 1)[1::2].astype(int)
    
    cell_w = (x2 - x1) / grid.cols
    cell_h = (y2 - y1) / grid.rows
    # Raio menor (18%) para evitar bordas
    raio = int(min(cell_w, cell_h) * 0.18) 
    
    res_bloco = {}
    
    # --- FREQUÊNCIA (Coluna a Coluna) ---
    if grid.labels == ["D", "U"]:
        freq_res = ["0", "0"] # D, U
        
        # Garante ordem correta das colunas (0=D, 1=U)
        for c_idx in range(len(centros_x)):
            cx = centros_x[c_idx]
            votos_coluna = []
            
            for r_idx, cy in enumerate(centros_y):
                roi = img_thresh[cy-raio:cy+raio, cx-raio:cx+raio]
                tinta = cv2.countNonZero(roi)
                votos_coluna.append(tinta)
                cv2.circle(img_debug, (cx, cy), 2, (0, 255, 255), -1)
            
            # Lógica Relativa: Qual linha ganhou na coluna?
            max_tinta = max(votos_coluna)
            idx_vencedor = np.argmax(votos_coluna)
            avg_outros = (sum(votos_coluna) - max_tinta) / (len(votos_coluna) - 1) if len(votos_coluna) > 1 else 0
            
            # Se o vencedor tem o dobro de tinta da média (destaque claro)
            if max_tinta > 20 and max_tinta > (avg_outros * 1.5):
                freq_res[c_idx] = str(idx_vencedor)
                cy_hit = centros_y[idx_vencedor]
                cv2.circle(img_debug, (cx, cy_hit), int(raio*1.2), (255, 0, 0), -1)
            else:
                # Ninguém marcou claro, assume 0 ou erro
                pass
                
        return "".join(freq_res), {}

    # --- QUESTÕES (Linha a Linha) ---
    for r_idx, cy in enumerate(centros_y):
        tintas = []
        for cx in centros_x:
            roi = img_thresh[cy-raio:cy+raio, cx-raio:cx+raio]
            tinta = cv2.countNonZero(roi)
            tintas.append(tinta)
            
        # Análise Relativa Horizontal
        max_tinta = max(tintas)
        idx_max = np.argmax(tintas)
        
        # Calcula média dos NÃO marcados
        soma_outros = sum(tintas) - max_tinta
        media_outros = soma_outros / 3
        
        marcou = False
        letra = "."
        
        # Lógica de Ouro: O marcado deve ser muito mais escuro que os outros
        # E deve ter um mínimo de tinta absoluta (ruído zero)
        if max_tinta > 25 and max_tinta > (media_outros * 2.0):
            marcou = True
            letra = grid.labels[idx_max]
            
        if grid.questao_inicial > 0:
            res_bloco[grid.questao_inicial + r_idx] = letra
            
            if marcou:
                cx_win = centros_x[idx_max]
                cv2.circle(img_debug, (cx_win, cy), int(raio), (0, 255, 0), 2)
            else:
                # Debug (Cinza = leu mas não aceitou)
                for i, cx in enumerate(centros_x):
                    cv2.circle(img_debug, (cx, cy), 2, (100, 100, 100), -1)

    return None, res_bloco

def processar_gabarito(img, conf: ConfiguracaoProva, gabarito=None, offset_x=0, offset_y=0):
    warped, thresh, w, h = alinhar_imagem(img, conf)
    vis = warped.copy()
    final = {"respostas": {}, "frequencia": "00"}
    
    for g in conf.grids:
        f_val, r_dict = ler_grid(thresh, g, w, h, vis)
        if g.labels == ["D", "U"]: final["frequencia"] = f_val
        else: final["respostas"].update(r_dict)
            
    return final, vis, None
