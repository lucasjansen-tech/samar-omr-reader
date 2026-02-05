from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from layout_samar import ConfiguracaoProva

def desenhar_ancoras(c, conf: ConfiguracaoProva):
    """Desenha as 4 âncoras de calibração"""
    c.setFillColor(colors.black)
    s = conf.ANCORA_SIZE
    w, h = conf.PAGE_W, conf.PAGE_H
    m = conf.MARGIN
    
    c.rect(m, h - m - s, s, s, fill=1, stroke=0)
    c.rect(w - m - s, h - m - s, s, s, fill=1, stroke=0)
    c.rect(m, m, s, s, fill=1, stroke=0)
    c.rect(w - m - s, m, s, s, fill=1, stroke=0)

def desenhar_cabecalho(c, conf: ConfiguracaoProva):
    w, h = conf.PAGE_W, conf.PAGE_H
    top_y = h - conf.MARGIN - conf.ANCORA_SIZE - 20
    
    # Títulos
    c.setFillColor(HexColor("#2980b9")) # Azul Oficial
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(w/2, top_y, conf.titulo_prova.upper())
    
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 10)
    c.drawCentredString(w/2, top_y - 15, conf.subtitulo)
    
    # Caixa de Dados (Sem CRE, com TURNO)
    box_start_y = top_y - 45
    line_height = 25
    
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    c.setFont("Helvetica-Bold", 9)
    
    # Linha 1: ESCOLA e TURNO
    y1 = box_start_y
    c.drawString(conf.MARGIN + 30, y1, "ESCOLA:")
    c.line(conf.MARGIN + 80, y1 - 2, w - 150, y1 - 2)
    
    c.drawString(w - 140, y1, "TURNO:")
    c.line(w - 95, y1 - 2, w - conf.MARGIN - 30, y1 - 2)
    
    # Linha 2: ALUNO e TURMA
    y2 = y1 - line_height
    c.drawString(conf.MARGIN + 30, y2, "ALUNO:")
    c.line(conf.MARGIN + 80, y2 - 2, w - 150, y2 - 2)
    
    c.drawString(w - 140, y2, "TURMA:")
    c.line(w - 95, y2 - 2, w - conf.MARGIN - 30, y2 - 2)
    
    # Linha 3: PROFESSOR e DATA
    y3 = y2 - line_height
    c.drawString(conf.MARGIN + 30, y3, "PROF.:")
    c.line(conf.MARGIN + 80, y3 - 2, w - 150, y3 - 2)
    
    c.drawString(w - 140, y3, "DATA:")
    c.drawString(w - 100, y3, "___/___/______")

def desenhar_grade(c, conf: ConfiguracaoProva):
    # Frequência
    if conf.tem_frequencia:
        # Borda Azul
        c.setStrokeColor(HexColor("#2980b9"))
        c.setLineWidth(1)
        c.rect(conf.FREQ_X - 5, conf.GRID_START_Y - 210, 50, 230, stroke=1, fill=0)
        
        # Título Laranja
        c.setFillColor(HexColor("#e67e22"))
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(conf.FREQ_X + 20, conf.GRID_START_Y + 10, "FREQ.")
        
        c.setFillColor(colors.black)
        for col_idx, label in enumerate(["D", "U"]):
            x = conf.FREQ_X + 10 + (col_idx * 25)
            c.setFont("Helvetica-Bold", 11)
            c.drawCentredString(x, conf.GRID_START_Y - 5, label)
            
            for i in range(10):
                y = conf.GRID_START_Y - 25 - (i * 18)
                c.circle(x, y + 3, 7, stroke=1, fill=0)
                c.setFont("Helvetica", 7)
                c.drawCentredString(x, y + 0.5, str(i))

    # Blocos de Questões
    current_x = conf.GRID_X_START
    
    for bloco in conf.blocos:
        c.setFillColor(HexColor(bloco.cor_hex))
        c.setStrokeColor(HexColor(bloco.cor_hex))
        
        # Cabeçalho do Bloco
        c.roundRect(current_x, conf.GRID_START_Y + 5, 100, 22, 4, fill=1, stroke=0)
        
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(current_x + 50, conf.GRID_START_Y + 12, bloco.titulo)
        
        # Componente Curricular
        c.setFillColor(HexColor(bloco.cor_hex))
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(current_x + 50, conf.GRID_START_Y - 5, bloco.componente.upper())
        
        # Bolinhas
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

def gerar_pdf(conf: ConfiguracaoProva, filename):
    c = canvas.Canvas(filename, pagesize=A4)
    desenhar_ancoras(c, conf)
    desenhar_cabecalho(c, conf)
    desenhar_grade(c, conf)
    c.save()
    return filename
