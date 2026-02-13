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
    
    # Blur para tirar ruído do papel
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # 1. Achar Âncoras (Threshold simples funciona bem para quadrados pretos)
    _, thresh_ancoras = cv2.threshold(blurred, 80, 255, cv2.THRESH_BINARY_INV)
    rect = encontrar_ancoras_globais(thresh_ancoras)
    
    W_FINAL, H_FINAL = conf.REF_W, conf.REF_H
    
    if rect is not None:
        m = int(W_FINAL * conf.MARGIN_PCT)
        dst = np.array([[m, m], [W_FINAL-m, m], [W_FINAL-m, H_FINAL-m], [m, H_FINAL-m]], dtype="float32")
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(gray, M, (W_FINAL, H_FINAL))
    else:
        warped = cv2.resize(gray, (W_FINAL, H_FINAL))

    # 2. PREPARAÇÃO PARA LEITURA (A MUDANÇA CHAVE)
    # OTSU Global: Decide o melhor ponto de corte entre "escuro" e "claro"
    # Isso preenche totalmente as bolinhas marcadas, sem deixar buracos
    _, binaria = cv2.threshold(warped, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    
    # Retorna a imagem colorida para debug e a binária para contagem
    vis_color = cv2.cvtColor(warped, cv2.COLOR_GRAY2BGR)
    return vis_color, binaria, W_FINAL, H_FINAL

def ler_grid(img_binaria, grid: GridConfig, w_img, h_img, img_debug):
    x1 = int(grid.x_start * w_img)
    x2 = int(grid.x_end * w_img)
    y1 = int(grid.y_start * h_img)
    y2 = int(grid.y_end * h_img)
    
    # Debug Verde
    cv2.rectangle(img_debug, (x1, y1), (x2, y2), (0, 255, 0), 2)
    
    # Coordenadas Matemáticas
    centros_y = np.linspace(y1, y2, grid.rows * 2 + 1)[1::2].astype(int)
    centros_x = np.linspace(x1, x2, grid.cols * 2 + 1)[1::2].astype(int)
    
    cell_w = (x2 - x1) / grid.cols
    cell_h = (y2 - y1) / grid.rows
    
    # Raio de leitura: 20% da célula (foco no miolo)
    raio = int(min(cell_w, cell_h) * 0.20)
    area_roi = (raio * 2) ** 2 # Quadrado ao redor do raio
    
    res_bloco = {}
    
    # --- FREQUÊNCIA ---
    if grid.labels == ["D", "U"]:
        freq_res = ["0", "0"]
        # Ordena X para garantir Esquerda(D) -> Direita(U)
        centros_x.sort()
        
        for c_idx, cx in enumerate(centros_x):
            votos_coluna = []
            for r_idx, cy in enumerate(centros_y):
                # Recorte na imagem BINÁRIA (Preto/Branco puro)
                roi = img_binaria[cy-raio:cy+raio, cx-raio:cx+raio]
                tinta = cv2.countNonZero(roi)
                votos_coluna.append(tinta)
                # Debug Amarelo
                cv2.circle(img_debug, (cx, cy), 2, (0, 255, 255), -1)
            
            idx_max = np.argmax(votos_coluna)
            max_tinta = max(votos_coluna)
            
            # Se mais de 40% da área estiver preta, é uma marcação
            if max_tinta > (area_roi * 0.40):
                freq_res[c_idx] = str(idx_max)
                cy_hit = centros_y[idx_max]
                cv2.circle(img_debug, (cx, cy_hit), int(raio), (255, 0, 0), -1)
                
        return "".join(freq_res), {}

    # --- QUESTÕES ---
    for r_idx, cy in enumerate(centros_y):
        tintas = []
        for cx in centros_x:
            roi = img_binaria[cy-raio:cy+raio, cx-raio:cx+raio]
            tinta = cv2.countNonZero(roi)
            tintas.append(tinta)
            
        max_tinta = max(tintas)
        idx_max = np.argmax(tintas)
        
        # Limiar Fixo: Se tiver mais de 40% de tinta, marcou.
        # OTSU garante que tinta é tinta.
        marcou = False
        if max_tinta > (area_roi * 0.40):
            marcou = True
            
        if grid.questao_inicial > 0:
            letra = grid.labels[idx_max] if marcou else "."
            res_bloco[grid.questao_inicial + r_idx] = letra
            
            if marcou:
                cx_win = centros_x[idx_max]
                cv2.circle(img_debug, (cx_win, cy), int(raio), (0, 255, 0), 2)
            else:
                for cx in centros_x:
                    cv2.circle(img_debug, (cx, cy), 2, (100, 100, 100), -1)

    return None, res_bloco

def processar_gabarito(img, conf: ConfiguracaoProva, gabarito=None, offset_x=0, offset_y=0):
    vis, binaria, w, h = alinhar_imagem(img, conf)
    final = {"respostas": {}, "frequencia": "00"}
    
    for g in conf.grids:
        f_val, r_dict = ler_grid(binaria, g, w, h, vis)
        if g.labels == ["D", "U"]: final["frequencia"] = f_val
        else: final["respostas"].update(r_dict)
            
    return final, vis, None
