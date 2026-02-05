import cv2
import numpy as np
from PIL import Image, ImageOps

def tratar_entrada(img_pil):
    """Corrige orientação e converte para formato que o OpenCV entende"""
    img_pil = ImageOps.exif_transpose(img_pil)
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)

def alinhar_gabarito(imagem):
    """Detecta as 4 âncoras pretas e corrige a perspectiva para 800x1100"""
    gray = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 75, 255, cv2.THRESH_BINARY_INV)
    contornos, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    centros = []
    for c in contornos:
        area = cv2.contourArea(c)
        if 400 < area < 8000:
            M = cv2.moments(c)
            if M["m00"] != 0:
                centros.append([int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])])
    
    if len(centros) == 4:
        pts = np.array(centros, dtype="float32")
        s = pts.sum(axis=1)
        diff = np.diff(pts, axis=1)
        rect = np.zeros((4, 2), dtype="float32")
        rect[0], rect[2] = pts[np.argmin(s)], pts[np.argmax(s)]
        rect[1], rect[3] = pts[np.argmin(diff)], pts[np.argmax(diff)]
        dst = np.array([[0,0], [799,0], [799,1099], [0,1099]], dtype="float32")
        M = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(imagem, M, (800, 1100))
    return None

def extrair_respostas(imagem_alinhada):
    """Varre as coordenadas e identifica o preenchimento das questões"""
    gray = cv2.cvtColor(imagem_alinhada, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    
    respostas = {}
    # Coordenadas baseadas no seu layout de página única calibrado
    blocos = {
        "LP1": {"x": 138, "y": 420, "start": 1},
        "LP2": {"x": 368, "y": 420, "start": 14},
        "MT1": {"x": 138, "y": 755, "start": 27},
        "MT2": {"x": 368, "y": 755, "start": 40}
    }
    for _, b in blocos.items():
        for i in range(13):
            q_idx = b["start"] + i
            y = b["y"] + (i * 25)
            pixels = []
            for j in range(4): # A, B, C, D
                x = b["x"] + (j * 35)
                roi = thresh[y:y+18, x:x+18]
                pixels.append(cv2.countNonZero(roi))
            respostas[q_idx] = ["A", "B", "C", "D"][np.argmax(pixels)] if max(pixels) > 120 else "."
    return respostas