from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from layout_samar import ConfiguracaoProva
from pdf2image import convert_from_path
import os

def desenhar_layout_grid(c, conf: ConfiguracaoProva):
    W, H = A4
    m = W * conf.MARGIN_PCT
    s = 30
    
    # Âncoras
    c.setFillColor(colors.black)
    c.rect(m, H-m-s, s, s, fill=1, stroke=0)
    c.rect(W-m-s, H-m-s, s, s, fill=1, stroke=0)
    c.rect(m, m, s, s, fill=1, stroke=0)
    c.rect(W-m-s, m, s, s, fill=1, stroke=0)
    
    # Cabeçalho
    c.setFillColor(HexColor("#2980b9"))
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(W/2, H - 50, conf.titulo_prova)
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 12)
    c.drawCentredString(W/2, H - 70, conf.subtitulo)
    
    c.setStrokeColor(colors.black); c.setLineWidth(0.5); c.setFont("Helvetica-Bold", 9)
    y = H - 110
    c.drawString(m, y, "UNIDADE DE ENSINO:"); c.line(m+100, y-2, W-m, y-2)
    y -= 25
    c.drawString(m, y, "ANO:"); c.line(m+30, y-2, m+150, y-2)
    c.drawString(m+160, y, "TURMA:"); c.line(m+200, y-2, m+300, y-2)
    c.drawString(m+310, y, "TURNO:"); c.line(m+350, y-2, W-m, y-2)
    y -= 25
    c.drawString(m, y, "ALUNO:"); c.line(m+40, y-2, W-m, y-2)
    
    # Instruções
    y -= 35
    c.setStrokeColor(HexColor("#e67e22"))
    c.rect(m, y-10, W-(2*m), 25, stroke=1, fill=0)
    c.setFillColor(colors.black); c.setFont("Helvetica", 8)
    c.drawString(m+10, y+2, "INSTRUÇÕES: 1. Use caneta azul ou preta. 2. Preencha totalmente a bolinha. 3. Não rasure.")
    
    for g in conf.grids:
        x1 = g.x_start * W
        w_g = (g.x_end - g.x_start) * W
        y_top = H - (g.y_start * H)
        h_g = (g.y_end - g.y_start) * H
        
        c.setFillColor(HexColor(g.cor_hex))
        c.roundRect(x1, y_top + 45, w_g, 20, 4, fill=1, stroke=0)
        c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(x1 + w_g/2, y_top + 51, g.titulo)
        
        if g.texto_extra:
            c.setFillColor(HexColor(g.cor_hex)); c.setFont("Helvetica-Bold", 7)
            c.drawCentredString(x1 + w_g/2, y_top + 32, g.texto_extra)
        
        cell_h = h_g / g.rows
        cell_w = w_g / g.cols
        c.setFillColor(colors.black); c.setStrokeColor(colors.black)
        
        if g.labels:
            for i, lbl in enumerate(g.labels):
                cx = x1 + (i * cell_w) + (cell_w/2)
                c.setFont("Helvetica-Bold", 9)
                c.drawCentredString(cx, y_top + 12, lbl)

        for r in range(g.rows):
            cy = y_top - (r * cell_h) - (cell_h/2)
            y_box_bot = y_top - ((r+1) * cell_h)
            
            c.setStrokeColor(colors.lightgrey); c.setLineWidth(0.5)
            c.rect(x1, y_box_bot, w_g, cell_h, stroke=1, fill=0)
            
            c.setFillColor(colors.black)
            if g.questao_inicial > 0:
                c.setFont("Helvetica-Bold", 9)
                c.drawRightString(x1 - 5, cy - 3, f"{g.questao_inicial+r:02d}")
            elif g.labels == ["D", "U"]:
                c.setFont("Helvetica", 9)
                c.drawRightString(x1 - 5, cy - 3, str(r))

            for col in range(g.cols):
                cx = x1 + (col * cell_w) + (cell_w/2)
                c.setStrokeColor(colors.black); c.setLineWidth(1)
                c.circle(cx, cy, 7, stroke=1, fill=0)
                if g.questao_inicial > 0:
                    c.setFont("Helvetica", 6)
                    c.drawCentredString(cx, cy - 2, g.labels[col])

def gerar_pdf(conf, filename):
    c = canvas.Canvas(filename, pagesize=A4)
    desenhar_layout_grid(c, conf)
    c.save()
    return filename

def gerar_imagem_a4(conf, filename_saida, formato="png"):
    temp_pdf = "temp_gabarito.pdf"
    gerar_pdf(conf, temp_pdf)
    try:
        imagens = convert_from_path(temp_pdf, dpi=300)
        if imagens:
            img = imagens[0]
            img.save(filename_saida, formato.upper())
            if os.path.exists(temp_pdf): os.remove(temp_pdf)
            return filename_saida
    except: return None
