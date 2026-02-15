import cv2
import numpy as np
from layout_samar import ConfiguracaoProva, GridConfig

def encontrar_ancoras_globais(thresh):
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    h, w = thresh.shape
    candidatos = []
    
    for c in cnts:
        area = cv2.contourArea(c)
        if area < (w * h * 0.001) or area > (w * h * 0.05): continue
        
        hull = cv2.convexHull(c)
        solidez = area / float(cv2.contourArea(hull)) if cv2.contourArea(hull) > 0 else 0
        x, y, bw, bh = cv2.boundingRect(c)
        ar = bw / float(bh)
        
        if solidez > 0.7 and 0.5 <= ar <= 2.0:
            M = cv2.moments(c)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                candidatos.append((cx, cy, area))
                
    if len(candidatos) < 4: return None
    
    pt_tl = min(candidatos, key=lambda item: item[0] + item[1])[:2]
    pt_tr = min(candidatos, key=lambda item: (w - item[0]) + item[1])[:2]
    pt_bl = min(candidatos, key=lambda item: item[0] + (h - item[1]))[:2]
    pt_br = min(candidatos, key=lambda item: (w - item[0]) + (h - item[1]))[:2]
    
    return np.array([pt_tl, pt_tr, pt_br, pt_bl], dtype="float32")

