import cv2
import numpy as np
from PIL import Image, ImageOps

def tratar_entrada(img_pil):
    img_pil = ImageOps.exif_transpose(img_pil)
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

def alinhar_gabarito(imagem):
    """Detecta as âncoras e corrige a perspectiva para um padrão fixo de 800x1100"""
    gray = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
    # Filtro focado em objetos muito pretos (âncoras digitais)
    _, thresh = cv2.threshold(gray, 80, 255, cv2.THRESH_BINARY_INV)
    contornos, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    centros = []
    img_diag = imagem.copy()

    for c in contornos:
        area = cv2.contourArea(c)
        if 400 < area < 10000:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            if len(approx) == 4:
                M = cv2.moments(c)
                if M["m00"] != 0:
                    cX, cY = int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])
                    centros.append([cX, cY])
                    cv2.drawContours(img_diag, [approx], -1, (0, 0, 255), 3)

    if len(centros) >= 4:
        pts = np.array(centros[:4], dtype="float32")
        s = pts.sum(axis=1)
        diff = np.diff(pts, axis=1)
        rect = np.zeros((4, 2), dtype="float32")
        rect[0], rect[2] = pts[np.argmin(s)], pts[np.argmax(s)]
        rect[1], rect[3] = pts[np.argmin(diff)], pts[np.argmax(diff)]

        dst = np.array([[0,0], [800,0], [800,1100], [0,1100]], dtype="float32")
        M = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(imagem, M, (800, 1100)), img_diag
    return None, img_diag

def extrair_dados(alinhada, gab_raiz=None):
    gray = cv2.cvtColor(alinhada, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    
    res = {"respostas": {}, "frequencia": ""}
    img_vis = alinhada.copy()

    # --- FREQUÊNCIA (Padrão 00-99) ---
    colunas_freq = [("D", 124), ("U", 157)] # Coordenadas X recalibradas
    freq_lida = ""
    for nome, x_base in colunas_freq:
        votos = []
        for i in range(10):
            y = 285 + (i * 24.5)
            roi = thresh[int(y):int(y+16), x_base:x_base+16]
            votos.append(cv2.countNonZero(roi))
            cv2.circle(img_vis, (x_base+8, int(y+8)), 4, (255, 0, 0), 1) # Pontos de busca
        
        idx = np.argmax(votos)
        if votos[idx] > 70:
            freq_lida += str(idx)
            cv2.circle(img_vis, (x_base+8, int(285+(idx*24.5)+8)), 8, (255, 0, 0), -1)
        else:
            freq_lida += "0" # Assume 0 se não houver marcação
    res["frequencia"] = freq_lida

    # --- QUESTÕES (52 Itens) ---
    blocos = [
        {"x": 208, "y": 454, "s": 1},  {"x": 421, "y": 454, "s": 14},
        {"x": 208, "y": 794, "s": 27}, {"x": 421, "y": 794, "s": 40}
    ]
    
    for b in blocos:
        for i in range(13):
            q_num = b["s"] + i
            y_q = int(b["y"] + (i * 24.8))
            pixels = []
            for j in range(4):
                x_q = b["x"] + (j * 33.2)
                roi = thresh[y_q:y_q+16, int(x_q):int(x_q+16)]
                pixels.append(cv2.countNonZero(roi))
            
            idx_a = np.argmax(pixels)
            marcou = max(pixels) > 75
            res["respostas"][q_num] = ["A", "B", "C", "D"][idx_a] if marcou else "."

            if marcou:
                cv2.circle(img_vis, (int(b["x"]+(idx_a*33.2)+8), y_q+8), 10, (0, 255, 0), 2)
            if gab_raiz and q_num in gab_raiz:
                idx_c = ["A", "B", "C", "D"].index(gab_raiz[q_num])
                cv2.circle(img_vis, (int(b["x"]+(idx_c*33.2)+8), y_q+8), 3, (0, 0, 255), -1)

    return res, img_vis
