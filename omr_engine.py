import cv2
import numpy as np
from PIL import Image, ImageOps

def tratar_entrada(img_pil):
    img_pil = ImageOps.exif_transpose(img_pil)
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

def alinhar_gabarito(imagem):
    gray = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
    # Blur leve para remover ruído digital
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
    
    contornos, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    centros = []
    
    img_copia = imagem.copy() # Para feedback visual

    for c in contornos:
        area = cv2.contourArea(c)
        if 300 < area < 10000:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            if len(approx) == 4:
                M = cv2.moments(c)
                if M["m00"] != 0:
                    cX = int(M["m10"] / M["m00"])
                    cY = int(M["m01"] / M["m00"])
                    centros.append([cX, cY])
                    # Desenha retângulo de diagnóstico
                    cv2.drawContours(img_copia, [approx], -1, (0, 0, 255), 3)

    if len(centros) >= 4:
        # Ordena: Top-Left, Top-Right, Bottom-Right, Bottom-Left
        pts = np.array(centros[:4], dtype="float32")
        s = pts.sum(axis=1)
        diff = np.diff(pts, axis=1)
        rect = np.zeros((4, 2), dtype="float32")
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]

        dst = np.array([[0,0], [800,0], [800,1100], [0,1100]], dtype="float32")
        M = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(imagem, M, (800, 1100)), img_copia
    return None, img_copia

def extrair_dados(alinhada, gab_oficial=None):
    gray = cv2.cvtColor(alinhada, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    
    res = {"respostas": {}, "frequencia": ""}
    img_overlay = alinhada.copy()

    # 1. FREQUÊNCIA (D e U)
    for col_nome, x_base in [("D", 58), ("U", 95)]:
        votos = []
        for i in range(10):
            y = 255 + (i * 24)
            roi = thresh[y:y+18, x_base:x_base+18]
            votos.append(cv2.countNonZero(roi))
        v_lido = str(np.argmax(votos)) if max(votos) > 70 else "?"
        res["frequencia"] += v_lido
        # Visual Freq: Azul para o detectado
        if v_lido != "?":
            y_marcado = 255 + (int(v_lido) * 24)
            cv2.circle(img_overlay, (x_base+9, y_marcado+9), 8, (255, 0, 0), 2)

    # 2. QUESTÕES (Blocos 1-4)
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
            
            idx_marcado = np.argmax(pixels)
            letra_aluno = ["A", "B", "C", "D"][idx_marcado] if max(pixels) > 80 else "N/A"
            res["respostas"][q_num] = letra_aluno

            # FEEDBACK VISUAL:
            for j in range(4):
                x = b["x"] + (j * 35)
                cor = (200, 200, 200) # Cinza padrão
                espessura = 1
                
                if letra_aluno != "N/A" and j == idx_marcado:
                    # Se aluno marcou, desenha círculo
                    cor = (0, 255, 0) # Verde para marcação do aluno
                    espessura = 2
                
                # Se tiver gabarito oficial e for erro, destaca em vermelho
                if gab_oficial and letra_aluno != gab_oficial.get(q_num) and j == ["A","B","C","D"].index(gab_oficial[q_num]):
                    cor = (0, 0, 255) # Resposta correta em Vermelho
                    espessura = 3

                cv2.circle(img_overlay, (x+9, y+9), 7, cor, espessura)
                
    return res, img_overlay
