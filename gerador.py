import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from pdf2image import convert_from_path

def gerar_pdf(conf, filename):
    c = canvas.Canvas(filename, pagesize=A4)
    w, h = A4

    # 1. Âncoras do Sistema SAMAR
    m_pct = conf.MARGIN_PCT
    s_px = w * 0.04
    offset = w * m_pct

    c.setFillColorRGB(0, 0, 0)
    c.rect(offset, h - offset - s_px, s_px, s_px, fill=1) # Top-Left
    c.rect(w - offset - s_px, h - offset - s_px, s_px, s_px, fill=1) # Top-Right
    c.rect(offset, offset, s_px, s_px, fill=1) # Bottom-Left
    c.rect(w - offset - s_px, offset, s_px, s_px, fill=1) # Bottom-Right

    # 2. Títulos Oficiais do SAMAR
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w / 2.0, h * 0.88, conf.titulo_prova)
    c.setFont("Helvetica", 12)
    c.drawCentredString(w / 2.0, h * 0.85, conf.subtitulo)

    # 3. Cabeçalho de Identificação (Estável e com espaço)
    c.setFont("Helvetica-Bold", 10)
    
    # Linha 1
    c.drawString(w * 0.1, h * 0.78, "ESCOLA:")
    c.line(w * 0.18, h * 0.78, w * 0.9, h * 0.78)

    # Linha 2
    c.drawString(w * 0.1, h * 0.74, "ALUNO:")
    c.line(w * 0.17, h * 0.74, w * 0.65, h * 0.74)
    c.drawString(w * 0.68, h * 0.74, "TURMA:")
    c.line(w * 0.75, h * 0.74, w * 0.9, h * 0.74)

    # Linha 3
    c.drawString(w * 0.1, h * 0.70, "DATA: ______ / ______ / ________")

    # 4. Desenho dos Grids (Coordenadas Nativas)
    for grid in conf.grids:
        x1 = grid.x_start * w
        x2 = grid.x_end * w
        y1_pdf = h - (grid.y_end * h)
        y2_pdf = h - (grid.y_start * h)

        c.setFillColorRGB(0, 0, 0)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString((x1+x2)/2, y2_pdf + 10, grid.titulo)
        if grid.texto_extra:
            c.setFont("Helvetica", 8)
            c.drawCentredString((x1+x2)/2, y2_pdf + 0, grid.texto_extra)

        cell_w = (x2 - x1) / grid.cols
        cell_h = (y2_pdf - y1_pdf) / grid.rows
        raio = min(cell_w, cell_h) * 0.25

        c.setFont("Helvetica", 8)
        for col in range(grid.cols):
            cx = x1 + (col * cell_w) + (cell_w / 2)
            c.drawCentredString(cx, y2_pdf - 8, grid.labels[col])

        c.setStrokeColorRGB(0.4, 0.4, 0.4)
        for row in range(grid.rows):
            cy = y2_pdf - (row * cell_h) - (cell_h / 2) - 15

            if grid.questao_inicial > 0:
                q_num = grid.questao_inicial + row
                c.setFont("Helvetica-Bold", 8)
                c.drawString(x1 - 15, cy - 3, str(q_num))
            else:
                c.setFont("Helvetica-Bold", 8)
                c.drawString(x1 - 15, cy - 3, str(row))

            c.setLineWidth(1)
            for col in range(grid.cols):
                cx = x1 + (col * cell_w) + (cell_w / 2)
                c.circle(cx, cy, raio, stroke=1, fill=0)

    c.save()

def gerar_imagem_a4(conf, filename, ext):
    pdf_tmp = "temp_gen.pdf"
    gerar_pdf(conf, pdf_tmp)
    try:
        pages = convert_from_path(pdf_tmp, dpi=200)
        if pages:
            if ext.lower() == "png":
                pages[0].save(filename, "PNG")
            else:
                pages[0].save(filename, "JPEG")
            os.remove(pdf_tmp)
            return True
    except Exception as e:
        print(e)
    if os.path.exists(pdf_tmp): os.remove(pdf_tmp)
    return False
