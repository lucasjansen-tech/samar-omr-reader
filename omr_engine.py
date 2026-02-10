import cv2
import numpy as np
from layout_samar import ConfiguracaoProva

def order_points(pts):
    # Ordena coordenadas: Top-Esq, Top-Dir, Inf-Dir, Inf-Esq
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def pre_processamento_robusto(img):
    """
    Prepara a imagem para funcionar em qualquer scanner/câmera.
    Remove ruído, corrige iluminação e fecha buracos de impressão.
    """
    # 1. Converte para Cinza
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img

    # 2. Blur para reduzir ruído de scanner (pontilhados)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # 3. Canny Edge Detection (Melhor que Threshold simples para achar bordas)
    edged = cv2.Canny(blurred, 75, 200)

    # 4. Operações Morfológicas (Engrossar linhas falhadas)
    # Isso salva impressões com pouca tinta ou scanners ruins
    kernel = np.ones((5,5), np.uint8)
    dilated = cv2.dilate(edged, kernel, iterations=2)
    
    return dilated

def encontrar_ancoras_robustas(img_processada):
    """
    Não busca quadrados perfeitos. Busca os 4 elementos principais nos cantos.
    """
    cnts, _ = cv2.findContours(img_processada.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Ordena contornos do maior para o menor
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
    
    ancoras_candidatas = []
    
    h_img, w_img = img_processada.shape[:2]
    area_total = h_img * w_img

    for c in cnts:
        area = cv2.contourArea(c)
        
        # Filtro de Tamanho: Ignora sujeira pequena e ignora borda da folha inteira
        # Uma âncora deve ser aprox 0.05% a 5% da folha
        if (area_total * 0.0005) < area < (area_total * 0.05):
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.03 * peri, True)
            
            # Se tem 4 pontas (quadrado) OU é uma mancha densa (blob)
            # Aceitamos blobs redondos também, pois scanners distorcem cantos
            if len(approx) >= 4:
                x, y, w, h = cv2.boundingRect(approx)
                ar = w / float(h)
                
                # Aspect Ratio: Âncora é mais ou menos quadrada (0.5 a 1.5)
                if 0.5 <= ar <= 1.5:
                    ancoras_candidatas.append(c)
            
        if len(ancoras_candidatas) >= 4:
            break
            
    return ancoras_candidatas

def alinhar_imagem(img, conf: ConfiguracaoProva):
    # Processamento pesado para destacar as marcas pretas
    processed = pre_processamento_robusto(img)
    cnts = encontrar_ancoras_robustas(processed)
    
    if len(cnts) == 4:
        # Extrai os centros das 4 âncoras encontradas
        pts_raw = []
        for c in cnts:
            M = cv2.moments(c)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                pts_raw.append([cx, cy])
            else:
                # Fallback se momento for zero (raro)
                x,y,_,_ = cv2.boundingRect(c)
                pts_raw.append([x, y])

        pts = np.array(pts_raw, dtype="float32")
        rect = order_points(pts)

        # --- WARP DE PERSPECTIVA ---
        scale = 2.0
        w_final = int(conf.PAGE_W * scale)
        h_final = int(conf.PAGE_H * scale)
        
        # Onde as âncoras deveriam estar (Baseado no layout)
        m = conf.MARGIN * scale
        
        # Mapeia os 4 pontos encontrados para os 4 cantos ideais
        # AQUI É O SEGREDO: Forçamos a imagem a caber no gabarito ideal
        dst = np.array([
            [m, m],                     # Top-Left
            [w_final - m, m],           # Top-Right
            [w_final - m, h_final - m], # Bottom-Right
            [m, h_final - m]            # Bottom-Left
        ], dtype="float32")
        
        M = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(img, M, (w_final, h_final)), scale
    
    else:
        # MODO DE EMERGÊNCIA: Se não achou 4 âncoras, tenta usar as bordas da imagem
        # Isso ajuda se a pessoa cortou a foto bem em cima das âncoras
        return cv2.resize(img, (int(conf.PAGE_W*2), int(conf.PAGE_H*2))), 2.0

