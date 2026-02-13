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

# --- GEOMETRIA BLINDADA ---
# Y_TOP: 0.35 (Espaço seguro para o cabeçalho)
# Y_BOT: 0.85 (Termina bem antes da âncora inferior que fica em 0.95)
Y_TOP = 0.35
Y_BOT = 0.85 

ALTURA_BLOCO = Y_BOT - Y_TOP
ALTURA_FREQ = (ALTURA_BLOCO / 13) * 10
Y_END_FREQ = Y_TOP + ALTURA_FREQ

TIPOS_PROVA = {
    "52_Questoes_Grid": ConfiguracaoProva(
        titulo_prova="AVALIAÇÃO DE APRENDIZAGEM",
        subtitulo="Ensino Fundamental II - 7º ao 9º Ano",
        grids=[
            # FREQ: Começa em 0.10. Totalmente segura e longe da âncora (0.05).
            GridConfig("FREQ.", "", 0.10, 0.16, Y_TOP, Y_END_FREQ, 10, 2, ["D", "U"], 0, COR_LARANJA),
            
            # BLOCOS: Todos entre 0.20 e 0.90 (Âncoras ficam de fora)
            GridConfig("BLOCO 1", "LÍNGUA PORTUGUESA", 0.20, 0.35, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 1, COR_AZUL),
            GridConfig("BLOCO 2", "LÍNGUA PORTUGUESA", 0.38, 0.53, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 14, COR_AZUL),
            GridConfig("BLOCO 3", "MATEMÁTICA", 0.56, 0.71, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 27, COR_LARANJA),
            GridConfig("BLOCO 4", "MATEMÁTICA", 0.74, 0.89, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 40, COR_LARANJA),
        ]
    )
}
