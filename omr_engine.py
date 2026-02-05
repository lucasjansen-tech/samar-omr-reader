import cv2
import numpy as np
from PIL import Image, ImageOps

def tratar_entrada(img_pil):
    img_pil = ImageOps.exif_transpose(img_pil)
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

def alinhar_gabarito(imagem):
    """Localiza as 4 âncoras pretas e corrige a perspectiva."""
    gray = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
    # Ajuste de binarização para detectar âncoras digitais ou escaneadas
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
    contornos, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    centros = []
    for c in contornos:
        area = cv2.contourArea(c)
        # Filtro de área mais flexível para âncoras digitais
        if 200 < area < 15000:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.04 * peri, True)
            if len(approx) == 4: # Procura por formas quadrangulares
                M = cv2.moments(c)
                if M["m00"] != 0:
                    cX = int(M["m10"] / M["m00"])
                    cY = int(M["m01"] / M["m00"])
                    centros.append([cX, cY])
    
    # Se encontrar mais ou menos que 4, tentamos pegar os 4 mais distantes
    if len(centros) >= 4:
        pts = np.array(centros[:4], dtype="float32")
        s = pts.sum(axis=1)
        diff = np.diff(pts, axis=1)
        rect = np.zeros((4, 2), dtype="float32")
        rect[0] = pts[np.argmin(s)]    # Top-left
        rect[2] = pts[np.argmax(s)]    # Bottom-right
        rect[1] = pts[np.argmin(diff)] # Top-right
        rect[3] = pts[np.argmax(diff)] # Bottom-left

        dst = np.array([[0,0], [799,0], [799,1099], [0,1099]], dtype="float32")
        M = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(imagem, M, (800, 1100))
    return None

def extrair_dados(alinhada):
    """Extrai frequência e respostas."""
    gray = cv2.cvtColor(alinhada, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    
    res = {"respostas": {}, "frequencia": ""}
    
    # Frequência: D e U
    freq_map = {"D": 55, "U": 90}
    val_f = ""
    for k, x_base in freq_map.items():
        v_col = []
        for i in range(10):
            y = 252 + (i * 24)
            roi = thresh[y:y+18, x_base:x_base+18]
            v_col.append(cv2.countNonZero(roi))
        val_f += str(np.argmax(v_col)) if max(v_col) > 50 else "?"
    res["frequencia"] = val_f

    # Questões: Blocos 1 a 4
    blocos = [
        {"x": 138, "y": 420, "start": 1},  # LP1
        {"x": 368, "y": 420, "start": 14}, # LP2
        {"x": 138, "y": 755, "start": 27}, # MT1
        {"x": 368, "y": 755, "start": 40}  # MT2
    ]
    
    for b in blocos:
        for i in range(13):
            q_idx = b["start"] + i
            y_q = b["y"] + (i * 25)
            p_alt = []
            for j in range(4): # A, B, C, D
                x_q = b["x"] + (j * 35)
                roi = thresh[y_q:y_q+18, x_q:x_q+18]
                p_alt.append(cv2.countNonZero(roi))
                # Feedback visual no PDF
                cv2.circle(alinhada, (x_q+9, y_q+9), 6, (0, 255, 0), 1)
            
            if max(p_alt) > 80:
                res["respostas"][q_idx] = ["A", "B", "C", "D"][np.argmax(p_alt)]
            else:
                res["respostas"][q_idx] = "."
                
    return res, alinhada
