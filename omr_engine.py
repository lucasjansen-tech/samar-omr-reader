import cv2
import numpy as np
from layout_samar import ConfiguracaoProva

def order_points(pts):
    # Ordena os pontos: Top-Esq, Top-Dir, Inf-Dir, Inf-Esq
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def alinhar_imagem(img, conf: ConfiguracaoProva):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Threshold adaptativo ou fixo dependendo do contraste
    # Usando fixo invertido para pegar o preto
    _, thresh = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)
    
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    ancoras = []
    
    # Detecta as âncoras (quadrados pretos)
    for c in cnts:
        area = cv2.contourArea(c)
        # Filtro de área ajustado para resolução típica (200dpi)
        if 200 < area < 20000:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.04 * peri, True)
            
            # Se tem 4 lados e é aproximadamente quadrado
            if len(approx) == 4:
                (x, y, w, h) = cv2.boundingRect(approx)
                ar = w / float(h)
                if 0.8 <= ar <= 1.2:
                    M = cv2.moments(c)
                    if M["m00"] != 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                        ancoras.append([cx, cy])
    
    if len(ancoras) >= 4:
        # Pega os 4 cantos detectados e ordena
        pts = np.array(ancoras, dtype="float32")
        rect = order_points(pts)
        
        # --- A CORREÇÃO MÁGICA ---
        # Definimos o tamanho final da imagem corrigida (warp)
        # Usamos escala 2x para melhor precisão na leitura
        scale = 2.0
        w_final = int(conf.PAGE_W * scale)
        h_final = int(conf.PAGE_H * scale)
        
        # Margem onde as âncoras DEVERIAM estar no PDF original
        m = conf.MARGIN * scale
        
        # Mapeamento:
        # O ponto detectado (rect[0]) vai para (m, m)
        # O ponto detectado (rect[1]) vai para (w-m, m) ... e assim por diante
        dst = np.array([
            [m, m],                     # Top-Left
            [w_final - m, m],           # Top-Right
            [w_final - m, h_final - m], # Bottom-Right
            [m, h_final - m]            # Bottom-Left
        ], dtype="float32")
        
        # Calcula a matriz de transformação e aplica
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(img, M, (w_final, h_final))
        return warped, scale
    
    # Se falhar, retorna imagem redimensionada (modo fallback)
    return cv2.resize(img, (int(conf.PAGE_W*2), int(conf.PAGE_H*2))), 2.0

