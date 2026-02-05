# gerador.py
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from layout_samar import ConfiguracaoProva

def desenhar_ancoras(c, conf: ConfiguracaoProva):
    """Desenha os 4 quadrados pretos fundamentais"""
    c.setFillColor(colors.black)
    s = conf.ANCORA_SIZE
    w, h = conf.PAGE_W, conf.PAGE_H
    m = conf.MARGIN
    
    # Top-Left, Top-Right, Bottom-Left, Bottom-Right
    c.rect(m, h - m - s, s, s, fill=1, stroke=0)
    c.rect(w - m - s, h - m - s, s, s, fill=1, stroke=0)
    c.rect(m, m, s, s, fill=1, stroke=0)
    c.rect(w - m - s, m, s, s, fill=1, stroke=0)

def desenhar_cabecalho(c, conf: ConfiguracaoProva):
    """Área livre para logos e textos"""
    w, h = conf.PAGE_W, conf.PAGE_H
    top = h - conf.MARGIN - conf.ANCORA_SIZE - 10
    
    # Títulos
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w/2, top - 20, conf.titulo_prova)
    c.setFont("Helvetica", 10)
    c.drawCentredString(w/2, top - 35, conf.subtitulo)
    
    # Caixa de Identificação
    c.rect(conf.MARGIN + 30, top - 80, 300, 25, stroke=1, fill=0)
    c.drawString(conf.MARGIN + 35, top - 70, "NOME:")
    
    c.rect(w - conf.MARGIN - 150, top - 80, 120, 25, stroke=1, fill=0)
    c.drawString(w - conf.MARGIN - 145, top - 70, "DATA:")
    
    # Orientações (Pequenas)
    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(w/2, top - 100, "Orientações: Preencha completamente a bolinha com caneta azul ou preta.")

def desenhar_grade(c, conf: ConfiguracaoProva):
    # --- Frequência ---
    if conf.tem_frequencia:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(conf.FREQ_X, conf.FREQ_Y_START + 15, "FREQ")
        
        for col_idx, label in enumerate(["D", "U"]):
            x = conf.FREQ_X + (col_idx * 25)
            c.drawString(x + 6, conf.FREQ_Y_START + 2, label)
            for i in range(10):
                y = conf.FREQ_Y_START - 15 - (i * 18) # Passo de 18pts
                c.circle(x + 10, y + 5, 7, stroke=1, fill=0)
                c.setFont("Helvetica", 7)
                c.drawCentredString(x + 10, y + 2.5, str(i))
                
    # --- Questões ---
    current_x = conf.GRID_X_START
    
    for bloco in conf.blocos:
        # Título do Bloco
        c.setFillColor(colors.lightgrey)
        c.rect(current_x, conf.GRID_START_Y + 10, 90, 15, fill=1, stroke=0)
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(current_x + 45, conf.GRID_START_Y + 14, bloco.titulo)
        
        for i in range(bloco.quantidade):
            q_num = bloco.questao_inicial + i
            y = conf.GRID_START_Y - 15 - (i * 20) # Passo de 20pts
            
            c.setFont("Helvetica-Bold", 9)
            c.drawString(current_x, y, f"{q_num:02d}")
            
            for j, letra in enumerate(["A", "B", "C", "D"]):
                bx = current_x + 25 + (j * 18)
                c.circle(bx, y + 3, 7, stroke=1, fill=0)
                c.setFont("Helvetica", 7)
                c.drawCentredString(bx, y + 1, letra)
                
        current_x += conf.GRID_COL_W

def gerar_pdf(conf: ConfiguracaoProva, filename):
    c = canvas.Canvas(filename, pagesize=A4)
    desenhar_ancoras(c, conf)
    desenhar_cabecalho(c, conf)
    desenhar_grade(c, conf)
    c.save()
    return filename
