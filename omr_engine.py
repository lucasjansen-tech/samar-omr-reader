import cv2
import numpy as np
from layout_samar import ConfiguracaoProva

def alinhar_imagem_pelas_ancoras(img, conf: ConfiguracaoProva):
    # Lógica robusta de detecção de 4 cantos (a mesma que já funcionou antes)
    # A diferença é que agora o DESTINO do warp é calculado dinamicamente
    # baseado no conf.PAGE_W e conf.PAGE_H
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 80, 255, cv2.THRESH_BINARY_INV)
    
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    ancoras = []
    
    for c in cnts:
        area = cv2.contourArea(c)
        if 200 < area < 10000:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.04 * peri, True)
            if len(approx) == 4:
                M = cv2.moments(c)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    ancoras.append([cx, cy])

    if len(ancoras) >= 4:
        # Ordenação Top-Left ... Bottom-Right
        pts = np.array(ancoras, dtype="float32")
        s = pts.sum(axis=1)
        diff = np.diff(pts, axis=1)
        rect = np.zeros((4, 2), dtype="float32")
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        
        # O PULO DO GATO: Mapear para coordenadas DO PDF (Upscaled x2 para qualidade)
        scale = 2.0
        w_pdf = conf.PAGE_W * scale
        h_pdf = conf.PAGE_H * scale
        m = conf.MARGIN * scale
        sz = conf.ANCORA_SIZE * scale
        
        # Coordenadas esperadas dos centros das âncoras no PDF
        # Lembre-se: PDF Y cresce pra cima, Imagem Y cresce pra baixo.
        # Vamos usar geometria de imagem (Top=0)
        dst = np.array([
            [m + sz/2, h_pdf - (m + sz/2)],      # TL (no PDF é embaixo, aqui invertemos logicamente ou usamos coordenadas visuais)
            # ESPERA! Para simplificar: Vamos mapear visualmente onde desenhamos os quadrados.
            # No gerador: TL é (MARGIN, H - MARGIN - SIZE).
            # Em coordenadas de IMAGEM (Y=0 em cima):
            # TL = MARGIN
            # BL = H - MARGIN - SIZE
            
            # Vamos simplificar: Mapear para os cantos exatos da imagem de saída
            [0, 0],
            [w_pdf, 0],
            [w_pdf, h_pdf],
            [0, h_pdf]
        ], dtype="float32")
        
        # Mas as âncoras detectadas não estão nos cantos 0,0, estão nas margens.
        # Ajuste Correto:
        dst = np.array([
            [m, m],                     # TL (Visualmente em cima na folha impressa)
            [w_pdf - m, m],             # TR
            [w_pdf - m, h_pdf - m],     # BR
            [m, h_pdf - m]              # BL
        ], dtype="float32")

        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(img, M, (int(w_pdf), int(h_pdf)))
        return warped, scale
    
    return cv2.resize(img, (int(conf.PAGE_W*2), int(conf.PAGE_H*2))), 2.0

def processar_gabarito(img, conf: ConfiguracaoProva, gabarito_respostas=None):
    warped, scale = alinhar_imagem_pelas_ancoras(img, conf)
    
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    
    res = {"respostas": {}, "frequencia": ""}
    img_vis = warped.copy()
    
    # Função auxiliar para converter coord PDF -> coord Imagem
    h_pdf_pt = conf.PAGE_H
    
    def pt_to_px(x_pt, y_pt):
        # ReportLab (0,0) é Bottom-Left. OpenCV é Top-Left.
        # y_opencv = (Pagina_Altura - y_reportlab) * scale
        return int(x_pt * scale), int((h_pdf_pt - y_pt) * scale)

    # --- 1. LER FREQUÊNCIA ---
    if conf.tem_frequencia:
        val_freq = ""
        for col_idx, label in enumerate(["D", "U"]):
            votos = []
            x_base = conf.FREQ_X + (col_idx * 25)
            for i in range(10):
                y_base = conf.FREQ_Y_START - 15 - (i * 18)
                
                cx, cy = pt_to_px(x_base + 10, y_base + 5) # +offsets do circulo
                roi = thresh[cy-10:cy+10, cx-10:cx+10]
                votos.append(cv2.countNonZero(roi))
                cv2.circle(img_vis, (cx, cy), 10, (255, 200, 0), 1)
            
            if max(votos) > 100:
                idx = np.argmax(votos)
                val_freq += str(idx)
                # Marcação visual
                y_hit = conf.FREQ_Y_START - 15 - (idx * 18)
                cx, cy = pt_to_px(x_base + 10, y_hit + 5)
                cv2.circle(img_vis, (cx, cy), 12, (255, 0, 0), -1)
            else:
                val_freq += "0"
        res["frequencia"] = val_freq

    # --- 2. LER QUESTÕES (Dinâmico pelos Blocos) ---
    current_x = conf.GRID_X_START
    
    for bloco in conf.blocos:
        for i in range(bloco.quantidade):
            q_num = bloco.questao_inicial + i
            y_base = conf.GRID_START_Y - 15 - (i * 20)
            
            pixels = []
            coords = []
            
            for j in range(4): # A, B, C, D
                bx = current_x + 25 + (j * 18)
                cx, cy = pt_to_px(bx, y_base + 3)
                coords.append((cx, cy))
                
                roi = thresh[cy-10:cy+10, cx-10:cx+10]
                pixels.append(cv2.countNonZero(roi))
            
            marcou = max(pixels) > 100
            idx = np.argmax(pixels)
            letra = ["A", "B", "C", "D"][idx] if marcou else "."
            res["respostas"][q_num] = letra
            
            # Desenha Máscara
            cx, cy = coords[idx]
            if gabarito_respostas and q_num in gabarito_respostas:
                correta = gabarito_respostas[q_num]
                idx_corr = ["A","B","C","D"].index(correta)
                cx_corr, cy_corr = coords[idx_corr]
                
                if marcou:
                    if letra == correta:
                        cv2.circle(img_vis, (cx, cy), 14, (0, 255, 0), -1)
                    else:
                        cv2.circle(img_vis, (cx, cy), 14, (0, 0, 255), -1)
                        cv2.circle(img_vis, (cx_corr, cy_corr), 14, (0, 255, 0), 3)
                else:
                    cv2.circle(img_vis, (cx_corr, cy_corr), 10, (0, 255, 255), 2)
            elif marcou:
                cv2.circle(img_vis, (cx, cy), 10, (100, 100, 100), -1)

        current_x += conf.GRID_COL_W

    return res, img_vis
