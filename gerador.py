import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from pdf2image import convert_from_path

def gerar_pdf(conf, filename, titulo_custom=None, subtitulo_custom=None, logos=None):
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

    # 2. Inserção de Logos Dinâmicas
    y_logo = h * 0.895
    h_logo = h * 0.05
    w_logo = w * 0.18

    if logos:
        if logos.get('esq'):
            c.drawImage(ImageReader(logos['esq']), w * 0.10, y_logo, width=w_logo, height=h_logo, preserveAspectRatio=True, mask='auto')
        if logos.get('cen'):
            c.drawImage(ImageReader(logos['cen']), w * 0.41, y_logo, width=w_logo, height=h_logo, preserveAspectRatio=True, mask='auto')
        if logos.get('dir'):
            c.drawImage(ImageReader(logos['dir']), w * 0.72, y_logo, width=w_logo, height=h_logo, preserveAspectRatio=True, mask='auto')

    # 3. Títulos Dinâmicos
    texto_titulo = titulo_custom if titulo_custom else conf.titulo_prova
    texto_subtitulo = subtitulo_custom if subtitulo_custom else conf.subtitulo

    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(w / 2.0, h * 0.865, texto_titulo)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(w / 2.0, h * 0.850, texto_subtitulo)

    # 4. Cabeçalho Visual (Idêntico ao SAMAR original)
    c.setLineWidth(1)
    c.rect(w * 0.08, h * 0.77, w * 0.84, h * 0.06) # Caixa principal
    c.line(w * 0.08, h * 0.80, w * 0.92, h * 0.80) # Divisória horizontal
    c.line(w * 0.50, h * 0.77, w * 0.50, h * 0.80) # Divisória vertical Turma/Data

    c.setFont("Helvetica-Bold", 9)
    c.drawString(w * 0.09, h * 0.81, "ESCOLA:")
    c.drawString(w * 0.09, h * 0.78, "TURMA:")
    c.drawString(w * 0.51, h * 0.78, "DATA: ______ / ______ / _________")

    # Instruções
    c.drawString(w * 0.08, h * 0.74, "Caro(a) aluno(a),")
    c.setFont("Helvetica", 9)
    c.drawString(w * 0.08, h * 0.725, "Sua participação neste Simulado é muito importante para avançarmos na qualidade da educação da nossa escola.")
    c.drawString(w * 0.08, h * 0.710, "Para melhor utilização deste cartão-resposta, segue orientações para preenchimento:")
    c.drawString(w * 0.12, h * 0.695, "• Use a caneta esferográfica azul ou preta para assinalar uma única resposta para cada questão,")
    c.drawString(w * 0.12, h * 0.680, "  preenchendo totalmente o círculo e tomando cuidado para não ultrapassar o espaço delimitado.")
    
    c.setFont("Helvetica-Bold", 9)
    c.drawString(w * 0.12, h * 0.665, "Marcação CORRETA: ( • )        Marcação INCORRETA: ( X ) ( / )")

    c.setFont("Helvetica-Bold", 10)
    c.drawString(w * 0.08, h * 0.635, "NOME DO ALUNO:")
    c.line(w * 0.25, h * 0.635, w * 0.92, h * 0.635)

    # 5. Grids (Intocável)
    for grid in conf.grids:
        x1 = grid.x_start * w
        x2 = grid.x_end * w
        y1_pdf = h - (grid.y_end * h)
        y2_pdf = h - (grid.y_start * h)

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
            c.setStrokeColorRGB(0.4, 0.4, 0.4)
            for col in range(grid.cols):
                cx = x1 + (col * cell_w) + (cell_w / 2)
                c.circle(cx, cy, raio, stroke=1, fill=0)

    c.save()

def gerar_imagem_a4(conf, filename, ext, titulo_custom=None, subtitulo_custom=None, logos=None):
    pdf_tmp = "temp_gen.pdf"
    gerar_pdf(conf, pdf_tmp, titulo_custom, subtitulo_custom, logos)
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
