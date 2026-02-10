import cv2
import numpy as np
from layout_samar import ConfiguracaoProva

def order_points(pts):
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1); rect[0] = pts[np.argmin(s)]; rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1); rect[1] = pts[np.argmin(diff)]; rect[3] = pts[np.argmax(diff)]
    return rect

def encontrar_ancoras_quadradas(thresh_img):
    cnts, _ = cv2.findContours(thresh_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidatos = []
    h, w = thresh_img.shape
    for c in cnts:
        area = cv2.contourArea(c)
        if area < 100 or area > (h*w * 0.05): continue
        approx = cv2.approxPolyDP(c, 0.04 * cv2.arcLength(c, True), True)
        if len(approx) == 4:
            x, y, bw, bh = cv2.boundingRect(approx)
            ar = bw / float(bh)
            if 0.7 <= ar <= 1.3:
                M = cv2.moments(c)
                if M["m00"] != 0:
                    candidatos.append([int(M["m10"]/M["m00"]), int(M["m01"]/M["m00"])])
    
    if len(candidatos) < 4: return None
    pts = np.array(candidatos, dtype="float32")
    s = pts.sum(axis=1); d = np.diff(pts, axis=1)
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]], dtype="float32")

def alinhar_imagem(img, conf):
    if len(img.shape) == 3: gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else: gray = img
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    rect = encontrar_ancoras_quadradas(thresh)
    
    if rect is not None:
        scale = 2.0
        w_t, h_t = int(conf.PAGE_W * scale), int(conf.PAGE_H * scale)
        m = conf.MARGIN * scale
        s = (conf.ANCORA_SIZE / 2.0) * scale
        dst = np.array([[m+s, m+s], [w_t-(m+s), m+s], [w_t-(m+s), h_t-(m+s)], [m+s, h_t-(m+s)]], dtype="float32")
        M = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(img, M, (w_t, h_t)), scale, thresh
    return cv2.resize(img, (int(conf.PAGE_W*2), int(conf.PAGE_H*2))), 2.0, thresh

def get_coords_manual(x_pdf, y_pdf, off_x, off_y, scale, page_h):
    return int(x_pdf * scale) + off_x, int((page_h - y_pdf) * scale) + off_y