def alinhar_imagem(img, conf: ConfiguracaoProva):
    if len(img.shape) == 3: gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else: gray = img
    
    W_FINAL, H_FINAL = conf.REF_W, conf.REF_H
    is_evalbee = "EVALBEE" in conf.titulo_prova.upper()
    
    # =======================================================
    # A SOLUÇÃO: SE FOR EVALBEE, APENAS PEGA A IMAGEM COMO É
    # =======================================================
    if is_evalbee:
        # Pega a imagem do jeito que está e ajusta para A4 de forma "flat".
        warped = cv2.resize(gray, (W_FINAL, H_FINAL))
    else:
        # LÓGICA NATIVA SAMAR (Mantida intocada)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, thresh_ancoras = cv2.threshold(blurred, 120, 255, cv2.THRESH_BINARY_INV)
        rect = encontrar_ancoras_globais(thresh_ancoras)
        
        if rect is not None:
            m_px = W_FINAL * conf.MARGIN_PCT
            s_px = W_FINAL * 0.04 
            offset = m_px + (s_px / 2.0)
            dst = np.array([
                [offset, offset],
                [W_FINAL - offset, offset],
                [W_FINAL - offset, H_FINAL - offset],
                [offset, H_FINAL - offset]
            ], dtype="float32")
            M = cv2.getPerspectiveTransform(rect, dst)
            warped = cv2.warpPerspective(gray, M, (W_FINAL, H_FINAL))
        else:
            warped = cv2.resize(gray, (W_FINAL, H_FINAL))
            
    # Filtro OTSU
    blur_warp = cv2.GaussianBlur(warped, (3, 3), 0)
    _, binaria = cv2.threshold(blur_warp, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    kernel = np.ones((2,2), np.uint8)
    binaria = cv2.morphologyEx(binaria, cv2.MORPH_OPEN, kernel)
    
    return cv2.cvtColor(warped, cv2.COLOR_GRAY2BGR), binaria, W_FINAL, H_FINAL

def ler_grid(img_binaria, grid: GridConfig, w_img, h_img, img_debug, gabarito=None):
    x1 = grid.x_start * w_img
    x2 = grid.x_end * w_img
    y1 = grid.y_start * h_img
    y2 = grid.y_end * h_img
    
    cv2.rectangle(img_debug, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
    
    cell_w = (x2 - x1) / grid.cols
    cell_h = (y2 - y1) / grid.rows
    
    centros_x = [int(x1 + (c * cell_w) + (cell_w / 2)) for c in range(grid.cols)]
    centros_y = [int(y1 + (r * cell_h) + (cell_h / 2)) for r in range(grid.rows)]
    
    raio = int(min(cell_w, cell_h) * 0.18) 
    area_roi = (raio * 2) ** 2
    
    res_bloco = {}
    
    if grid.labels == ["D", "U"]:
        freq_res = ["0", "0"]
        for c_idx, cx in enumerate(centros_x):
            votos = []
            for cy in centros_y:
                roi = img_binaria[cy-raio:cy+raio, cx-raio:cx+raio]
                votos.append(cv2.countNonZero(roi))
                cv2.circle(img_debug, (cx, cy), 2, (0, 255, 255), -1)
            
            idx_max = np.argmax(votos)
            max_tinta = max(votos)
            
            if max_tinta > (area_roi * 0.25):
                freq_res[c_idx] = str(idx_max)
                cv2.circle(img_debug, (cx, centros_y[idx_max]), int(raio), (255, 0, 0), -1)
                
        return "".join(freq_res), {}

    for r_idx, cy in enumerate(centros_y):
        tintas = []
        for cx in centros_x:
            roi = img_binaria[cy-raio:cy+raio, cx-raio:cx+raio]
            tintas.append(cv2.countNonZero(roi))
            
        marcadas = []
        max_tinta_linha = max(tintas) if tintas else 0
        
        for idx, tinta in enumerate(tintas):
            if tinta > (area_roi * 0.25) and tinta > (max_tinta_linha * 0.60):
                marcadas.append(idx)
        
        if grid.questao_inicial > 0:
            q_num = grid.questao_inicial + r_idx
            resp_oficial = gabarito.get(q_num, ".") if gabarito else "."
            
            if len(marcadas) == 0:
                res_bloco[q_num] = "."
                for cx in centros_x: cv2.circle(img_debug, (cx, cy), 2, (150, 150, 150), -1)
                
            elif len(marcadas) == 1:
                idx_max = marcadas[0]
                letra = grid.labels[idx_max]
                res_bloco[q_num] = letra
                
                cor = (0, 255, 0) 
                if resp_oficial in ["NULA", "X"]:
                    cor = (255, 200, 0) 
                elif gabarito and letra != resp_oficial:
                    cor = (0, 0, 255) 
                    
                cv2.circle(img_debug, (centros_x[idx_max], cy), int(raio), cor, 3)
                
            else:
                res_bloco[q_num] = "*" 
                cor = (255, 200, 0) if resp_oficial in ["NULA", "X"] else (0, 140, 255)
                for idx in marcadas:
                    cv2.circle(img_debug, (centros_x[idx], cy), int(raio), cor, 3)

    return None, res_bloco

def processar_gabarito(img, conf: ConfiguracaoProva, gabarito=None, offset_x=0, offset_y=0):
    vis, binaria, w, h = alinhar_imagem(img, conf)
    final = {"respostas": {}, "frequencia": "00"}
    
    for g in conf.grids:
        f_val, r_dict = ler_grid(binaria, g, w, h, vis, gabarito)
        if g.labels == ["D", "U"]: final["frequencia"] = f_val
        else: final["respostas"].update(r_dict)
            
    if gabarito:
        acertos = 0
        detalhes_correcao = {}
        
        for q_num_int, resp_lida in final["respostas"].items():
            resp_oficial = gabarito.get(q_num_int, ".")
            status = "Em Branco"
            
            if resp_oficial in ["NULA", "X"]:
                status = "Correto (Anulada)"
                acertos += 1
            else:
                if resp_lida == "*":
                    status = "Múltiplas Marcações" 
                elif resp_lida != ".":
                    if resp_lida == resp_oficial:
                        status = "Correto"
                        acertos += 1
                    else:
                        status = "Incorreto"
            
            detalhes_correcao[q_num_int] = {
                "Lida": "Múltiplas" if resp_lida == "*" else resp_lida,
                "Gabarito": resp_oficial,
                "Status": status
            }
            
        final["total_acertos"] = acertos
        final["correcao_detalhada"] = detalhes_correcao
        
    return final, vis, None
