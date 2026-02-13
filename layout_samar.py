from dataclasses import dataclass
from typing import List

# Cores
COR_AZUL = "#2980b9"
COR_LARANJA = "#e67e22"

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

# --- GEOMETRIA EXPANDIDA ---
Y_TOP = 0.33
Y_BOT = 0.93 # Estendido para não cortar a questão 52

# Sincronia da Frequência (10 linhas ocupam 10/13 da altura do bloco)
ALTURA_BLOCO = Y_BOT - Y_TOP
ALTURA_FREQ = (ALTURA_BLOCO / 13) * 10
Y_END_FREQ = Y_TOP + ALTURA_FREQ

TIPOS_PROVA = {
    "52_Questoes_Grid": ConfiguracaoProva(
        titulo_prova="AVALIAÇÃO DE APRENDIZAGEM",
        subtitulo="Ensino Fundamental II - 7º ao 9º Ano",
        grids=[
            # FREQ (Alargada para 0.04-0.13 para garantir leitura de D e U)
            GridConfig("FREQ.", "", 0.04, 0.13, Y_TOP, Y_END_FREQ, 10, 2, ["D", "U"], 0, COR_LARANJA),
            
            # BLOCOS (Ajustados horizontalmente para caber números)
            GridConfig("BLOCO 1", "LÍNGUA PORTUGUESA", 0.16, 0.33, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 1, COR_AZUL),
            GridConfig("BLOCO 2", "LÍNGUA PORTUGUESA", 0.37, 0.54, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 14, COR_AZUL),
            GridConfig("BLOCO 3", "MATEMÁTICA", 0.58, 0.75, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 27, COR_LARANJA),
            GridConfig("BLOCO 4", "MATEMÁTICA", 0.79, 0.96, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 40, COR_LARANJA),
        ]
    )
}
