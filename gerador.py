from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from layout_samar import ConfiguracaoProva, GridConfig
import os

def cm_to_pt(cm): return cm * 28.3465

def desenhar_layout_grid(c, conf: ConfiguracaoProva):
    W, H = A4 # 595 x 842
    
    # 1. Âncoras (5% da borda)
    m = W * conf.MARGIN_PCT
    s = 30 # Tamanho fixo em pontos
    c.setFillColor(colors.black)
    c.rect(m, H-m-s, s, s, fill=1, stroke=0) # TL
    c.rect(W-m-s, H-m-s, s, s, fill=1, stroke=0) # TR
    c.rect(m, m, s, s, fill=1, stroke=0) # BL
    c.rect(W-m-s, m, s, s, fill=1, stroke=0) # BR
    
    # 2. Cabeçalho (Fixo no topo)
    c.setFillColor(HexColor("#2980b9"))
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(W/2, H - 50, conf.titulo_prova)
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 12)
    c.drawCentredString(W/2, H - 70, conf.subtitulo)
    
    # Linhas de dados
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    c.setFont("Helvetica-Bold", 10)
    
    y_start = H - 120
    c.drawString(m, y_start, "UNIDADE DE ENSINO:")
    c.line(m + 110, y_start-2, W-m, y_start-2)
    
    c.drawString(m, y_start-30, "ALUNO:")
    c.line(m + 50, y_start-32, W-m, y_start-32)
    
    # 3. Desenhar GRIDS
    for grid in conf.grids:
        # Converter % para pontos PDF
        # PDF Y começa de baixo (0) para cima (H)
        # Nossos grids Y são de cima (0.0) para baixo (1.0)
        # Então: y_pdf = H - (y_pct * H)
        
        x1 = grid.x_start_pct * W
        w_grid = (grid.x_end_pct - grid.x_start_pct) * W
        
        y_top = H - (grid.y_start_pct * H)
        y_bot = H - (grid.y_end_pct * H)
        h_grid = y_top - y_bot
        
        # Título do Bloco
        c.setFillColor(HexColor(grid.cor_hex))
        c.roundRect(x1, y_top + 10, w_grid, 20, 4, fill=1, stroke=0)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(x1 + w_grid/2, y_top + 16, grid.titulo)
        
        # Corpo do Grid
        cell_h = h_grid / grid.rows
        cell_w = w_grid / grid.cols
        
        c.setFillColor(colors.black)
        c.setStrokeColor(colors.black)
        
        # Cabeçalho das colunas (ABCD ou DU)
        if grid.labels:
            for i, lbl in enumerate(grid.labels):
                cx = x1 + (i * cell_w) + (cell_w/2)
                c.setFont("Helvetica-Bold", 9)
                c.drawCentredString(cx, y_top + 2, lbl)

        # Linhas
        for r in range(grid.rows):
            cy = y_top - (r * cell_h) - (cell_h/2)
            
            # Número da questão
            if grid.questao_inicial > 0:
                q_num = grid.questao_inicial + r
                c.setFont("Helvetica-Bold", 9)
                c.drawRightString(x1 - 5, cy - 3, f"{q_num:02d}")
            elif grid.labels == ["D", "U"]:
                # Números da frequência (0-9) ao lado
                c.setFont("Helvetica", 9)
                c.drawRightString(x1 - 5, cy - 3, str(r))

            # Bolinhas
            for col in range(grid.cols):
                cx = x1 + (col * cell_w) + (cell_w/2)
                c.circle(cx, cy, 7, stroke=1, fill=0)
                
                # Letra dentro da bolinha (se não for freq)
                if grid.questao_inicial > 0:
                    c.setFont("Helvetica", 6)
                    c.drawCentredString(cx, cy - 2, grid.labels[col])

def gerar_pdf(conf: ConfiguracaoProva, filename):
    c = canvas.Canvas(filename, pagesize=A4)
    desenhar_layout_grid(c, conf)
    c.save()
    return filename

def gerar_imagem_a4(conf, filename_saida, formato="png"):
    # (Mantém igual, usando pdf2image)
    pass
