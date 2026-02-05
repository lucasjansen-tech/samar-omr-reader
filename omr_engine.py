import cv2
import numpy as np
from PIL import Image, ImageOps

def tratar_entrada(img_pil):
    img_pil = ImageOps.exif_transpose(img_pil)
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

def alinhar_gabarito(imagem):
    """Localiza as 4 âncoras e extrai apenas a área interna do gabarito."""
    gray = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
    # Filtro rigoroso para detectar apenas os quadrados pretos
    _, thresh = cv2.threshold(gray, 80, 255, cv2.THRESH_BINARY_INV)
    contornos, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    centros = []
    for c in contornos:
        area = cv2.contourArea(c)
        if 400 < area < 10000: # Tamanho das âncoras do SAMAR
            M = cv2.moments(c)
            if M["m00"] != 0:
                centros.append([int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])])

    if len(centros) >= 4:
        pts = np.array(centros[:4], dtype="float32")
        s = pts.sum(axis=1)
        diff = np.diff(pts, axis=1)
        rect = np.zeros((4, 2), dtype="float32")
        # Top-left, Top-right, Bottom-right, Bottom-left
        rect[0], rect[2] = pts[np.argmin(s)], pts[np.argmax(s)]
        rect[1], rect[3] = pts[np.argmin(diff)], pts[np.argmax(diff)]

        # Mapeia para uma grade fixa onde as questões estão sempre no mesmo lugar
        dst = np.array([[0,0], [800,0], [800,1000], [0,1000]], dtype="float32")
        M = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(imagem, M, (800, 1000))
    return None

def extrair_dados(alinhada, gab_oficial=None):
    gray = cv2.cvtColor(alinhada, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    
    res = {"respostas": {}, "frequencia": ""}
    img_vis = alinhada.copy()

    # 1. FREQUÊNCIA (D e U) - Lógica Decimal (00-99)
    colunas_freq = [("D", 78), ("U", 115)] # X baseado no início da âncora
    freq_final = ""
    for nome, x_base in colunas_freq:
        votos = []
        for i in range(10):
            y = 125 + (i * 24.5) # Y a partir da âncora superior
            roi = thresh[int(y):int(y+16), x_base:x_base+16]
            votos.append(cv2.countNonZero(roi))
            cv2.circle(img_vis, (x_base+8, int(y+8)), 4, (255, 0, 0), 1)
        
        idx = np.argmax(votos)
        # Se nada foi pintado (votos baixos), considera 0
        val = str(idx) if votos[idx] > 70 else "0"
        freq_final += val
        if val != "0" or votos[idx] > 70:
            cv2.circle(img_vis, (x_base+8, int(125+(idx*24.5)+8)), 8, (255, 0, 0), -1)
    res["frequencia"] = freq_final

    # 2. QUESTÕES (Blocos 1-4)
    blocos = [
        {"x": 165, "y": 305, "s": 1},  {"x": 415, "y": 305, "s": 14},
        {"x": 165, "y": 685, "s": 27}, {"x": 415, "y": 685, "s": 40}
    ]
    
    for b in blocos:
        for i in range(13):
            q_num = b["s"] + i
            y_q = int(b["y"] + (i * 25.2))
            pixels = []
            for j in range(4): # A, B, C, D
                x_q = int(b["x"] + (j * 37.5))
                roi = thresh[y_q:y_q+16, x_q:x_q+16]
                pixels.append(cv2.countNonZero(roi))
            
            idx_a = np.argmax(pixels)
            marcou = max(pixels) > 75
            letra_aluno = ["A", "B", "C", "D"][idx_a] if marcou else "."
            res["respostas"][q_num] = letra_aluno

            # POSIÇÃO DOS CÍRCULOS VERDES (Sobre a letra marcada)
            if marcou:
                x_v = int(b["x"] + (idx_a * 37.5) + 8)
                cv2.circle(img_vis, (x_v, y_q+8), 11, (0, 255, 0), 2)
            
            # PONTO VERMELHO (Gabarito Raiz)
            if gab_oficial and q_num in gab_oficial:
                idx_c = ["A", "B", "C", "D"].index(gab_oficial[q_num])
                x_c = int(b["x"] + (idx_c * 37.5) + 8)
                cv2.circle(img_vis, (x_c, y_q+8), 3, (0, 0, 255), -1)

    return res, img_vis
