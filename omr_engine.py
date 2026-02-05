import cv2
import numpy as np
from PIL import Image, ImageOps

def tratar_entrada(img_pil):
    img_pil = ImageOps.exif_transpose(img_pil)
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

def alinhar_gabarito(imagem):
    gray = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
    
    contornos, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    centros = []
    img_diag = imagem.copy()

    for c in contornos:
        area = cv2.contourArea(c)
        if 500 < area < 15000:
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

def extrair_dados(alinhada, gab_oficial=None):
    gray = cv2.cvtColor(alinhada, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    
    res = {"respostas": {}, "frequencia": ""}
    img_vis = alinhada.copy()

    # --- LÓGICA DE FREQUÊNCIA (00-99) ---
    # Coordenadas ajustadas para o padrão observado na imagem de auditoria
    colunas_freq = [("D", 58), ("U", 95)]
    resultado_freq = []

    for nome, x_base in colunas_freq:
        votos = []
        for i in range(10):
            y = 255 + (i * 24)
            roi = thresh[y:y+18, x_base:x_base+18]
            votos.append(cv2.countNonZero(roi))
            # Círculos azuis para onde o sensor está "olhando" na frequência
            cv2.circle(img_vis, (x_base+9, y+9), 4, (255, 0, 0), 1)
        
        # Se o máximo de pixels for muito baixo, considera 0 (não marcado)
        if max(votos) < 80:
            resultado_freq.append("0")
        else:
            idx = np.argmax(votos)
            resultado_freq.append(str(idx))
            # Feedback visual da marcação detectada na frequência
            cv2.circle(img_vis, (x_base+9, 255+(idx*24)+9), 8, (255, 0, 0), -1)

    res["frequencia"] = "".join(resultado_freq)

    # --- LÓGICA DE QUESTÕES ---
    blocos = [{"x": 140, "y": 422, "s": 1}, {"x": 372, "y": 422, "s": 14}, 
              {"x": 140, "y": 758, "s": 27}, {"x": 372, "y": 758, "s": 40}]
    
    for b in blocos:
        for i in range(13):
            q_num = b["s"] + i
            y = b["y"] + (i * 25)
            pixels = []
            for j in range(4):
                x = b["x"] + (j * 35)
                pixels.append(cv2.countNonZero(thresh[y:y+18, x:x+18]))
            
            idx_aluno = np.argmax(pixels)
            marcou = max(pixels) > 80
            letra_aluno = ["A", "B", "C", "D"][idx_aluno] if marcou else "N/A"
            res["respostas"][q_num] = letra_aluno

            # FEEDBACK VISUAL SOBRE AS RESPOSTAS
            for j in range(4):
                x = b["x"] + (j * 35)
                # Se for a resposta do aluno, desenha em VERDE
                if marcou and j == idx_aluno:
                    cv2.circle(img_vis, (x+9, y+9), 9, (0, 255, 0), 2)
                
                # Se tiver gabarito oficial e for a correta, desenha um ponto central
                if gab_oficial and j == ["A","B","C","D"].index(gab_oficial[q_num]):
                    cv2.circle(img_vis, (x+9, y+9), 4, (0, 0, 255), -1)

    return res, img_vis
