import cv2
import numpy as np
from layout_samar import ConfiguracaoProva

def order_points(pts):
    """Ordena coordenadas: Top-Esq, Top-Dir, Inf-Dir, Inf-Esq"""
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)] # TL
    rect[2] = pts[np.argmax(s)] # BR
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)] # TR
    rect[3] = pts[np.argmax(diff)] # BL
    return rect

def encontrar_ancoras_globais(img_binaria, min_area=100):
    """
    Busca todas as formas quadradas na imagem inteira e retorna
    os 4 cantos mais prováveis que formam a folha.
    """
    cnts, _ = cv2.findContours(img_binaria, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidatos = []
    
    h_img, w_img = img_binaria.shape
    area_total = h_img * w_img
    
    for c in cnts:
        area = cv2.contourArea(c)
        # Filtro 1: Tamanho (Nem sujeira minúscula, nem a borda da folha inteira)
        if (area_total * 0.0001) < area < (area_total * 0.05):
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.04 * peri, True)
            
            # Filtro 2: Forma (4 lados ou "blob" sólido quadrado)
            if len(approx) == 4 or (area / (cv2.boundingRect(c)[2] * cv2.boundingRect(c)[3]) > 0.8):
                # Calcula centro
                M = cv2.moments(c)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    candidatos.append([cx, cy])

    # Se achou menos de 4, falhou.
    if len(candidatos) < 4:
        return None

    # Se achou 4 ou mais, precisamos descobrir quais são os CANTOS EXTREMOS.
    pts = np.array(candidatos, dtype="float32")
    
    # Estratégia: A soma de X+Y é mínima no TL e máxima no BR.
    # A diferença Y-X ou X-Y define os outros dois.
    s = pts.sum(axis=1)
    d = np.diff(pts, axis=1)
    
    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]
    tr = pts[np.argmin(d)]
    bl = pts[np.argmax(d)]
    
    return np.array([tl, tr, br, bl], dtype="float32")

def alinhar_imagem(img, conf: ConfiguracaoProva):
    # 1. Pré-processamento Robusto
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
    
    # Blur para reduzir ruído de impressão
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    # Threshold de Otsu (automático)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    
    # 2. Busca Global de Âncoras
    rect = encontrar_ancoras_globais(thresh)
    
    if rect is not None:
        # Se achou os 4 cantos, prepara para desentortar (Warp)
        # Usamos escala 2x para garantir precisão na leitura das bolinhas
        scale = 2.0
        w_final = int(conf.PAGE_W * scale)
        h_final = int(conf.PAGE_H * scale)
        
        # Mapeamos para a posição EXATA definida no Layout
        m = conf.MARGIN
        s_half = conf.ANCORA_SIZE / 2.0
        
        # Coordenadas de destino (Centros das âncoras)
        dst = np.array([
            [(m + s_half)*scale, (m + s_half)*scale],           # TL
            [(conf.PAGE_W - m - s_half)*scale, (m + s_half)*scale], # TR
            [(conf.PAGE_W - m - s_half)*scale, (conf.PAGE_H - m - s_half)*scale], # BR
            [(m + s_half)*scale, (conf.PAGE_H - m - s_half)*scale]  # BL
        ], dtype="float32")
        
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(img, M, (w_final, h_final))
        return warped, scale, thresh
    
    # Fallback: Se não achou âncoras, retorna redimensionado (vai falhar na leitura, mas não quebra o app)
    return cv2.resize(img, (int(conf.PAGE_W*2), int(conf.PAGE_H*2))), 2.0, thresh

def processar_gabarito(img, conf: ConfiguracaoProva, gabarito=None, offset_x=0, offset_y=0):
    warped, scale, _ = alinhar_imagem(img, conf)
    
    # Recalcula threshold na imagem alinhada para leitura precisa das bolinhas
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY_INV, 51, 10)
    
    res = {"respostas": {}, "frequencia": ""}
    img_vis = warped.copy()
    
    # Função de mapeamento PDF -> Pixel (com offset de ajuste manual se precisar)
    def get_px(x_pdf, y_pdf):
        px = int(x * scale) + offset_x
        py = int((conf.PAGE_H - y_pdf) * scale) + offset_y
        return px, py
    
    start_y = conf.GRID_START_Y
    
    # 1. FREQUÊNCIA
    if conf.tem_frequencia:
        val_freq = ""
        # Centro da coluna de frequência
        center_x = conf.FREQ_X + 27 
        offset_col = 12
        
        for col_idx in range(2): 
            votos = []
            # Coluna D (Esq) ou U (Dir)
            col_cx = center_x - offset_col if col_idx == 0 else center_x + offset_col
            
            for i in range(10):
                y_pos = start_y - 25 - (i * 18)
                cx, cy = get_px(col_cx, y_pos + 3) # +3 ajuste ótico
                
                # ROI (Região de Leitura)
                roi = thresh[cy-10:cy+10, cx-10:cx+10]
                votos.append(cv2.countNonZero(roi))
                
                # Debug Visual (Cinza)
                cv2.circle(img_vis, (cx, cy), 10, (200, 200, 200), 1)
            
            # Decisão: Quem tem mais tinta?
            max_votos = max(votos)
            if max_votos > (50 * scale): # Limite mínimo de tinta
                idx = np.argmax(votos)
                val_freq += str(idx)
                
                # Marcação Visual (Azul)
                y_hit = start_y - 25 - (idx * 18)
                cx, cy = get_px(col_cx, y_hit + 3)
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
                cx, cy = get_px(bx, y_pos + 3)
                coords.append((cx, cy))
                
                roi = thresh[cy-10:cy+10, cx-10:cx+10]
                densidade.append(cv2.countNonZero(roi))
            
            # Lógica "Vencedor Leva Tudo" (Ignora letras impressas)
            max_val = max(densidade)
            avg_val = sum(densidade) / 4
            idx_max = np.argmax(densidade)
            
            # Se o máximo for significativamente maior que a média das outras 3
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
                        cv2.circle(img_vis, (cx, cy), 13, (0, 255, 0), -1) # Verde Sólido (Certo)
                    else:
                        cv2.circle(img_vis, (cx, cy), 13, (0, 0, 255), -1) # Vermelho (Errado)
                        cv2.circle(img_vis, (cx_c, cy_c), 13, (0, 255, 0), 3) # Verde Vazado (Correção)
                else:
                    cv2.circle(img_vis, (cx_c, cy_c), 10, (0, 255, 255), 2) # Amarelo (Em branco)
            elif marcou:
                cv2.circle(img_vis, (cx, cy), 10, (100, 100, 100), -1) # Cinza (Leitura sem gabarito)

        current_x += conf.GRID_COL_W
        
    return res, img_vis