def processar_gabarito(img, conf: ConfiguracaoProva, gabarito=None):
    warped, scale = alinhar_imagem(img, conf)
    
    # Converte para tons de cinza e binariza para leitura das bolinhas
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    
    res = {"respostas": {}, "frequencia": ""}
    img_vis = warped.copy()
    
    # Função auxiliar para converter coordenadas do Layout (PDF) para a Imagem (Pixel)
    # Importante: O eixo Y do ReportLab cresce para cima, o da imagem para baixo.
    # Mas como desenhamos tudo com coordenadas relativas ao topo no gerador, 
    # precisamos garantir que aqui usamos a mesma lógica.
    # No `gerador.py`, você usa: y = start_y - ...
    # Aqui vamos usar a mesma lógica.
    
    def get_coords(x_pdf, y_pdf):
        # Como o warp alinhou a imagem ao PDF (exceto pela escala),
        # a conversão é direta, apenas invertendo o Y se necessário.
        # Mas no seu gerador, o (0,0) do canvas é Bottom-Left.
        # PAGE_H - y_pdf converte para Top-Left.
        px_x = int(x_pdf * scale)
        px_y = int((conf.PAGE_H - y_pdf) * scale)
        return px_x, px_y

    # --- LEITURA DA FREQUÊNCIA ---
    if conf.tem_frequencia:
        val_freq = ""
        box_w = 54
        box_x = conf.FREQ_X
        center_x = box_x + (box_w / 2)
        offset_x = 12
        
        for col_idx in range(2): # D, U
            votos = []
            col_center_x = center_x - offset_x if col_idx == 0 else center_x + offset_x
            
            for i in range(10):
                # Mesma fórmula Y do gerador
                y_pos_pdf = conf.GRID_START_Y - 25 - (i * 18)
                
                # Coordenada na imagem
                cx, cy = get_coords(col_center_x, y_pos_pdf)
                # Ajuste fino: +3px em Y para centralizar na bolinha (compensação visual)
                cy += int(3 * scale) 
                
                # Região de Interesse (ROI)
                r = int(9 * scale) # Raio de leitura
                roi = thresh[cy-r:cy+r, cx-r:cx+r]
                
                # Conta pixels pretos (marcação)
                pixels = cv2.countNonZero(roi)
                votos.append(pixels)
                
                # Debug visual (onde o robô está olhando)
                cv2.circle(img_vis, (cx, cy), r, (200, 200, 200), 1)

            # Decide qual foi marcado
            if max(votos) > (50 * scale): # Limite de sensibilidade
                idx = np.argmax(votos)
                val_freq += str(idx)
                
                # Desenha marcação na imagem final
                y_hit_pdf = conf.GRID_START_Y - 25 - (idx * 18)
                cx, cy = get_coords(col_center_x, y_hit_pdf)
                cy += int(3 * scale)
                cv2.circle(img_vis, (cx, cy), int(10*scale), (255, 0, 0), -1) # Azul
            else:
                val_freq += "0"
        
        res["frequencia"] = val_freq

    # --- LEITURA DAS QUESTÕES ---
    current_x = conf.GRID_X_START
    
    for bloco in conf.blocos:
        for i in range(bloco.quantidade):
            q_num = bloco.questao_inicial + i
            y_pos_pdf = conf.GRID_START_Y - 25 - (i * 20)
            
            pixels_alternativas = []
            coords_alternativas = []
            
            for j in range(4): # A, B, C, D
                bx_pdf = current_x + 20 + (j * 20)
                cx, cy = get_coords(bx_pdf, y_pos_pdf)
                cy += int(3 * scale) # Ajuste fino
                coords_alternativas.append((cx, cy))
                
                r = int(9 * scale)
                roi = thresh[cy-r:cy+r, cx-r:cx+r]
                pixels_alternativas.append(cv2.countNonZero(roi))

            marcou = max(pixels_alternativas) > (50 * scale)
            idx_escolhido = np.argmax(pixels_alternativas)
            letra_aluna = ["A", "B", "C", "D"][idx_escolhido] if marcou else "."
            
            res["respostas"][q_num] = letra_aluna
            
            # --- DESENHO DO GABARITO VISUAL ---
            cx, cy = coords_alternativas[idx_escolhido]
            
            if gabarito and q_num in gabarito:
                correta = gabarito[q_num]
                idx_correta = ["A","B","C","D"].index(correta)
                cx_c, cy_c = coords_alternativas[idx_correta]
                
                if marcou:
                    if letra_aluna == correta:
                        # ACERTOU (Verde)
                        cv2.circle(img_vis, (cx, cy), int(10*scale), (0, 255, 0), -1)
                    else:
                        # ERROU (Vermelho na marcação, Anel Verde na correta)
                        cv2.circle(img_vis, (cx, cy), int(10*scale), (0, 0, 255), -1)
                        cv2.circle(img_vis, (cx_c, cy_c), int(10*scale), (0, 255, 0), 3)
                else:
                    # EM BRANCO (Mostra qual era a correta com anel amarelo)
                    cv2.circle(img_vis, (cx_c, cy_c), int(8*scale), (0, 255, 255), 2)
            
            elif marcou:
                # SEM GABARITO (Apenas mostra o que leu em cinza)
                cv2.circle(img_vis, (cx, cy), int(8*scale), (100, 100, 100), -1)
        
        # Avança para a próxima coluna de blocos
        current_x += conf.GRID_COL_W

    return res, img_vis
