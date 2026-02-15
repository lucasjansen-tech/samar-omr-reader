from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from pdf2image import convert_from_path
import os
import io

def gerar_pdf(conf, filename, titulo_custom=None, subtitulo_custom=None, logos=None):
    c = canvas.Canvas(filename, pagesize=A4)
    w, h = A4

    # 1. Âncoras do Sistema SAMAR (Intocáveis)
    m_pct = conf.MARGIN_PCT
    s_px = w * 0.04
    offset = w * m_pct

    c.setFillColorRGB(0, 0, 0)
    c.rect(offset, h - offset - s_px, s_px, s_px, fill=1) # Top-Left
    c.rect(w - offset - s_px, h - offset - s_px, s_px, s_px, fill=1) # Top-Right
    c.rect(offset, offset, s_px, s_px, fill=1) # Bottom-Left
    c.rect(w - offset - s_px, offset, s_px, s_px, fill=1) # Bottom-Right

    # 2. Inserção das Logos (Se enviadas)
    y_logo = h * 0.85
    h_logo = h * 0.07
    w_logo = w * 0.20

    if logos:
        # ImageReader aceita o arquivo vindo direto do painel do Streamlit
        if logos.get('esq'):
            c.drawImage(ImageReader(logos['esq']), w * 0.1, y_logo, width=w_logo, height=h_logo, preserveAspectRatio=True, mask='auto')
        if logos.get('cen'):
            c.drawImage(ImageReader(logos['cen']), w * 0.40, y_logo, width=w_logo, height=h_logo, preserveAspectRatio=True, mask='auto')
        if logos.get('dir'):
            c.drawImage(ImageReader(logos['dir']), w * 0.70, y_logo, width=w_logo, height=h_logo, preserveAspectRatio=True, mask='auto')

    # 3. Títulos Dinâmicos
    t_prova = titulo_custom if titulo_custom else conf.titulo_prova
    s_prova = subtitulo_custom if subtitulo_custom else conf.subtitulo

    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w / 2.0, h * 0.80, t_prova)
    c.setFont("Helvetica", 12)
    c.drawCentredString(w / 2.0, h * 0.78, s_prova)

    # 4. Cabeçalho de Identificação (Linhas para o aluno preencher)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(w * 0.1, h * 0.72, "NOME DO ALUNO:")
    c.line(w * 0.26, h * 0.72, w * 0.9, h * 0.72)
    
    c.drawString(w * 0.1, h * 0.69, "ESCOLA:")
    c.line(w * 0.17, h * 0.69, w * 0.45, h * 0.69)
    
    c.drawString(w * 0.5, h * 0.69, "TURMA:")
    c.line(w * 0.57, h * 0.69, w * 0.7, h * 0.69)
    
    c.drawString(w * 0.75, h * 0.69, "DATA:")
    c.line(w * 0.82, h * 0.69, w * 0.9, h * 0.69)

    # 5. Grade de Questões (A matemática já validada do layout_samar)
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

def gerar_imagem_a4(conf, filename, ext, titulo=None, subtitulo=None, logos=None):
    pdf_tmp = "temp_gen.pdf"
    gerar_pdf(conf, pdf_tmp, titulo, subtitulo, logos)
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
