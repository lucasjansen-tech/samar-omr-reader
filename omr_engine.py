import cv2
import numpy as np
from PIL import Image, ImageOps

def tratar_entrada(img_pil):
    img_pil = ImageOps.exif_transpose(img_pil)
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

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

def alinhar_gabarito(imagem):
    # Redimensiona para 1000px de largura mantendo proporção
    h_orig, w_orig = imagem.shape[:2]
    ratio = 1000.0 / w_orig
    img_resize = cv2.resize(imagem, (1000, int(h_orig * ratio)))
    
    gray = cv2.cvtColor(img_resize, cv2.COLOR_BGR2GRAY)
    
    # TRUQUE NOVO: Morphological Closing
    # Isso "fecha" buracos dentro dos quadrados pretos para facilitar a detecção
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    closed = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
    
    # Binarização
    _, thresh = cv2.threshold(closed, 90, 255, cv2.THRESH_BINARY_INV)
    
    # Procura contornos nos 4 cantos da imagem
    h, w = img_resize.shape[:2]
    centers = []
    
    # Margens de busca (evita bordas sujas e foca nos cantos)
    margem_x = int(w * 0.25) # 25% da largura
    margem_y = int(h * 0.25) # 25% da altura
    
    quadrantes = [
        (0, 0, margem_x, margem_y),           # Top-Left
        (w - margem_x, 0, w, margem_y),       # Top-Right
        (w - margem_x, h - margem_y, w, h),   # Bottom-Right
        (0, h - margem_y, margem_x, h)        # Bottom-Left
    ]
    
    for (x1, y1, x2, y2) in quadrantes:
        roi = thresh[y1:y2, x1:x2]
        cnts, _ = cv2.findContours(roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if cnts:
            # Pega o maior objeto preto do quadrante (a âncora)
            c = max(cnts, key=cv2.contourArea)
            area = cv2.contourArea(c)
            
            # Aceita qualquer coisa grande e preta (não precisa ser quadrado perfeito)
            if area > 300: 
                M = cv2.moments(c)
                if M["m00"] != 0:
                    cX = int((M["m10"] / M["m00"]) + x1)
                    cY = int((M["m01"] / M["m00"]) + y1)
                    centers.append([cX, cY])

    # Se achou os 4 pontos, faz o alinhamento
    if len(centers) == 4:
        pts = np.array(centers, dtype="float32")
        rect = order_points(pts)
        
        # Warp para tamanho PADRÃO (1000 x 1400)
        dst = np.array([
            [0, 0],
            [1000 - 1, 0],
            [1000 - 1, 1400 - 1],
            [0, 1400 - 1]], dtype="float32")

        M = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(img_resize, M, (1000, 1400))
    
    # FALLBACK INTELIGENTE:
    # Se falhar, tenta achar a borda da folha inteira
    print("Âncoras não encontradas. Tentando enquadramento da página...")
    cnts_page, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if cnts_page:
        c_page = max(cnts_page, key=cv2.contourArea)
        if cv2.contourArea(c_page) > (h * w * 0.5): # Se for maior que 50% da imagem
            rect = cv2.minAreaRect(c_page)
            box = cv2.boxPoints(rect)
            box = np.int0(box)
            rect_ordered = order_points(box.astype("float32"))
            dst = np.array([[0,0], [999,0], [999,1399], [0,1399]], dtype="float32")
            M = cv2.getPerspectiveTransform(rect_ordered, dst)
            return cv2.warpPerspective(img_resize, M, (1000, 1400))

    return cv2.resize(imagem, (1000, 1400))

def extrair_dados(img_warped, gab_oficial=None):
    # Imagem PADRONIZADA 1000x1400
    gray = cv2.cvtColor(img_warped, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    
    res = {"respostas": {}, "frequencia": ""}
    img_mask = img_warped.copy()

    # --- 1. FREQUÊNCIA ---
    # Correção: Movido para BAIXO (Y=245) para sair de cima das letras D/U
    # Correção: Movido para DIREITA (X=145/192) para pegar as bolinhas
    cols_freq = [("D", 145), ("U", 192)] 
    freq_final = ""

    for nome, x in cols_freq:
        votos = []
        for i in range(10):
            # Y inicial = 245, Passo = 35
            y = int(245 + (i * 35)) 
            
            # ROI maior (14px) para tolerar desalinhamento
            roi = thresh[y-14:y+14, x-14:x+14]
            votos.append(cv2.countNonZero(roi))
            
            # Debug: Mostra onde está lendo (azul claro vazio)
            cv2.circle(img_mask, (x, y), 14, (255, 200, 0), 1)
        
        if max(votos) > 130:
            idx = np.argmax(votos)
            freq_final += str(idx)
            cv2.circle(img_mask, (x, int(245 + (idx * 35))), 14, (255, 0, 0), -1)
        else:
            freq_final += "0"
            
    res["frequencia"] = freq_final

    # --- 2. QUESTÕES ---
    # Correção: Blocos movidos +45px para a DIREITA para sair de cima das letras A,B...
    # Correção: Blocos movidos +10px para BAIXO para centralizar
    blocos = [
        (265, 460, 1),   # Bloco 1 (Esq)
        (580, 460, 14),  # Bloco 2 (Dir)
        (265, 990, 27),  # Bloco 3 (Esq Baixo)
        (580, 990, 40)   # Bloco 4 (Dir Baixo)
    ]
    
    step_x = 50 # Distância entre bolinhas horizontal
    step_y = 36.5 # Distância vertical

    for (bx, by, q_start) in blocos:
        for i in range(13):
            q_num = q_start + i
            cy = int(by + (i * step_y))
            
            pixels_q = []
            for j in range(4): # A, B, C, D
                cx = int(bx + (j * step_x))
                roi = thresh[cy-14:cy+14, cx-14:cx+14]
                pixels_q.append(cv2.countNonZero(roi))
                
                # Debug: Mostra grade de leitura (verde claro vazio)
                # cv2.circle(img_mask, (cx, cy), 14, (0, 255, 0), 1)
            
            marcou = max(pixels_q) > 130
            idx_aluno = np.argmax(pixels_q)
            letra_aluno = ["A", "B", "C", "D"][idx_aluno] if marcou else "."
            res["respostas"][q_num] = letra_aluno

            # MÁSCARA VISUAL
            cx_aluno = int(bx + (idx_aluno * step_x))

            if gab_oficial and q_num in gab_oficial:
                correta = gab_oficial[q_num]
                idx_correta = ["A", "B", "C", "D"].index(correta)
                cx_correta = int(bx + (idx_correta * step_x))

                if marcou:
                    if letra_aluno == correta:
                        cv2.circle(img_mask, (cx_aluno, cy), 14, (0, 255, 0), -1) # Verde
                    else:
                        cv2.circle(img_mask, (cx_aluno, cy), 14, (0, 0, 255), -1) # Vermelho
                        cv2.circle(img_mask, (cx_correta, cy), 14, (0, 255, 0), 3) # Anel Verde
                else:
                    cv2.circle(img_mask, (cx_correta, cy), 10, (0, 255, 255), 2) # Amarelo (Branco)
            
            elif marcou:
                 cv2.circle(img_mask, (cx_aluno, cy), 12, (100, 100, 100), -1) # Cinza

    return res, img_mask
