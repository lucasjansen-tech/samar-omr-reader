from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from layout_samar import ConfiguracaoProva

def desenhar_ancoras(c, conf: ConfiguracaoProva):
    c.setFillColor(colors.black)
    s = conf.ANCORA_SIZE
    w, h = conf.PAGE_W, conf.PAGE_H
    m = conf.MARGIN
    
    # Âncoras agora desenhadas na nova margem segura (mais longe da borda)
    c.rect(m, h - m - s, s, s, fill=1, stroke=0)
    c.rect(w - m - s, h - m - s, s, s, fill=1, stroke=0)
    c.rect(m, m, s, s, fill=1, stroke=0)
    c.rect(w - m - s, m, s, s, fill=1, stroke=0)

def desenhar_cabecalho(c, conf: ConfiguracaoProva):
    w, h = conf.PAGE_W, conf.PAGE_H
    # Topo relativo à nova margem
    top_y = h - conf.MARGIN - conf.ANCORA_SIZE - 20
    
    # Títulos (Configuráveis no layout_samar.py)
    c.setFillColor(HexColor("#2980b9"))
    c.setFont("Helvetica-Bold", 14) # Ajustei fonte para caber títulos longos
    c.drawCentredString(w/2, top_y, conf.titulo_prova.upper())
    
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 10)
    c.drawCentredString(w/2, top_y - 15, conf.subtitulo)
    
    # Dados do Aluno
    box_y = top_y - 45
    line_h = 25
    
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    c.setFont("Helvetica-Bold", 9)
    
    # Linhas de dados
    y = box_y
    c.drawString(conf.MARGIN + 30, y, "ESCOLA:")
    c.line(conf.MARGIN + 80, y-2, w - 160, y-2)
    c.drawString(w - 150, y, "TURNO:")
    c.line(w - 110, y-2, w - conf.MARGIN - 30, y-2)
    
    y -= line_h
    c.drawString(conf.MARGIN + 30, y, "ALUNO:")
    c.line(conf.MARGIN + 80, y-2, w - 160, y-2)
    c.drawString(w - 150, y, "TURMA:")
    c.line(w - 110, y-2, w - conf.MARGIN - 30, y-2)
    
    y -= line_h
    c.drawString(conf.MARGIN + 30, y, "PROF.:")
    c.line(conf.MARGIN + 80, y-2, w - 160, y-2)
    c.drawString(w - 150, y, "DATA:")
    c.drawString(w - 110, y, "___/___/______")

def desenhar_grade(c, conf: ConfiguracaoProva):
    # --- FREQUÊNCIA (CENTRALIZADA) ---
    if conf.tem_frequencia:
        # Dimensões da Caixa
        box_w = 54
        box_h = 230
        box_x = conf.FREQ_X
        box_y = conf.GRID_START_Y - 210
        
        # Borda da caixa
        c.setStrokeColor(HexColor("#2980b9"))
        c.setLineWidth(1)
        c.rect(box_x, box_y, box_w, box_h, stroke=1, fill=0)
        
        # Centro da caixa para alinhar tudo
        center_x = box_x + (box_w / 2)
        
        # Título FREQ
        c.setFillColor(HexColor("#e67e22"))
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(center_x, conf.GRID_START_Y + 10, "FREQ.")
        
        c.setFillColor(colors.black)
        
        # Desenha Colunas (Centralizadas em relação ao meio da caixa)
        # Offset para esquerda e direita do centro
        offset_x = 12 
        
        for col_idx, label in enumerate(["D", "U"]):
            # Se for D (idx 0), subtrai offset. Se for U (idx 1), soma offset.
            col_center_x = center_x - offset_x if col_idx == 0 else center_x + offset_x
            
            c.setFont("Helvetica-Bold", 11)
            c.drawCentredString(col_center_x, conf.GRID_START_Y - 5, label)
            
            for i in range(10):
                y = conf.GRID_START_Y - 25 - (i * 18)
                c.setStrokeColor(colors.black)
                # Círculo centralizado na coluna
                c.circle(col_center_x, y + 3, 7, stroke=1, fill=0)
                c.setFont("Helvetica", 7)
                c.drawCentredString(col_center_x, y + 0.5, str(i))

    # --- QUESTÕES ---
    current_x = conf.GRID_X_START
    
    for bloco in conf.blocos:
        c.setFillColor(HexColor(bloco.cor_hex))
        c.setStrokeColor(HexColor(bloco.cor_hex))
        
        c.roundRect(current_x, conf.GRID_START_Y + 5, 105, 22, 4, fill=1, stroke=0)
        
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(current_x + 52, conf.GRID_START_Y + 12, bloco.titulo)
        
        c.setFillColor(HexColor(bloco.cor_hex))
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(current_x + 52, conf.GRID_START_Y - 6, bloco.componente.upper())
        
        c.setFillColor(colors.black)
        c.setStrokeColor(colors.black)
        
        for i in range(bloco.quantidade):
            q_num = bloco.questao_inicial + i
            y = conf.GRID_START_Y - 25 - (i * 20)
            
            c.setFont("Helvetica-Bold", 9)
            c.drawString(current_x - 5, y, f"{q_num:02d}")
            
            for j, letra in enumerate(["A", "B", "C", "D"]):
                bx = current_x + 20 + (j * 20)
                c.circle(bx, y + 3, 7, stroke=1, fill=0)
                c.setFont("Helvetica", 6)
                c.drawCentredString(bx, y + 1, letra)
                
        current_x += conf.GRID_COL_W

    c.save()
    return filename
