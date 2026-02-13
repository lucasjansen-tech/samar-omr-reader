from dataclasses import dataclass
from typing import List

# Cores Oficiais (Baseado na imagem image_cd30f5.png)
COR_AZUL = "#2980b9"    # Português
COR_LARANJA = "#e67e22" # Matemática

@dataclass
class GridConfig:
    titulo: str
    x_start: float # % da largura (0.0 a 1.0)
    x_end: float   # % da largura
    y_start: float # % da altura (0.0 a 1.0)
    y_end: float   # % da altura
    rows: int
    cols: int
    labels: List[str] 
    questao_inicial: int
    cor_hex: str

@dataclass
class ConfiguracaoProva:
    titulo_prova: str
    subtitulo: str
    grids: List[GridConfig]
    REF_W = 1240 # Resolução de referência (A4 150dpi)
    REF_H = 1754
    MARGIN_PCT = 0.05 

# --- MODELO 52 QUESTÕES (CORRIGIDO) ---
# Ajuste Fino Vertical para imagem do 7º-9º ano
Y_TOP = 0.32  # Começa em 32% da folha
Y_BOT = 0.91  # Vai até 91%

TIPOS_PROVA = {
    "52_Questoes_Grid": ConfiguracaoProva(
        titulo_prova="AVALIAÇÃO DE APRENDIZAGEM",
        subtitulo="Ensino Fundamental II - 7º ao 9º Ano",
        grids=[
            # FREQUÊNCIA (Laranja, conforme imagem)
            GridConfig("FREQ.", 0.05, 0.12, Y_TOP, 0.62, 10, 2, ["D", "U"], 0, COR_LARANJA),
            
            # BLOCO 1 (Azul - Português)
            GridConfig("BLOCO 1", 0.16, 0.33, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 1, COR_AZUL),
            
            # BLOCO 2 (Azul - Português)
            GridConfig("BLOCO 2", 0.37, 0.54, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 14, COR_AZUL),
            
            # BLOCO 3 (Laranja - Matemática)
            GridConfig("BLOCO 3", 0.58, 0.75, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 27, COR_LARANJA),
            
            # BLOCO 4 (Laranja - Matemática)
            GridConfig("BLOCO 4", 0.79, 0.96, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 40, COR_LARANJA),
        ]
    )
}