def detectar_linhas_elasticas(img_thresh, x_center_pdf, y_start_pdf, spacing_pdf, num_rows, scale, page_h, off_y):
    """
    PROJEÇÃO VERTICAL: Escaneia uma faixa vertical na imagem para achar 
    onde as linhas REALMENTE estão, ignorando espaçamento fixo.
    """
    # 1. Define uma faixa vertical (ROI) onde esperamos as bolinhas
    x_px = int(x_center_pdf * scale)
    width_px = int(40 * scale) # Largura de busca
    
    # Coordenadas estimadas de topo e fundo
    y_top_pdf = y_start_pdf + 10 # Um pouco acima da primeira linha
    y_bot_pdf = y_start_pdf - (num_rows * spacing_pdf) - 10
    
    y_start_px = int((page_h - y_top_pdf) * scale) + off_y
    y_end_px = int((page_h - y_bot_pdf) * scale) + off_y
    
    # Proteção de bordas
    y_start_px = max(0, y_start_px)
    y_end_px = min(img_thresh.shape[0], y_end_px)
    x_left = max(0, x_px - width_px//2)
    x_right = min(img_thresh.shape[1], x_px + width_px//2)
    
    # 2. Recorta a faixa
    roi = img_thresh[y_start_px:y_end_px, x_left:x_right]
    
    # 3. Projeção Horizontal (Soma linhas)
    # Reduz para 1 dimensão (vetor vertical de densidade)
    projecao = cv2.reduce(roi, 1, cv2.REDUCE_SUM, dtype=cv2.CV_32F).flatten()
    
    # 4. Encontrar Picos (Onde tem bolinhas/texto)
    # Suaviza para evitar ruído
    projecao = cv2.GaussianBlur(projecao, (1, 5), 0)
    
    # Normaliza
    if projecao.max() > 0:
        projecao = projecao / projecao.max()
    
    # Busca regiões onde a densidade é alta (> 0.2)
    picos_y = []
    dentro_pico = False
    inicio_pico = 0
    
    for y, val in enumerate(projecao):
        if val > 0.2 and not dentro_pico:
            dentro_pico = True
            inicio_pico = y
        elif val <= 0.2 and dentro_pico:
            dentro_pico = False
            centro_pico = (inicio_pico + y) // 2
            picos_y.append(y_start_px + centro_pico)
            
    # 5. Filtragem e Validação
    # Esperamos 'num_rows' linhas.
    # Se achamos o número certo (ou próximo), usamos. Se não, fallback para fixo.
    
    ys_finais = []
    
    # Se achou picos suficientes, tenta casar com o esperado
    if len(picos_y) >= num_rows:
        # Pega os 'num_rows' picos mais prováveis (baseado em espaçamento regular)
        # Simplificação: Pega os primeiros num_rows se a contagem bater
        # ou tenta distribuir.
        # Aqui vamos confiar no fallback se a contagem for muito ruim.
        
        # Se tiver muitos picos (sujeira), pegamos os maiores intervalos? 
        # Vamos assumir que o recorte foi bom.
        
        # Retorna apenas os N primeiros que fazem sentido
        ys_finais = picos_y[:num_rows]
    else:
        # Fallback: Gera fixo
        spacing_px = int(spacing_pdf * scale)
        start_px = int((page_h - y_start_pdf) * scale) + off_y + int(spacing_px) # Ajuste inicial
        ys_finais = [start_px + (i * spacing_px) for i in range(num_rows)]
        
    # Garante que temos a lista completa preenchida com fixo se falhar
    while len(ys_finais) < num_rows:
        last = ys_finais[-1] if ys_finais else int((page_h - y_start_pdf)*scale)
        ys_finais.append(last + int(spacing_pdf * scale))
        
    return ys_finais[:num_rows]

def processar_gabarito(img, conf: ConfiguracaoProva, gabarito=None, offset_x=0, offset_y=0):
    warped, scale, _ = alinhar_imagem(img, conf)
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 51, 10)
    
    res = {"respostas": {}, "frequencia": ""}
    img_vis = warped.copy()
    
    # --- FREQUÊNCIA ELÁSTICA ---
    if conf.tem_frequencia:
        val_freq = ""
        cx_base = conf.FREQ_X + 27
        
        # Detecta as linhas Y dinamicamente olhando para a coluna de Frequência
        # Usamos 10 linhas, espaçamento base V_SPACING
        ys_dinamicos = detectar_linhas_elasticas(thresh, cx_base, conf.GRID_START_Y - 25, conf.V_SPACING, 10, scale, conf.PAGE_H, offset_y)
        
        offset_col = 12
        for col_idx in range(2): 
            votos = []
            col_cx = cx_base - offset_col if col_idx == 0 else cx_base + offset_col
            
            for i, y_px in enumerate(ys_dinamicos):
                # X fixo (ajustado pelo slider), Y dinâmico
                cx = int(col_cx * scale) + offset_x
                cy = y_px
                
                roi = thresh[cy-10:cy+10, cx-10:cx+10]
                votos.append(cv2.countNonZero(roi))
                cv2.circle(img_vis, (cx, cy), 10, (200, 200, 200), 1)
            
            if max(votos) > (50 * scale):
                idx = np.argmax(votos)
                val_freq += str(idx)
                # Pinta a escolhida
                cx_hit = int(col_cx * scale) + offset_x
                cy_hit = ys_dinamicos[idx]
                cv2.circle(img_vis, (cx_hit, cy_hit), 12, (255, 0, 0), -1)
            else:
                val_freq += "0"
        res["frequencia"] = val_freq
        
    # --- QUESTÕES ELÁSTICAS ---
    # Para cada bloco, detectamos as linhas novamente (pois podem estar desalinhadas do bloco 1)
    current_x = conf.GRID_X_START
    for bloco in conf.blocos:
        # Detecta Ys para este bloco específico (olhando para a primeira coluna do bloco)
        # Isso corrige se o bloco 4 estiver mais baixo que o bloco 1
        center_col_1 = current_x + 20
        ys_bloco = detectar_linhas_elasticas(thresh, center_col_1, conf.GRID_START_Y - 25, conf.V_SPACING, bloco.quantidade, scale, conf.PAGE_H, offset_y)
        
        for i in range(bloco.quantidade):
            q_num = bloco.questao_inicial + i
            # Pega o Y calculado elasticamente para esta linha
            if i < len(ys_bloco):
                cy_row = ys_bloco[i]
            else:
                # Fallback seguro
                cy_row = ys_bloco[-1] + int(conf.V_SPACING * scale)
            
            densidade = []
            coords = []
            
            for j in range(4): # A, B, C, D
                bx = current_x + 20 + (j * 20)
                cx = int(bx * scale) + offset_x
                cy = cy_row
                
                coords.append((cx, cy))
                roi = thresh[cy-10:cy+10, cx-10:cx+10]
                densidade.append(cv2.countNonZero(roi))
            
            max_val = max(densidade)
            avg_val = sum(densidade) / 4
            idx_max = np.argmax(densidade)
            
            if max_val > 80 and max_val > (avg_val * 1.35):
                letra = ["A", "B", "C", "D"][idx_max]
                res["respostas"][q_num] = letra
                marcou = True
            else:
                res["respostas"][q_num] = "."
                marcou = False
                idx_max = 0
            
            # Visualização
            cx_d, cy_d = coords[idx_max]
            if gabarito and q_num in gabarito:
                correta = gabarito[q_num]
                idx_c = ["A","B","C","D"].index(correta)
                cx_c, cy_c = coords[idx_c]
                if marcou:
                    if letra == correta: cv2.circle(img_vis, (cx_d, cy_d), 13, (0, 255, 0), -1)
                    else:
                        cv2.circle(img_vis, (cx_d, cy_d), 13, (0, 0, 255), -1)
                        cv2.circle(img_vis, (cx_c, cy_c), 13, (0, 255, 0), 3)
                else: cv2.circle(img_vis, (cx_c, cy_c), 10, (0, 255, 255), 2)
            elif marcou: cv2.circle(img_vis, (cx_d, cy_d), 10, (100, 100, 100), -1)

        current_x += conf.GRID_COL_W
        
    return res, img_vis, None
