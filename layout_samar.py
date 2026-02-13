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
    y_start: float   # % altura (Topo das BOLINHAS)
    y_end: float     # % altura (Fundo das BOLINHAS)
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

# --- GEOMETRIA ---
# Y_TOP: Onde começa a PRIMEIRA LINHA DE BOLINHAS (não o título)
# Baixei para 0.35 para caber os títulos em cima sem bater no cabeçalho
Y_TOP = 0.35 
Y_BOT = 0.92

TIPOS_PROVA = {
    "52_Questoes_Grid": ConfiguracaoProva(
        titulo_prova="AVALIAÇÃO DE APRENDIZAGEM",
        subtitulo="Ensino Fundamental II - 7º ao 9º Ano",
        grids=[
            # FREQ (Laranja)
            GridConfig("FREQ.", "", 0.05, 0.11, Y_TOP, 0.65, 10, 2, ["D", "U"], 0, COR_LARANJA),
            
            # BLOCO 1 (Azul)
            GridConfig("BLOCO 1", "LÍNGUA PORTUGUESA", 0.15, 0.32, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 1, COR_AZUL),
            
            # BLOCO 2 (Azul)
            GridConfig("BLOCO 2", "LÍNGUA PORTUGUESA", 0.36, 0.53, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 14, COR_AZUL),
            
            # BLOCO 3 (Laranja)
            GridConfig("BLOCO 3", "MATEMÁTICA", 0.57, 0.74, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 27, COR_LARANJA),
            
            # BLOCO 4 (Laranja)
            GridConfig("BLOCO 4", "MATEMÁTICA", 0.78, 0.95, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 40, COR_LARANJA),
        ]
    )
}
