from dataclasses import dataclass
from typing import List

COR_AZUL = "#2980b9"
COR_LARANJA = "#e67e22"

@dataclass
class GridConfig:
    titulo: str
    texto_extra: str
    x_start: float
    x_end: float
    y_start: float
    y_end: float
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

# GEOMETRIA VALIDADA
Y_TOP = 0.36
Y_BOT = 0.85 

ALTURA_BLOCO = Y_BOT - Y_TOP
ALTURA_FREQ = (ALTURA_BLOCO / 13) * 10
Y_END_FREQ = Y_TOP + ALTURA_FREQ

TIPOS_PROVA = {
    "52_Questoes_Grid": ConfiguracaoProva(
        titulo_prova="AVALIAÇÃO DE APRENDIZAGEM",
        subtitulo="Ensino Fundamental II - 7º ao 9º Ano",
        grids=[
            # FREQ: Movido para 0.09 para desgrudar da âncora (que vai até 0.05)
            GridConfig("FREQ.", "", 0.09, 0.15, Y_TOP, Y_END_FREQ, 10, 2, ["D", "U"], 0, COR_LARANJA),
            
            # BLOCOS
            GridConfig("BLOCO 1", "LÍNGUA PORTUGUESA", 0.19, 0.34, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 1, COR_AZUL),
            GridConfig("BLOCO 2", "LÍNGUA PORTUGUESA", 0.38, 0.53, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 14, COR_AZUL),
            GridConfig("BLOCO 3", "MATEMÁTICA", 0.57, 0.72, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 27, COR_LARANJA),
            GridConfig("BLOCO 4", "MATEMÁTICA", 0.76, 0.91, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 40, COR_LARANJA),
        ]
    )
}
