import cv2
import numpy as np
from PIL import Image, ImageOps

def tratar_entrada(img_pil):
    img_pil = ImageOps.exif_transpose(img_pil)
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

def alinhar_gabarito(imagem):
    gray = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
    # Binarização mais forte para PDF digital
    _, thresh = cv2.threshold(gray, 170, 255, cv2.THRESH_BINARY_INV)
    contornos, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    centros = []
    for c in contornos:
        area = cv2.contourArea(c)
        if 200 < area < 15000:
            M = cv2.moments(c)
            if M["m00"] != 0:
                centros.append([int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])])
    
    if len(centros) >= 4:
        pts = np.array(centros[:4], dtype="float32")
        s = pts.sum(axis=1)
        diff = np.diff(pts, axis=1)
        rect = np.zeros((4, 2), dtype="float32")
        rect[0] = pts[np.argmin(s)]       # Top-left
        rect[2] = pts[np.argmax(s)]       # Bottom-right
        rect[1] = pts[np.argmin(diff)]    # Top-right
        rect[3] = pts[np.argmax(diff)]    # Bottom-left

        dst = np.array([[0,0], [800,0], [800,1100], [0,1100]], dtype="float32")
        M = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(imagem, M, (800, 1100))
    return None

def extrair_dados(alinhada):
    gray = cv2.cvtColor(alinhada, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    
    res = {"respostas": {}, "frequencia": ""}
    
    # 1. FREQUÊNCIA (D e U) - Coordenadas Ajustadas
    for col_nome, x_base in [("D", 58), ("U", 95)]:
        votos = []
        for i in range(10):
            y = 255 + (i * 24)
            roi = thresh[y:y+18, x_base:x_base+18]
            votos.append(cv2.countNonZero(roi))
            # Desenha ponto visual de leitura
            cv2.circle(alinhada, (x_base+9, y+9), 5, (255, 0, 0), -1) 
        res["frequencia"] += str(np.argmax(votos)) if max(votos) > 80 else "?"

    # 2. QUESTÕES (Blocos 1-4)
    blocos = [{"x": 140, "y": 422, "s": 1}, {"x": 372, "y": 422, "s": 14}, 
              {"x": 140, "y": 758, "s": 27}, {"x": 372, "y": 758, "s": 40}]
    
    for b in blocos:
        for i in range(13):
            q_num = b["s"] + i
            y = b["y"] + (i * 25)
            pixels = []
            for j in range(4): # A, B, C, D
                x = b["x"] + (j * 35)
                roi = thresh[y:y+18, x:x+18]
                pixels.append(cv2.countNonZero(roi))
                # Círculo verde para indicar onde o sistema está "olhando"
                cv2.circle(alinhada, (x+9, y+9), 7, (0, 255, 0), 1)
            
            if max(pixels) > 90:
                res["respostas"][q_num] = ["A", "B", "C", "D"][np.argmax(pixels)]
            else:
                res["respostas"][q_num] = "N/A"
                
    return res, alinhada
