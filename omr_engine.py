import cv2
import numpy as np
from PIL import Image, ImageOps

def tratar_entrada(img_pil):
    img_pil = ImageOps.exif_transpose(img_pil)
    # Aumenta o contraste antes de processar
    img = np.array(img_pil)
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    return img

def ordenar_pontos(pts):
    # Ordena coordenadas: Top-Left, Top-Right, Bottom-Right, Bottom-Left
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def alinhar_gabarito(imagem):
    # Redimensiona para processamento (mantendo proporção)
    ratio = imagem.shape[0] / 800.0
    orig = imagem.copy()
    
    # Detecção de Bordas (Canny é melhor que Threshold para formas geométricas)
    gray = cv2.cvtColor(imagem, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 75, 200)

    # Encontra contornos
    cnts, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:5] # Pega os 5 maiores

    screenCnt = None
    
    # Procura por polígono de 4 lados (as âncoras externas ou a própria folha)
    for c in cnts:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            screenCnt = approx
            break

    # Se não achou a folha inteira, tenta achar as 4 âncoras individuais
    if screenCnt is None:
        # Estratégia B: Achar 4 componentes quadrados distantes
        # (Simplificado para focar no contorno da página se for PDF digital)
        h, w = imagem.shape[:2]
        screenCnt = np.array([[0,0], [w,0], [w,h], [0,h]]) # Fallback para imagem cheia

    # Transformação de Perspectiva
    warped = imagem
    if screenCnt is not None:
        pts = screenCnt.reshape(4, 2)
        rect = ordenar_pontos(pts)
        
        # Define tamanho padrão A4 (800 x 1130)
        maxWidth = 800
        maxHeight = 1130
        
        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]], dtype="float32")
            
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(orig, M, (maxWidth, maxHeight))

    return warped, edged # Retorna edged para debug se precisar

def extrair_dados(imagem_warped, gabarito_oficial=None):
    # Trabalhamos sempre com 800x1130
    h, w = imagem_warped.shape[:2]
    
    # Pre-processamento para leitura de marcas
    gray = cv2.cvtColor(imagem_warped, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    
    # Imagem de Debug (Visualização)
    debug_img = imagem_warped.copy()
    
    res = {"respostas": {}, "frequencia": ""}
    
    # --- FUNÇÃO AUXILIAR DE GRID ---
    def ler_grade(start_x, start_y, rows, cols, step_x, step_y, debug_color=(255, 0, 0)):
        matriz_leitura = []
        for r in range(rows):
            linha_votos = []
            for c in range(cols):
                cx = int(start_x + (c * step_x))
                cy = int(start_y + (r * step_y))
                
                # Região de Interesse (ROI)
                cv2.circle(debug_img, (cx, cy), 3, (200, 200, 200), 1) # Guia visual
                roi = thresh[cy-10:cy+10, cx-10:cx+10] # Janela de 20x20px
                pixels = cv2.countNonZero(roi)
                linha_votos.append(pixels)
                
                # Feedback visual (Círculo vazio = onde leu)
                cv2.circle(debug_img, (cx, cy), 10, debug_color, 1)
            matriz_leitura.append(linha_votos)
        return matriz_leitura

    # 1. LEITURA DA FREQUÊNCIA (Colunas D e U)
    # Ajuste Fino: Baseado em 800px de largura
    # D fica aprox em 12% da largura, U em 17%
    f_start_y = int(h * 0.25) # Começa aos 25% da altura
    f_step_y = 25 # Distância vertical entre bolinhas
    
    # Lê Coluna D
    d_vals = ler_grade(98, f_start_y, 10, 1, 0, f_step_y, (255, 100, 0))
    # Lê Coluna U
    u_vals = ler_grade(138, f_start_y, 10, 1, 0, f_step_y, (255, 100, 0))
    
    # Processa Frequência
    def get_digito(matrix):
        flat = [v[0] for v in matrix]
        if max(flat) > 150: # Threshold de pixel
            idx = np.argmax(flat)
            # Pinta de azul o detectado
            cy = int(f_start_y + (idx * f_step_y))
            cx = 98 if matrix == d_vals else 138
            cv2.circle(debug_img, (cx, cy), 10, (255, 0, 0), -1)
            return str(idx)
        return "0"

    res["frequencia"] = get_digito(d_vals) + get_digito(u_vals)

    # 2. LEITURA DAS QUESTÕES (4 Blocos)
    # Configuração dos Blocos (X Inicial, Y Inicial, Questão Inicial)
    # Bloco 1: Q1-13 (Esq) | Bloco 2: Q14-26 (Dir)
    # Bloco 3: Q27-39 (Esq Baixo) | Bloco 4: Q40-52 (Dir Baixo)
    
    q_step_x = 36 # Distância entre A-B-C-D
    q_step_y = 25 # Distância entre Q1-Q2
    
    blocos_config = [
        (185, 452, 1),   # Bloco 1
        (435, 452, 14),  # Bloco 2
        (185, 788, 27),  # Bloco 3
        (435, 788, 40)   # Bloco 4
    ]

    for (bx, by, q_start) in blocos_config:
        # Lê 13 linhas, 4 colunas
        matriz = ler_grade(bx, by, 13, 4, q_step_x, q_step_y, (0, 255, 0))
        
        for i, linha in enumerate(matriz):
            q_num = q_start + i
            if max(linha) > 150: # Se houver marcação
                idx = np.argmax(linha)
                letra = ["A", "B", "C", "D"][idx]
                res["respostas"][q_num] = letra
                
                # Desenha Círculo Verde Preenchido na marcação do aluno
                cx = int(bx + (idx * q_step_x))
                cy = int(by + (i * q_step_y))
                cv2.circle(debug_img, (cx, cy), 10, (0, 255, 0), -1)
                
                # Validação Gabarito (Ponto Vermelho se errou)
                if gabarito_oficial and gabarito_oficial.get(q_num) != letra:
                     idx_correto = ["A", "B", "C", "D"].index(gabarito_oficial[q_num])
                     cx_c = int(bx + (idx_correto * q_step_x))
                     cv2.circle(debug_img, (cx_c, cy), 5, (0, 0, 255), -1)
            else:
                res["respostas"][q_num] = "."

    return res, debug_img
