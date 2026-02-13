from dataclasses import dataclass
from typing import List

# Cores Oficiais
COR_AZUL = "#2980b9"    # Português
COR_LARANJA = "#e67e22" # Matemática

@dataclass
class GridConfig:
    titulo: str
    texto_extra: str
    x_start: float   # % largura
    x_end: float     # % largura
    y_start: float   # % altura
    y_end: float     # % altura
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
    REF_W = 1240
    REF_H = 1754
    MARGIN_PCT = 0.05 

# --- GEOMETRIA CONGELADA ---
# Ajustado para caber cabeçalho completo e instruções sem cortar o final
Y_TOP = 0.37
Y_BOT = 0.94

TIPOS_PROVA = {
    "52_Questoes_Grid": ConfiguracaoProva(
        titulo_prova="AVALIAÇÃO DE APRENDIZAGEM",
        subtitulo="Ensino Fundamental II - 7º ao 9º Ano",
        grids=[
            # FREQ (Esquerda)
            GridConfig("FREQ.", "", 0.08, 0.14, Y_TOP, 0.68, 10, 2, ["D", "U"], 0, COR_LARANJA),
            
            # BLOCO 1 (Português)
            GridConfig("BLOCO 1", "LÍNGUA PORTUGUESA", 0.18, 0.33, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 1, COR_AZUL),
            
            # BLOCO 2 (Português)
            GridConfig("BLOCO 2", "LÍNGUA PORTUGUESA", 0.37, 0.52, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 14, COR_AZUL),
            
            # BLOCO 3 (Matemática)
            GridConfig("BLOCO 3", "MATEMÁTICA", 0.56, 0.71, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 27, COR_LARANJA),
            
            # BLOCO 4 (Matemática)
            GridConfig("BLOCO 4", "MATEMÁTICA", 0.75, 0.90, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 40, COR_LARANJA),
        ]
    )
}
