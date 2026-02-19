import cv2
import numpy as np

def order_points(pts):
    # Organiza os 4 pontos na ordem: Top-Left, Top-Right, Bottom-Right, Bottom-Left
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def processar_gabarito(image, conf, gabarito_oficial):
    REF_W = conf.REF_W
    REF_H = conf.REF_H

    # 1. Pré-processamento inicial para encontrar âncoras
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 51, 15)

    # 2. Detecção de Contornos e Âncoras
    cnts, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    anchors = []
    for c in cnts:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.04 * peri, True)
        if len(approx) == 4:
            _, _, w, h = cv2.boundingRect(approx)
            ar = w / float(h)
            area = cv2.contourArea(c)
            if 0.8 <= ar <= 1.2 and area > 400:
                anchors.append(approx)

    if len(anchors) < 4:
        return {"erro": "Âncoras não encontradas."}, image, None

    # 3. Ordenação e Perspectiva (Warp)
    anchors = sorted(anchors, key=cv2.contourArea, reverse=True)[:4]
    pts = np.array([[x + w/2, y + h/2] for (x, y, w, h) in [cv2.boundingRect(a) for a in anchors]], dtype="float32")
    rect = order_points(pts)

    m = REF_W * conf.MARGIN_PCT
    s = 30 
    
    dst = np.array([
        [m + s/2, m + s/2],
        [REF_W - m - s/2, m + s/2],
        [REF_W - m - s/2, REF_H - m - s/2],
        [m + s/2, REF_H - m - s/2]
    ], dtype="float32")

    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(gray, M, (REF_W, REF_H)) # Imagem em tons de cinza alinhada
    warped_color = cv2.warpPerspective(image, M, (REF_W, REF_H)) # Imagem colorida alinhada

    # ====================================================================
    # BALANÇA DE ROTAÇÃO 180º (COM RASCUNHO TEMPORÁRIO)
    # ====================================================================
    # Cria um threshold temporário apenas para pesar a tinta nas pontas
    thresh_temp = cv2.adaptiveThreshold(warped, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 51, 15)

    mid_x_start = int(REF_W * 0.2)
    mid_x_end = int(REF_W * 0.8)

    # Topo: 4% a 10% (Onde estão os Títulos e Logos - Deve ser pesado)
    top_band = thresh_temp[int(REF_H*0.04):int(REF_H*0.10), mid_x_start:mid_x_end]
    # Fundo: 93% a 97% (Onde deve ser VAZIO absoluto - Deve ser leve)
    bot_band = thresh_temp[int(REF_H*0.93):int(REF_H*0.97), mid_x_start:mid_x_end]
    
    top_dark = cv2.countNonZero(top_band)
    bot_dark = cv2.countNonZero(bot_band)
    
    # Se o fundo pesar mais que o topo, está invertido.
    if bot_dark > top_dark:
        # Gira APENAS as imagens de base (cinza e colorida) para não perder qualidade
        warped = cv2.rotate(warped, cv2.ROTATE_180)
        warped_color = cv2.rotate(warped_color, cv2.ROTATE_180)
        # O threshold temporário é descartado.

    # ====================================================================
    # APLICA O THRESHOLD FINAL NA IMAGEM JÁ NA POSIÇÃO CORRETA
    # ====================================================================
    # Agora sim, geramos o alto contraste definitivo na imagem alinhada.
    # Isso garante bordas de bolinhas muito mais limpas e precisas.
    thresh_warped = cv2.adaptiveThreshold(warped, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 51, 15)

    # 5. Análise das Bolinhas (Loop Principal)
    respostas = {}
    correcao_detalhada = {}
    total_acertos = 0
    freq_arr = ["0", "0"] 

    for grid in conf.grids:
        x1 = int(grid.x_start * REF_W)
        x2 = int(grid.x_end * REF_W)
        y1 = int(grid.y_start * REF_H)
        y2 = int(grid.y_end * REF_H)

        cell_w = (x2 - x1) / grid.cols
        cell_h = (y2 - y1) / grid.rows

        for row in range(grid.rows):
            marcadas = []
            
            for col in range(grid.cols):
                cx = int(x1 + (col * cell_w) + (cell_w / 2))
                cy = int(y1 + (row * cell_h) + (cell_h / 2))
                
                raio = int(min(cell_w, cell_h) * 0.25)
                mask = np.zeros(thresh_warped.shape, dtype="uint8")
                cv2.circle(mask, (cx, cy), raio, 255, -1)
                
                mask = cv2.bitwise_and(thresh_warped, thresh_warped, mask=mask)
                total_pixels = cv2.countNonZero(mask)
                area_bolinha = np.pi * (raio ** 2)
                
                # Limiar de 40% de preenchimento
                if (total_pixels / area_bolinha) > 0.40:
                    marcadas.append(col)
                    cv2.circle(warped_color, (cx, cy), raio+4, (0, 165, 255), 2) # Círculo Laranja na detecção crua

            # Lógica de Correção e Frequência
            if grid.labels == ["D", "U"]:
                if 0 in marcadas: freq_arr[0] = str(row)
                if 1 in marcadas: freq_arr[1] = str(row)
            else:
                q_num = grid.questao_inicial + row
                if len(marcadas) == 0:
                    respostas[q_num] = "-"
                    correcao_detalhada[q_num] = {"Status": "Em Branco"}
                elif len(marcadas) > 1:
                    respostas[q_num] = "*"
                    correcao_detalhada[q_num] = {"Status": "Múltiplas Marcações"}
                else:
                    resp_letra = grid.labels[marcadas[0]]
                    respostas[q_num] = resp_letra
                    
                    gabarito_q = gabarito_oficial.get(q_num, "NULA")
                    # Desenha os círculos de correção (Verde/Vermelho/Azul) sobre o laranja
                    cx_final = int(x1 + (marcadas[0]*cell_w) + cell_w/2)
                    cy_final = int(y1 + (row*cell_h) + cell_h/2)

                    if gabarito_q == "NULA":
                        total_acertos += 1
                        correcao_detalhada[q_num] = {"Status": "Correto (Anulada)"}
                        cv2.circle(warped_color, (cx_final, cy_final), raio+4, (255, 0, 0), 3) 
                    elif resp_letra == gabarito_q:
                        total_acertos += 1
                        correcao_detalhada[q_num] = {"Status": "Correto"}
                        cv2.circle(warped_color, (cx_final, cy_final), raio+4, (0, 255, 0), 3) 
                    else:
                        correcao_detalhada[q_num] = {"Status": "Incorreto"}
                        cv2.circle(warped_color, (cx_final, cy_final), raio+4, (0, 0, 255), 3) 

    frequencia = "".join(freq_arr)
    
    resultado_final = {
        "frequencia": frequencia,
        "respostas": respostas,
        "total_acertos": total_acertos,
        "correcao_detalhada": correcao_detalhada
    }
    
    return resultado_final, warped_color, None
