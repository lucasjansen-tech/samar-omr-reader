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
    
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, thresh_ancoras = cv2.threshold(blurred, 100, 255, cv2.THRESH_BINARY_INV)
    rect = encontrar_ancoras_globais(thresh_ancoras)
    
    W_FINAL, H_FINAL = conf.REF_W, conf.REF_H
    
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
        
        blur_warp = cv2.GaussianBlur(warped, (3, 3), 0)
        _, binaria = cv2.threshold(blur_warp, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
        kernel = np.ones((2,2), np.uint8)
        binaria = cv2.morphologyEx(binaria, cv2.MORPH_OPEN, kernel)
        
        return cv2.cvtColor(warped, cv2.COLOR_GRAY2BGR), binaria, W_FINAL, H_FINAL
    
    r = cv2.resize(gray, (W_FINAL, H_FINAL))
    br = cv2.GaussianBlur(r, (3, 3), 0)
    _, rt = cv2.threshold(br, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    return cv2.cvtColor(r, cv2.COLOR_GRAY2BGR), rt, W_FINAL, H_FINAL

# Adicionado gabarito na assinatura da função
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
    
    # --- FREQUÊNCIA ---
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

    # --- QUESTÕES COM FEEDBACK DE COR ---
    for r_idx, cy in enumerate(centros_y):
        tintas = []
        for cx in centros_x:
            roi = img_binaria[cy-raio:cy+raio, cx-raio:cx+raio]
            tintas.append(cv2.countNonZero(roi))
            
        max_tinta = max(tintas)
        idx_max = np.argmax(tintas)
        media_ruido = (sum(tintas) - max_tinta) / 3 if sum(tintas) > max_tinta else 0
        
        marcou = False
        letra = "."
        
        if max_tinta > (area_roi * 0.25) and max_tinta > (media_ruido * 1.5):
            marcou = True
            letra = grid.labels[idx_max]
            
        if grid.questao_inicial > 0:
            q_num = grid.questao_inicial + r_idx
            res_bloco[q_num] = letra
            
            if marcou:
                # Lógica de Cor: Verde (Acerto), Vermelho (Erro)
                cor_marcada = (0, 255, 0) # Verde padrão
                if gabarito and q_num in gabarito:
                    if letra != gabarito[q_num]:
                        cor_marcada = (0, 0, 255) # Vermelho se errou
                
                # Desenha o círculo mais grosso para visualização clara
                cv2.circle(img_debug, (centros_x[idx_max], cy), int(raio), cor_marcada, 3)
            else:
                # Pontinhos cinzas indicam onde o sistema buscou, mas não achou tinta
                for cx in centros_x: cv2.circle(img_debug, (cx, cy), 2, (150, 150, 150), -1)

    return None, res_bloco

def processar_gabarito(img, conf: ConfiguracaoProva, gabarito=None, offset_x=0, offset_y=0):
    vis, binaria, w, h = alinhar_imagem(img, conf)
    final = {"respostas": {}, "frequencia": "00"}
    
    for g in conf.grids:
        # Passa o gabarito oficial para a função ler_grid para pintar as cores
        f_val, r_dict = ler_grid(binaria, g, w, h, vis, gabarito)
        if g.labels == ["D", "U"]: final["frequencia"] = f_val
        else: final["respostas"].update(r_dict)
            
    # --- ANÁLISE ESTATÍSTICA ---
    if gabarito:
        acertos = 0
        detalhes_correcao = {}
        
        for q_num_int, resp_lida in final["respostas"].items():
            resp_oficial = gabarito.get(q_num_int, ".")
            
            status = "Em Branco"
            if resp_lida != ".":
                if resp_lida == resp_oficial:
                    status = "Correto"
                    acertos += 1
                else:
                    status = "Incorreto"
            
            detalhes_correcao[q_num_int] = {
                "Lida": resp_lida,
                "Gabarito": resp_oficial,
                "Status": status
            }
            
        final["total_acertos"] = acertos
        final["correcao_detalhada"] = detalhes_correcao
        
    return final, vis, None
