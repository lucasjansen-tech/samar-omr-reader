import cv2
import numpy as np
from layout_samar import ConfiguracaoProva

def order_points(pts):
    """Ordena coordenadas: TL, TR, BR, BL"""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)] # TL
    rect[2] = pts[np.argmax(s)] # BR
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)] # TR
    rect[3] = pts[np.argmax(diff)] # BL
    return rect

def encontrar_ancoras_robustas(img_gray):
    """
    Usa MORFOLOGIA MATEMÁTICA para apagar texto e bolinhas,
    deixando apenas as âncoras sólidas visíveis para o detector.
    """
    # 1. Binarização Invertida (Preto vira Branco)
    _, thresh = cv2.threshold(img_gray, 80, 255, cv2.THRESH_BINARY_INV)
    
    # 2. OPERAÇÃO DE EROSÃO E DILATAÇÃO (O SEGREDO)
    # Isso remove linhas finas (texto, bordas de bolinhas) e mantém blocos sólidos.
    kernel_size = 5 # Ajustável
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
    
    # Erode 2x (some com texto) -> Dilata 2x (restaura tamanho da âncora)
    morphed = cv2.erode(thresh, kernel, iterations=2)
    morphed = cv2.dilate(morphed, kernel, iterations=2)
    
    # Agora buscamos contornos na imagem "limpa"
    cnts, _ = cv2.findContours(morphed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidatos = []
    
    h, w = img_gray.shape
    area_total = h * w
    
    for c in cnts:
        area = cv2.contourArea(c)
        # Filtro de área: Âncora tem que ser visível
        if area < 200 or area > (area_total * 0.05):
            continue
            
        x, y, w_box, h_box = cv2.boundingRect(c)
        ar = w_box / float(h_box)
        
        # Filtro de Forma: Tem que ser quadrado (0.8 a 1.2)
        # Isso elimina os cabeçalhos "BLOCO 1" que são retangulares
        if 0.7 <= ar <= 1.3:
            M = cv2.moments(c)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                candidatos.append([cx, cy])

    if len(candidatos) < 4:
        return None, morphed # Retorna imagem processada para debug

    # Seleciona os 4 cantos extremos
    pts = np.array(candidatos, dtype="float32")
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1)
    
    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]
    tr = pts[np.argmin(d)]
    bl = pts[np.argmax(d)]
    
    return np.array([tl, tr, br, bl], dtype="float32"), morphed

def alinhar_imagem(img, conf: ConfiguracaoProva):
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
        
    rect, debug_img = encontrar_ancoras_robustas(gray)
    
    if rect is not None:
        scale = 2.0
        w_final = int(conf.PAGE_W * scale)
        h_final = int(conf.PAGE_H * scale)
        m = conf.MARGIN * scale
        s_half = (conf.ANCORA_SIZE / 2.0) * scale
        
        dst = np.array([
            [m + s_half, m + s_half],
            [w_final - (m + s_half), m + s_half],
            [w_final - (m + s_half), h_final - (m + s_half)],
            [m + s_half, h_final - (m + s_half)]
        ], dtype="float32")
        
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(img, M, (w_final, h_final))
        return warped, scale, debug_img
        
    return cv2.resize(img, (int(conf.PAGE_W*2), int(conf.PAGE_H*2))), 2.0, debug_img

def get_coords_magnetic(x_pdf, y_pdf, off_x, off_y, scale, page_h, img_thresh):
    """
    LEITURA MAGNÉTICA:
    Calcula a posição teórica e procura o centro de massa de tinta mais próximo.
    Se o aluno marcou um pouco fora, isso corrige automaticamente.
    """
    # Posição Teórica
    px = int(x_pdf * scale) + off_x
    py = int((page_h - y_pdf) * scale) + off_y
    
    # Define uma janela de busca (Search Window) de 20x20 pixels ao redor
    search_radius = 14
    y_min = max(0, py - search_radius)
    y_max = min(img_thresh.shape[0], py + search_radius)
    x_min = max(0, px - search_radius)
    x_max = min(img_thresh.shape[1], px + search_radius)
    
    roi = img_thresh[y_min:y_max, x_min:x_max]
    
    # Se houver tinta significativa na região (uma bolinha marcada)
    if cv2.countNonZero(roi) > 20:
        M = cv2.moments(roi)
        if M["m00"] != 0:
            # Novo centro relativo ao ROI
            dx = int(M["m10"] / M["m00"])
            dy = int(M["m01"] / M["m00"])
            # Atualiza posição global (Snap)
            return x_min + dx, y_min + dy
            
    # Se não achou nada (em branco), retorna o teórico mesmo
    return px, py

def processar_gabarito(img, conf: ConfiguracaoProva, gabarito=None, offset_x=0, offset_y=0):
    warped, scale, debug_img = alinhar_imagem(img, conf)
    
    # Threshold limpo para leitura
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY_INV, 51, 10)
    
    res = {"respostas": {}, "frequencia": ""}
    img_vis = warped.copy()
    
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
                # Usa Leitura Magnética
                cx, cy = get_coords_magnetic(col_cx, y_pos + 3, offset_x, offset_y, scale, conf.PAGE_H, thresh)
                
                roi = thresh[cy-9:cy+9, cx-9:cx+9]
                votos.append(cv2.countNonZero(roi))
                cv2.circle(img_vis, (cx, cy), 9, (200, 200, 200), 1)
            
            if max(votos) > (50 * scale):
                idx = np.argmax(votos)
                val_freq += str(idx)
                
                # Visualização na coordenada magnética achada
                y_hit = start_y - 25 - (idx * 18)
                cx, cy = get_coords_magnetic(col_cx, y_hit + 3, offset_x, offset_y, scale, conf.PAGE_H, thresh)
                cv2.circle(img_vis, (cx, cy), 11, (255, 0, 0), -1)
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
                # Usa Leitura Magnética
                cx, cy = get_coords_magnetic(bx, y_pos + 3, offset_x, offset_y, scale, conf.PAGE_H, thresh)
                coords.append((cx, cy))
                
                roi = thresh[cy-9:cy+9, cx-9:cx+9]
                densidade.append(cv2.countNonZero(roi))
            
            # Winner Takes All
            max_val = max(densidade)
            avg_val = sum(densidade) / 4
            idx_max = np.argmax(densidade)
            
            if max_val > 80 and max_val > (avg_val * 1.3):
                marcou = True
                letra = ["A", "B", "C", "D"][idx_max]
                res["respostas"][q_num] = letra
            else:
                marcou = False
                res["respostas"][q_num] = "."
                idx_max = 0
            
            cx, cy = coords[idx_max]
            if gabarito and q_num in gabarito:
                correta = gabarito[q_num]
                idx_c = ["A","B","C","D"].index(correta)
                cx_c, cy_c = coords[idx_c]
                
                if marcou:
                    if letra == correta:
                        cv2.circle(img_vis, (cx, cy), 12, (0, 255, 0), -1)
                    else:
                        cv2.circle(img_vis, (cx, cy), 12, (0, 0, 255), -1)
                        cv2.circle(img_vis, (cx_c, cy_c), 12, (0, 255, 0), 3)
                else:
                    cv2.circle(img_vis, (cx_c, cy_c), 10, (0, 255, 255), 2)
            elif marcou:
                cv2.circle(img_vis, (cx, cy), 10, (100, 100, 100), -1)

        current_x += conf.GRID_COL_W
        
    return res, img_vis, debug_img
