import cv2
import numpy as np
from layout_samar import ConfiguracaoProva

def order_points(pts):
    """Ordena 4 pontos: Top-Esq, Top-Dir, Inf-Dir, Inf-Esq"""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)] # TL
    rect[2] = pts[np.argmax(s)] # BR
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)] # TR
    rect[3] = pts[np.argmax(diff)] # BL
    return rect

def encontrar_ancoras_globais(thresh_img):
    """
    Estratégia: Encontra TODOS os contornos quadrados e pega os 4 que
    formam o retângulo de maior área (os cantos da folha).
    """
    cnts, _ = cv2.findContours(thresh_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    candidatos = []
    h_img, w_img = thresh_img.shape
    area_total = h_img * w_img
    
    for c in cnts:
        area = cv2.contourArea(c)
        # Filtro de Tamanho: Ignora ruídos pequenos e bordas gigantes
        if area < 100 or area > (area_total * 0.05):
            continue
            
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.04 * peri, True)
        
        # Se tem 4 lados (quadrado) OU é um blob sólido compacto
        if len(approx) == 4:
            (x, y, w, h) = cv2.boundingRect(approx)
            aspect_ratio = w / float(h)
            # Verifica se é quadrado (aceita leve distorção)
            if 0.6 <= aspect_ratio <= 1.4:
                M = cv2.moments(c)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    candidatos.append([cx, cy])

    # Se não achou pelo menos 4 quadrados, impossível alinhar
    if len(candidatos) < 4:
        return None

    # Algoritmo de Seleção dos Extremos:
    # Converte para array numpy
    pts = np.array(candidatos, dtype="float32")
    
    # Para achar os cantos da folha, buscamos os extremos geométricos:
    # TL: menor soma (x+y)
    # BR: maior soma (x+y)
    # TR: maior diferença (x-y) ou menor (y-x)
    # BL: maior diferença (y-x)
    
    # Porém, se houver muitos quadrados (ex: checkbox no texto), 
    # precisamos garantir que pegamos os mais "externos".
    
    # Ordena todos os candidatos e pega os 4 que melhor se encaixam nos cantos
    # Simplificação robusta:
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1)
    
    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]
    tr = pts[np.argmin(d)]
    bl = pts[np.argmax(d)]
    
    return np.array([tl, tr, br, bl], dtype="float32")

def alinhar_imagem(img, conf: ConfiguracaoProva):
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
    
    # Pré-processamento
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    
    rect = encontrar_ancoras_globais(thresh)
    
    if rect is not None:
        scale = 2.0
        w_final = int(conf.PAGE_W * scale)
        h_final = int(conf.PAGE_H * scale)
        m = conf.MARGIN * scale
        s_half = (conf.ANCORA_SIZE / 2.0) * scale
        
        # Mapeia para os CENTROS das âncoras ideais
        dst = np.array([
            [m + s_half, m + s_half],                         # TL
            [w_final - (m + s_half), m + s_half],             # TR
            [w_final - (m + s_half), h_final - (m + s_half)], # BR
            [m + s_half, h_final - (m + s_half)]              # BL
        ], dtype="float32")
        
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(img, M, (w_final, h_final))
        return warped, scale, thresh
        
    # Fallback
    return cv2.resize(img, (int(conf.PAGE_W*2), int(conf.PAGE_H*2))), 2.0, thresh

def processar_gabarito(img, conf: ConfiguracaoProva, gabarito=None, offset_x=0, offset_y=0):
    warped, scale, _ = alinhar_imagem(img, conf)
    
    # Thresholding para leitura
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY_INV, 51, 10)
    
    res = {"respostas": {}, "frequencia": ""}
    img_vis = warped.copy()
    
    # Função interna segura (captura scale e conf, recebe offsets)
    def get_coords(x_pdf, y_pdf, off_x, off_y):
        px = int(x_pdf * scale) + off_x
        py = int((conf.PAGE_H - y_pdf) * scale) + off_y
        return px, py
    
    start_y = conf.GRID_START_Y
    
    # 1. FREQUÊNCIA
    if conf.tem_frequencia:
        val_freq = ""
        center_x = conf.FREQ_X + 27
        offset_col = 12
        
        for col_idx in range(2): 
            votos = []
            col_cx = center_x - offset_col if col_idx == 0 else center_x + offset_col
            
            for i in range(10):
                y_pos = start_y - 25 - (i * 18)
                cx, cy = get_coords(col_cx, y_pos + 3, offset_x, offset_y)
                
                roi = thresh[cy-10:cy+10, cx-10:cx+10]
                votos.append(cv2.countNonZero(roi))
                cv2.circle(img_vis, (cx, cy), 10, (200, 200, 200), 1)
            
            if max(votos) > (60 * scale):
                idx = np.argmax(votos)
                val_freq += str(idx)
                y_hit = start_y - 25 - (idx * 18)
                cx, cy = get_coords(col_cx, y_hit + 3, offset_x, offset_y)
                cv2.circle(img_vis, (cx, cy), 12, (255, 0, 0), -1)
            else:
                val_freq += "0"
        res["frequencia"] = val_freq
        
    # 2. QUESTÕES
    current_x = conf.GRID_X_START
    for bloco in conf.blocos:
        for i in range(bloco.quantidade):
            q_num = bloco.questao_inicial + i
            y_pos = start_y - 25 - (i * 20)
            
            densidade = []
            coords = []
            
            for j in range(4): # A, B, C, D
                bx = current_x + 20 + (j * 20)
                cx, cy = get_coords(bx, y_pos + 3, offset_x, offset_y)
                coords.append((cx, cy))
                
                roi = thresh[cy-10:cy+10, cx-10:cx+10]
                densidade.append(cv2.countNonZero(roi))
            
            # Lógica Winner Takes All (Relativo)
            max_val = max(densidade)
            avg_val = sum(densidade) / 4
            idx_max = np.argmax(densidade)
            
            # Regra: Deve ser muito maior que a média (diferenciar letra impressa de marcação)
            if max_val > 80 and max_val > (avg_val * 1.3):
                marcou = True
                letra = ["A", "B", "C", "D"][idx_max]
                res["respostas"][q_num] = letra
            else:
                marcou = False
                res["respostas"][q_num] = "."
                idx_max = 0
            
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
        
    return res, img_vis, None # Retorna None no debug por enquanto
