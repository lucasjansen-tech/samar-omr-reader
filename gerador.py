from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from layout_samar import ConfiguracaoProva
from pdf2image import convert_from_path
import os

def desenhar_layout_grid(c, conf: ConfiguracaoProva, titulo_custom=None, subtitulo_custom=None, logos=None):
    W, H = A4
    m = W * conf.MARGIN_PCT
    s = 30
    
    # Âncoras
    c.setFillColor(colors.black)
    c.rect(m, H-m-s, s, s, fill=1, stroke=0)
    c.rect(W-m-s, H-m-s, s, s, fill=1, stroke=0)
    c.rect(m, m, s, s, fill=1, stroke=0)
    c.rect(W-m-s, m, s, s, fill=1, stroke=0)
    
    # ====================================================================
    # TOPO: LOGOS E TÍTULOS (Levemente subidos para dar respiro embaixo)
    # ====================================================================
    texto_titulo = titulo_custom if titulo_custom else conf.titulo_prova
    texto_subtitulo = subtitulo_custom if subtitulo_custom else conf.subtitulo

    if logos:
        LOGO_BOX_W = 120  
        LOGO_BOX_H = 45   
        y_logo_pos = H - 65 

        if logos.get('esq'):
            c.drawImage(ImageReader(logos['esq']), 80, y_logo_pos, width=LOGO_BOX_W, height=LOGO_BOX_H, preserveAspectRatio=True, mask='auto')
        if logos.get('cen'):
            x_cen = (W / 2) - (LOGO_BOX_W / 2)
            c.drawImage(ImageReader(logos['cen']), x_cen, y_logo_pos, width=LOGO_BOX_W, height=LOGO_BOX_H, preserveAspectRatio=True, mask='auto')
        if logos.get('dir'):
            x_dir = W - 80 - LOGO_BOX_W
            c.drawImage(ImageReader(logos['dir']), x_dir, y_logo_pos, width=LOGO_BOX_W, height=LOGO_BOX_H, preserveAspectRatio=True, mask='auto')
            
    c.setFillColor(HexColor("#2980b9"))
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(W/2, H - 90, texto_titulo)
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 12)
    c.drawCentredString(W/2, H - 105, texto_subtitulo)
    
    # ====================================================================
    # CABEÇALHO 
    # ====================================================================
    c.setStrokeColor(colors.black); c.setLineWidth(0.8); c.setFont("Helvetica-Bold", 9)
    y = H - 130 
    
    c.drawString(m, y, "UNIDADE DE ENSINO:"); c.line(m+100, y-2, W-m, y-2)
    y -= 25
    c.drawString(m, y, "ANO:"); c.line(m+30, y-2, m+150, y-2)
    c.drawString(m+160, y, "TURMA:"); c.line(m+200, y-2, m+300, y-2)
    c.drawString(m+310, y, "TURNO:"); c.line(m+350, y-2, W-m, y-2)
    y -= 25
    c.drawString(m, y, "ALUNO:"); c.line(m+40, y-2, W-m, y-2)
    
    # ====================================================================
    # INSTRUÇÕES SINTETIZADAS E VISUAIS (Caixa folgada com mais respiro)
    # ====================================================================
    y_inst = y - 20
    c.setStrokeColor(HexColor("#e67e22"))
    
    # Caixa mais alta (85px) para as letras respirarem, bem longe do gabarito!
    c.rect(m, y_inst - 70, W-(2*m), 85, stroke=1, fill=0) 
    
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(m+10, y_inst + 3, "INSTRUÇÕES PARA PREENCHIMENTO:")
    
    c.setFont("Helvetica", 8)
    c.drawString(m+10, y_inst - 11, "• Caro(a) aluno(a), sua participação é muito importante para avançarmos na qualidade da educação da nossa escola.")
    c.drawString(m+10, y_inst - 25, "• Use caneta esferográfica azul ou preta. Escolha apenas uma opção por questão e preencha totalmente o círculo.")
    c.drawString(m+10, y_inst - 39, "• Não rasure o cartão. Em hipótese nenhuma haverá outro cartão-resposta para substituição.")
    
    # Exemplos Visuais bem distribuídos na base da caixa
    c.setFont("Helvetica-Bold", 8)
    c.drawString(m+10, y_inst - 55, "Marcação CORRETA:")
    c.circle(m+105, y_inst - 52, 4, fill=1, stroke=0) # Bolinha preta
    
    c.drawString(m+130, y_inst - 55, "Marcação INCORRETA:")
    
    cy_m = y_inst - 52
    c.setStrokeColor(colors.black); c.setLineWidth(0.5)
    
    # Desenhando X
    cx = m+235
    c.circle(cx, cy_m, 4, fill=0, stroke=1)
    c.line(cx-2, cy_m-2, cx+2, cy_m+2); c.line(cx-2, cy_m+2, cx+2, cy_m-2)
    
    # Desenhando Check (V)
    cx += 15
    c.circle(cx, cy_m, 4, fill=0, stroke=1)
    c.line(cx-2, cy_m, cx-1, cy_m-2); c.line(cx-1, cy_m-2, cx+3, cy_m+2)
    
    # Desenhando Ponto
    cx += 15
    c.circle(cx, cy_m, 4, fill=0, stroke=1)
    c.circle(cx, cy_m, 1, fill=1, stroke=0)
    
    # ====================================================================
    # GABARITO E GRIDS (Intocável - Ouro)
    # ====================================================================
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
                
                # ADICIONA OS QUADRADINHOS DE REFERÊNCIA (Para o aluno escrever a Frequência)
                if g.labels == ["D", "U"]:
                    c.setStrokeColor(colors.black); c.setLineWidth(0.5)
                    c.rect(cx - 7, y_top + 22, 14, 14, stroke=1, fill=0)

        for r in range(g.rows):
            cy = y_top - (r * cell_h) - (cell_h/2)
            y_box_bot = y_top - ((r+1) * cell_h)
            
            # GRID VISUAL (Retângulo cinza)
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
                
                # ADICIONA A REFERÊNCIA DENTRO DA BOLINHA
                if g.questao_inicial > 0:
                    c.setFont("Helvetica", 6)
                    c.drawCentredString(cx, cy - 2, g.labels[col])
                elif g.labels == ["D", "U"]:
                    c.setFont("Helvetica", 6)
                    c.drawCentredString(cx, cy - 2, str(r)) 

def gerar_pdf(conf, filename, titulo_custom=None, subtitulo_custom=None, logos=None):
    c = canvas.Canvas(filename, pagesize=A4)
    desenhar_layout_grid(c, conf, titulo_custom, subtitulo_custom, logos)
    c.save()
    return filename

def gerar_imagem_a4(conf, filename_saida, formato="png", titulo_custom=None, subtitulo_custom=None, logos=None):
    temp_pdf = "temp_gabarito.pdf"
    gerar_pdf(conf, temp_pdf, titulo_custom, subtitulo_custom, logos)
    try:
        imagens = convert_from_path(temp_pdf, dpi=300)
        if imagens:
            img = imagens[0]
            img.save(filename_saida, formato.upper())
            if os.path.exists(temp_pdf): os.remove(temp_pdf)
            return filename_saida
    except: return None