def processar_gabarito(img, conf: ConfiguracaoProva, gabarito=None, offset_x=0, offset_y=0):
    warped, scale = alinhar_imagem(img, conf)
    
    # Binarização para leitura (Otsu é ótimo para scanner, Adaptive é melhor para câmera)
    gray = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    
    # Adaptive Threshold: Resolve problemas de sombra e iluminação desigual
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY_INV, 51, 10)
    
    res = {"respostas": {}, "frequencia": ""}
    img_vis = warped.copy()
    
    def pdf_to_pixel(x, y_pdf):
        # Transforma coordenada do PDF (Pontos) para Imagem (Pixels)
        px = int(x * scale) + offset_x
        py = int((conf.PAGE_H - y_pdf) * scale) + offset_y
        return px, py
    
    start_y = conf.GRID_START_Y
    
    # 1. FREQUÊNCIA
    if conf.tem_frequencia:
        val_freq = ""
        center_x = conf.FREQ_X + 27 # Centro da caixa
        offset_col = 12
        
        for col_idx in range(2): 
            votos = []
            col_cx = center_x - offset_col if col_idx == 0 else center_x + offset_col
            
            for i in range(10):
                # Usamos a lógica relativa robusta
                y_pos = start_y - 25 - (i * 18)
                cx, cy = pdf_to_pixel(col_cx, y_pos + 3)
                
                # Aumentei o raio de leitura para pegar marcações mal centralizadas
                roi = thresh[cy-11:cy+11, cx-11:cx+11]
                votos.append(cv2.countNonZero(roi))
                
                # Visualização da área de busca (Cinza claro)
                cv2.circle(img_vis, (cx, cy), 11, (200, 200, 200), 1)
            
            # Limiar de detecção (Sensitivity)
            # Se mais de 35% dos pixels do circulo forem pretos, marcou.
            if max(votos) > (150): 
                idx = np.argmax(votos)
                val_freq += str(idx)
                
                y_hit = start_y - 25 - (idx * 18)
                cx, cy = pdf_to_pixel(col_cx, y_hit + 3)
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
            
            pixels = []
            coords = []
            for j in range(4):
                bx = current_x + 20 + (j * 20)
                cx, cy = pdf_to_pixel(bx, y_pos + 3)
                coords.append((cx, cy))
                
                # ROI maior para robustez
                roi = thresh[cy-11:cy+11, cx-11:cx+11]
                pixels.append(cv2.countNonZero(roi))
            
            # Detecção de marcação
            if max(pixels) > 150:
                idx = np.argmax(pixels)
                letra = ["A", "B", "C", "D"][idx]
                res["respostas"][q_num] = letra
                marcou = True
            else:
                letra = "."
                marcou = False
                idx = 0 # Default para visualização
            
            # Visualização do Gabarito
            cx, cy = coords[idx]
            if gabarito and q_num in gabarito:
                correta = gabarito[q_num]
                idx_c = ["A","B","C","D"].index(correta)
                cx_c, cy_c = coords[idx_c]
                
                if marcou:
                    if letra == correta:
                        cv2.circle(img_vis, (cx, cy), 13, (0, 255, 0), -1) # Verde (Certo)
                    else:
                        cv2.circle(img_vis, (cx, cy), 13, (0, 0, 255), -1) # Vermelho (Errado)
                        cv2.circle(img_vis, (cx_c, cy_c), 13, (0, 255, 0), 3) # Verde Vazado (Era essa)
                else:
                     # Em branco: Mostra qual era a certa em Amarelo
                    cv2.circle(img_vis, (cx_c, cy_c), 10, (0, 255, 255), 2)
            elif marcou:
                # Sem gabarito oficial: Apenas mostra o que leu em cinza
                cv2.circle(img_vis, (cx, cy), 10, (100, 100, 100), -1)
                
        current_x += conf.GRID_COL_W
        
    return res, img_vis
