import cv2
import numpy as np
from layout_samar import ConfiguracaoProva, GridConfig

def encontrar_ancoras_globais(thresh):
    """Encontra os 4 cantos extremos da folha."""
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidatos = []
    h, w = thresh.shape
    
    for c in cnts:
        area = cv2.contourArea(c)
        if area < 100 or area > (w*h*0.1): continue
        approx = cv2.approxPolyDP(c, 0.04 * cv2.arcLength(c, True), True)
        if len(approx) == 4:
            x, y, bw, bh = cv2.boundingRect(approx)
            ar = bw / float(bh)
            if 0.7 <= ar <= 1.3: # Quadrado
                M = cv2.moments(c)
                if M["m00"] != 0:
                    candidatos.append([int(M["m10"]/M["m00"]), int(M["m01"]/M["m00"])])
    
    if len(candidatos) < 4: return None
    pts = np.array(candidatos, dtype="float32")
    s = pts.sum(axis=1); d = np.diff(pts, axis=1)
    return np.array([pts[np.argmin(s)], pts[np.argmin(d)], pts[np.argmax(s)], pts[np.argmax(d)]], dtype="float32")

def alinhar_imagem(img, conf: ConfiguracaoProva):
    """
    Normaliza a imagem para o tamanho de referência (REF_W x REF_H)
    baseado nas âncoras.
    """
    if len(img.shape) == 3: gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else: gray = img
    
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    
    rect = encontrar_ancoras_globais(thresh)
    
    # Tamanho de trabalho padronizado (Alta resolução)
    W_FINAL = conf.REF_W
    H_FINAL = conf.REF_H
    
    if rect is not None:
        # Âncoras ficam a 5% das bordas (definido no layout)
        m = int(W_FINAL * conf.MARGIN_PCT)
        
        dst = np.array([
            [m, m],                 # TL
            [W_FINAL-m, m],         # TR
            [W_FINAL-m, H_FINAL-m], # BR
            [m, H_FINAL-m]          # BL
        ], dtype="float32")
        
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(img, M, (W_FINAL, H_FINAL))
        return warped, W_FINAL, H_FINAL
    
    return cv2.resize(img, (W_FINAL, H_FINAL)), W_FINAL, H_FINAL

def ler_grid(img_thresh, grid: GridConfig, w_img, h_img, img_debug):
    """
    Lê um grid específico (Frequência ou Bloco) dividindo-o matematicamente.
    """
    # 1. Definir a área do Grid em pixels
    x1 = int(grid.x_start_pct * w_img)
    x2 = int(grid.x_end_pct * w_img)
    y1 = int(grid.y_start_pct * h_img)
    y2 = int(grid.y_end_pct * h_img)
    
    # Desenha o retângulo do grid no debug (Visualização do "Quadrante")
    cv2.rectangle(img_debug, (x1, y1), (x2, y2), (255, 0, 0), 2)
    
    # Altura e largura de CADA CÉLULA (Bolinha)
    cell_h = (y2 - y1) / grid.rows
    cell_w = (x2 - x1) / grid.cols
    
    resultados_bloco = {}
    
    for r in range(grid.rows):
        densidades = []
        centros = []
        
        # Coordenada Y central da linha atual
        cy = int(y1 + (r * cell_h) + (cell_h / 2))
        
        for c in range(grid.cols):
            # Coordenada X central da coluna atual
            cx = int(x1 + (c * cell_w) + (cell_w / 2))
            centros.append((cx, cy))
            
            # ROI de leitura (Raio fixo ou proporcional)
            raio = int(min(cell_h, cell_w) * 0.25)
            roi = img_thresh[cy-raio:cy+raio, cx-raio:cx+raio]
            densidades.append(cv2.countNonZero(roi))
            
            # Debug: Mostra onde leu
            cv2.circle(img_debug, (cx, cy), raio, (200, 200, 200), 1)

        # Lógica Winner-Takes-All para a linha
        max_val = max(densidades)
        idx_max = np.argmax(densidades)
        avg_val = sum(densidades) / len(densidades)
        
        if grid.labels[0] == "D": # Lógica especial Frequência (Dígito a Dígito)
             # Na freq, lemos cada coluna independentemente? 
             # No seu layout, é uma coluna D e uma U.
             # O loop acima percorre D e U na mesma linha (ex: 0 e 0).
             # Isso não serve para freq vertical.
             # Ajuste: A Freq é lida verticalmente, mas o grid foi definido como 10 linhas.
             # Então a linha 0 tem o número '0' da Dezena e '0' da Unidade.
             pass # Frequência será tratada montando o número no final
        
        # Critério de Marcação
        marcou = False
        letra = "."
        
        if max_val > (raio*raio*0.8) and max_val > (avg_val * 1.3):
            marcou = True
            if grid.labels == ["D", "U"]: # Frequência
                # Retorna qual coluna foi marcada (D ou U) e o valor é o índice da linha
                letra = str(r) # O valor é a linha (0 a 9)
                # Guarda (coluna, valor)
                resultados_bloco[f"L{r}"] = (c, marcou) # Simplificação
            else:
                letra = grid.labels[idx_max]
        
        # Salva resultado da Questão
        if grid.questao_inicial > 0:
            q_num = grid.questao_inicial + r
            resultados_bloco[q_num] = letra if marcou else "."
            
            # Pinta o debug
            if marcou:
                cv2.circle(img_debug, centros[idx_max], int(raio*1.2), (0, 255, 0), 2)

    # Tratamento especial para Frequência (Retornar string "15", "02", etc)
    if grid.labels == ["D", "U"]:
        # Recalcular lógica vertical para freq
        # Vamos varrer colunas verticalmente
        freq_res = ["0", "0"]
        for c in range(grid.cols):
            col_votos = []
            for r in range(grid.rows):
                cx = int(x1 + (c * cell_w) + (cell_w / 2))
                cy = int(y1 + (r * cell_h) + (cell_h / 2))
                raio = int(min(cell_h, cell_w) * 0.25)
                roi = img_thresh[cy-raio:cy+raio, cx-raio:cx+raio]
                col_votos.append(cv2.countNonZero(roi))
            
            idx_voto = np.argmax(col_votos)
            if max(col_votos) > (raio*raio*0.8):
                freq_res[c] = str(idx_voto)
                # Pinta debug
                cy_hit = int(y1 + (idx_voto * cell_h) + (cell_h / 2))
                cx_hit = int(x1 + (c * cell_w) + (cell_w / 2))
                cv2.circle(img_debug, (cx_hit, cy_hit), int(raio*1.2), (255, 0, 0), -1)
                
        return "".join(freq_res), resultados_bloco

    return None, resultados_bloco

def processar_gabarito(img, conf: ConfiguracaoProva, gabarito=None, offset_x=0, offset_y=0):
    warped, w, h = alinhar_imagem(img, conf)
    
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 51, 10)
    
    img_vis = warped.copy()
    res_final = {"respostas": {}, "frequencia": "00"}
    
    # Processa cada GRID definido no Layout
    for grid in conf.grids:
        freq_val, dict_res = ler_grid(thresh, grid, w, h, img_vis)
        
        if grid.labels == ["D", "U"]:
            res_final["frequencia"] = freq_val
        else:
            res_final["respostas"].update(dict_res)
            
    return res_final, img_vis, None
