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
    # Âncoras ficam a 5% da borda (bem externas)
    MARGIN_PCT = 0.05 

# --- GEOMETRIA ---
# Y_TOP: Baixei para 0.36 para dar espaço aos títulos dos blocos não baterem no cabeçalho
Y_TOP = 0.36 
# Y_BOT: Até 92% para caber as 13 questões confortavelmente
Y_BOT = 0.92

TIPOS_PROVA = {
    "52_Questoes_Grid": ConfiguracaoProva(
        titulo_prova="AVALIAÇÃO DE APRENDIZAGEM",
        subtitulo="Ensino Fundamental II - 7º ao 9º Ano",
        grids=[
            # FREQUÊNCIA (Mais estreita e recuada da âncora)
            # Começa em 0.08 (8%) para ficar longe da âncora que está em 0.05 (5%)
            GridConfig("FREQ.", "", 0.08, 0.14, Y_TOP, 0.66, 10, 2, ["D", "U"], 0, COR_LARANJA),
            
            # BLOCOS (Compactados horizontalmente)
            # Note os intervalos menores entre x_start e x_end para reduzir a largura total
            GridConfig("BLOCO 1", "LÍNGUA PORTUGUESA", 0.18, 0.33, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 1, COR_AZUL),
            GridConfig("BLOCO 2", "LÍNGUA PORTUGUESA", 0.37, 0.52, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 14, COR_AZUL),
            GridConfig("BLOCO 3", "MATEMÁTICA", 0.56, 0.71, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 27, COR_LARANJA),
            GridConfig("BLOCO 4", "MATEMÁTICA", 0.75, 0.90, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 40, COR_LARANJA),
        ]
    )
}
