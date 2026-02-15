import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
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

    # 2. Inserção de Logos Dinâmicas no Topo
    y_logo = h * 0.89
    if logos:
        if logos.get('esq'):
            c.drawImage(ImageReader(logos['esq']), w * 0.08, y_logo, width=w*0.18, height=h*0.06, preserveAspectRatio=True, mask='auto')
        if logos.get('cen'):
            c.drawImage(ImageReader(logos['cen']), w * 0.30, y_logo, width=w*0.40, height=h*0.06, preserveAspectRatio=True, mask='auto')
        if logos.get('dir'):
            c.drawImage(ImageReader(logos['dir']), w * 0.74, y_logo, width=w*0.18, height=h*0.06, preserveAspectRatio=True, mask='auto')

    # 3. Títulos Dinâmicos
    texto_titulo = titulo_custom if titulo_custom else conf.titulo_prova
    texto_subtitulo = subtitulo_custom if subtitulo_custom else conf.subtitulo

    c.setFillColor(colors.HexColor("#2980b9")) # Azul no Título
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(w / 2.0, h * 0.85, texto_titulo)
    
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica", 11)
    c.drawCentredString(w / 2.0, h * 0.83, texto_subtitulo)

    # 4. Cabeçalho Visual (Limpo, sem bordas pesadas)
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(0.5)
    c.setFont("Helvetica-Bold", 9)

    # Linha 1: UNIDADE DE ENSINO
    c.drawString(w * 0.08, h * 0.78, "UNIDADE DE ENSINO:")
    c.line(w * 0.23, h * 0.78, w * 0.92, h * 0.78)

    # Linha 2: ANO, TURMA, TURNO
    c.drawString(w * 0.08, h * 0.74, "ANO:")
    c.line(w * 0.12, h * 0.74, w * 0.35, h * 0.74)
    
    c.drawString(w * 0.38, h * 0.74, "TURMA:")
    c.line(w * 0.44, h * 0.74, w * 0.65, h * 0.74)
    
    c.drawString(w * 0.68, h * 0.74, "TURNO:")
    c.line(w * 0.74, h * 0.74, w * 0.92, h * 0.74)

    # Linha 3: ALUNO
    c.drawString(w * 0.08, h * 0.70, "ALUNO:")
    c.line(w * 0.14, h * 0.70, w * 0.92, h * 0.70)

    # Caixa de INSTRUÇÕES (Laranja clara)
    c.setStrokeColor(colors.HexColor("#f39c12")) 
    c.setLineWidth(0.5)
    c.rect(w * 0.08, h * 0.65, w * 0.84, h * 0.03)
    c.setFillColorRGB(0.3, 0.3, 0.3)
    c.setFont("Helvetica", 8)
    c.drawString(w * 0.09, h * 0.662, "INSTRUÇÕES: 1. Use caneta azul ou preta. 2. Preencha totalmente a bolinha.")

    # 5. Grids com TARJAS, CORES e QUADROS AJUSTADOS
    for grid in conf.grids:
        x1 = grid.x_start * w
        x2 = grid.x_end * w
        y1_pdf = h - (grid.y_end * h)
        y2_pdf = h - (grid.y_start * h)
        
        cor_materia = colors.HexColor(grid.cor_hex)

        # -------------------------------------------------------------
        # DESENHA O QUADRO DE SEPARAÇÃO (Sem sobreposições)
        # -------------------------------------------------------------
        # Margem BEM CUSTA (pad_x = 6) para os blocos não se encavalarem
        pad_x = 6
        box_x = x1 - pad_x
        box_w = (x2 - x1) + (pad_x * 2)
        box_y = y1_pdf - 20
        box_h = (y2_pdf - y1_pdf) + 30
        
        if grid.labels == ["D", "U"]:
            box_x = x1 - 5
            box_w = (x2 - x1) + 10
            
        c.setStrokeColor(cor_materia)
        c.setLineWidth(0.5)
        c.roundRect(box_x, box_y, box_w, box_h, 3, stroke=1, fill=0)

        # -------------------------------------------------------------
        # TARJA SÓLIDA DO BLOCO (Banner)
        # -------------------------------------------------------------
        banner_h = 16
        banner_y = y2_pdf + 14
        
        c.setFillColor(cor_materia)
        c.roundRect(box_x, banner_y, box_w, banner_h, 4, stroke=0, fill=1)
        
        c.setFillColorRGB(1, 1, 1) # Texto branco
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString((x1+x2)/2, banner_y + 4, grid.titulo)

        # -------------------------------------------------------------
        # TEXTOS DA DISCIPLINA (Abaixo do Banner)
        # -------------------------------------------------------------
        if grid.texto_extra:
            c.setFillColor(cor_materia)
            c.setFont("Helvetica-Bold", 7)
            c.drawCentredString((x1+x2)/2, banner_y - 10, grid.texto_extra)
            
        if grid.labels == ["D", "U"]:
            c.setStrokeColorRGB(0.5, 0.5, 0.5)
            # Caixinhas brancas para escrever número sob a tarja D U
            c.rect(x1 - 6, banner_y - 14, 12, 12, fill=0)
            c.rect(x2 - 6, banner_y - 14, 12, 12, fill=0)

        # -------------------------------------------------------------
        # BOLINHAS E ALTERNATIVAS
        # -------------------------------------------------------------
        c.setFillColorRGB(0, 0, 0)
        c.setStrokeColorRGB(0.4, 0.4, 0.4)

        cell_w = (x2 - x1) / grid.cols
        cell_h = (y2_pdf - y1_pdf) / grid.rows
        raio = min(cell_w, cell_h) * 0.25

        c.setFont("Helvetica-Bold", 8)
        for col in range(grid.cols):
            cx = x1 + (col * cell_w) + (cell_w / 2)
            c.drawCentredString(cx, y2_pdf - 6, grid.labels[col])

        for row in range(grid.rows):
            cy = y2_pdf - (row * cell_h) - (cell_h / 2) - 15

            if grid.questao_inicial > 0:
                q_num = grid.questao_inicial + row
                c.setFont("Helvetica", 8)
                # Formata com dois dígitos (01, 02...)
                c.drawString(x1 - 16, cy - 3, f"{q_num:02d}")
            else:
                c.setFont("Helvetica", 8)
                c.drawString(x1 - 10, cy - 3, str(row))

            c.setLineWidth(1)
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
