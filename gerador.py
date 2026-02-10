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
    
    # Desenha as 4 âncoras
    # Top-Left, Top-Right
    c.rect(m, h - m - s, s, s, fill=1, stroke=0)
    c.rect(w - m - s, h - m - s, s, s, fill=1, stroke=0)
    # Bottom-Left, Bottom-Right
    c.rect(m, m, s, s, fill=1, stroke=0)
    c.rect(w - m - s, m, s, s, fill=1, stroke=0)

def desenhar_cabecalho(c, conf: ConfiguracaoProva):
    w, h = conf.PAGE_W, conf.PAGE_H
    top_y = h - conf.MARGIN - conf.ANCORA_SIZE - 20
    
    # Títulos
    c.setFillColor(HexColor("#2980b9"))
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(w/2, top_y, conf.titulo_prova.upper())
    
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 11)
    c.drawCentredString(w/2, top_y - 18, conf.subtitulo)
    
    # --- NOVO CABEÇALHO COMPLETO ---
    box_y = top_y - 50
    lh = 28 
    
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    c.setFont("Helvetica-Bold", 9)
    
    # L1: UNIDADE DE ENSINO
    y = box_y
    c.drawString(conf.MARGIN + 20, y, "UNIDADE DE ENSINO:")
    c.line(conf.MARGIN + 125, y-2, w - conf.MARGIN - 20, y-2)
    
    # L2: ANO | TURMA | TURNO
    y -= lh
    c.drawString(conf.MARGIN + 20, y, "ANO DE ENSINO:")
    c.line(conf.MARGIN + 105, y-2, conf.MARGIN + 200, y-2)
    
    c.drawString(conf.MARGIN + 220, y, "TURMA:")
    c.line(conf.MARGIN + 260, y-2, conf.MARGIN + 340, y-2)
    
    c.drawString(w - 150, y, "TURNO:")
    c.line(w - 110, y-2, w - conf.MARGIN - 20, y-2)
    
    # L3: NOME
    y -= lh
    c.drawString(conf.MARGIN + 20, y, "NOME DO ALUNO:")
    c.line(conf.MARGIN + 110, y-2, w - conf.MARGIN - 20, y-2)

def desenhar_grade(c, conf: ConfiguracaoProva):
    start_y = conf.GRID_START_Y
    
    # Frequência
    if conf.tem_frequencia:
        box_w = 54
        box_x = conf.FREQ_X
        
        c.setStrokeColor(HexColor("#2980b9"))
        c.setLineWidth(1)
        c.rect(box_x, start_y - 215, box_w, 235, stroke=1, fill=0)
        
        center_x = box_x + (box_w / 2)
        c.setFillColor(HexColor("#e67e22"))
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(center_x, start_y + 10, "FREQ.")
        
        c.setFillColor(colors.black)
        offset_x = 12
        for col_idx, label in enumerate(["D", "U"]):
            col_center_x = center_x - offset_x if col_idx == 0 else center_x + offset_x
            c.setFont("Helvetica-Bold", 11)
            c.drawCentredString(col_center_x, start_y - 5, label)
            for i in range(10):
                y = start_y - 25 - (i * 18)
                c.setStrokeColor(colors.black)
                c.circle(col_center_x, y + 3, 7, stroke=1, fill=0)
                c.setFont("Helvetica", 8)
                c.drawCentredString(col_center_x, y + 0.5, str(i))

    # Questões
    current_x = conf.GRID_X_START
    for bloco in conf.blocos:
        c.setFillColor(HexColor(bloco.cor_hex))
        c.setStrokeColor(HexColor(bloco.cor_hex))
        
        c.roundRect(current_x, start_y + 5, 105, 22, 4, fill=1, stroke=0)
        
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(current_x + 52, start_y + 12, bloco.titulo)
        
        c.setFillColor(HexColor(bloco.cor_hex))
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(current_x + 52, start_y - 6, bloco.componente.upper())
        
        c.setFillColor(colors.black)
        c.setStrokeColor(colors.black)
        
        for i in range(bloco.quantidade):
            q_num = bloco.questao_inicial + i
            y = start_y - 25 - (i * 20)
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
