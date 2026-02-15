from dataclasses import dataclass
from typing import List

COR_AZUL = "#2980b9"
COR_LARANJA = "#e67e22"
COR_EVALBEE = "#555555" 

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

# =========================================================
# GEOMETRIA: SISTEMA SAMAR NATIVO (Validado e Separado)
# =========================================================
Y_TOP = 0.35
Y_BOT = 0.85 
ALTURA_BLOCO = Y_BOT - Y_TOP

Y_END_FREQ_13 = Y_TOP + ((ALTURA_BLOCO / 13) * 10) 
Y_END_FREQ_11 = Y_TOP + ((ALTURA_BLOCO / 11) * 10) 
Y_END_FREQ_09 = Y_BOT 

TIPOS_PROVA = {
    # ---------------------------------------------------------
    # PADRÕES NATIVOS (SISTEMA SAMAR)
    # ---------------------------------------------------------
    "SAMAR_52_Questoes": ConfiguracaoProva(
        titulo_prova="AVALIAÇÃO DE APRENDIZAGEM",
        subtitulo="Ensino Fundamental II - 7º ao 9º Ano",
        grids=[
            GridConfig("FREQ.", "", 0.10, 0.16, Y_TOP, Y_END_FREQ_13, 10, 2, ["D", "U"], 0, COR_LARANJA),
            GridConfig("BLOCO 1", "LÍNGUA PORTUGUESA", 0.20, 0.35, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 1, COR_AZUL),
            GridConfig("BLOCO 2", "LÍNGUA PORTUGUESA", 0.38, 0.53, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 14, COR_AZUL),
            GridConfig("BLOCO 3", "MATEMÁTICA", 0.56, 0.71, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 27, COR_LARANJA),
            GridConfig("BLOCO 4", "MATEMÁTICA", 0.74, 0.89, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 40, COR_LARANJA),
        ]
    ),

    "SAMAR_44_Questoes": ConfiguracaoProva(
        titulo_prova="AVALIAÇÃO DE APRENDIZAGEM",
        subtitulo="Ensino Fundamental - 4º ao 6º Ano",
        grids=[
            GridConfig("FREQ.", "", 0.10, 0.16, Y_TOP, Y_END_FREQ_11, 10, 2, ["D", "U"], 0, COR_LARANJA),
            GridConfig("BLOCO 1", "LÍNGUA PORTUGUESA", 0.20, 0.35, Y_TOP, Y_BOT, 11, 4, ["A","B","C","D"], 1, COR_AZUL),
            GridConfig("BLOCO 2", "LÍNGUA PORTUGUESA", 0.38, 0.53, Y_TOP, Y_BOT, 11, 4, ["A","B","C","D"], 12, COR_AZUL),
            GridConfig("BLOCO 3", "MATEMÁTICA", 0.56, 0.71, Y_TOP, Y_BOT, 11, 4, ["A","B","C","D"], 23, COR_LARANJA),
            GridConfig("BLOCO 4", "MATEMÁTICA", 0.74, 0.89, Y_TOP, Y_BOT, 11, 4, ["A","B","C","D"], 34, COR_LARANJA),
        ]
    ),

    "SAMAR_18_Questoes": ConfiguracaoProva(
        titulo_prova="AVALIAÇÃO DE APRENDIZAGEM",
        subtitulo="Ensino Fundamental I - 1º ao 3º Ano",
        grids=[
            GridConfig("FREQ.", "", 0.15, 0.22, Y_TOP, Y_END_FREQ_09, 10, 2, ["D", "U"], 0, COR_LARANJA),
            GridConfig("BLOCO 1", "LÍNGUA PORTUGUESA", 0.32, 0.52, Y_TOP, Y_BOT, 9, 4, ["A","B","C","D"], 1, COR_AZUL),
            GridConfig("BLOCO 2", "MATEMÁTICA", 0.58, 0.78, Y_TOP, Y_BOT, 9, 4, ["A","B","C","D"], 10, COR_LARANJA),
        ]
    ),

    # ---------------------------------------------------------
    # PADRÕES IMPORTADOS DO EVALBEE (Mapeamento Plano em A4)
    # ---------------------------------------------------------
    "EVALBEE_52_Questoes": ConfiguracaoProva(
        titulo_prova="GABARITO EVALBEE",
        subtitulo="Ensino Fundamental II - 7º ao 9º Ano",
        grids=[
            GridConfig("FREQ.", "", 0.08, 0.15, 0.50, 0.90, 10, 2, ["D", "U"], 0, COR_EVALBEE),
            GridConfig("BLOCO 1", "", 0.20, 0.35, 0.50, 0.90, 13, 4, ["A","B","C","D"], 1, COR_EVALBEE),
            GridConfig("BLOCO 2", "", 0.40, 0.55, 0.50, 0.90, 13, 4, ["A","B","C","D"], 14, COR_EVALBEE),
            GridConfig("BLOCO 3", "", 0.60, 0.75, 0.50, 0.90, 13, 4, ["A","B","C","D"], 27, COR_EVALBEE),
            GridConfig("BLOCO 4", "", 0.80, 0.95, 0.50, 0.90, 13, 4, ["A","B","C","D"], 40, COR_EVALBEE),
        ]
    ),

    "EVALBEE_44_Questoes": ConfiguracaoProva(
        titulo_prova="GABARITO EVALBEE",
        subtitulo="Ensino Fundamental - 4º ao 6º Ano",
        grids=[
            GridConfig("FREQ.", "", 0.08, 0.15, 0.50, 0.90, 10, 2, ["D", "U"], 0, COR_EVALBEE),
            GridConfig("BLOCO 1", "", 0.20, 0.35, 0.50, 0.90, 11, 4, ["A","B","C","D"], 1, COR_EVALBEE),
            GridConfig("BLOCO 2", "", 0.40, 0.55, 0.50, 0.90, 11, 4, ["A","B","C","D"], 12, COR_EVALBEE),
            GridConfig("BLOCO 3", "", 0.60, 0.75, 0.50, 0.90, 11, 4, ["A","B","C","D"], 23, COR_EVALBEE),
            GridConfig("BLOCO 4", "", 0.80, 0.95, 0.50, 0.90, 11, 4, ["A","B","C","D"], 34, COR_EVALBEE),
        ]
    ),

    # FOCO ABSOLUTO AQUI: A Frequência e os Blocos começam a 60% da página (0.60).
    "EVALBEE_18_Questoes": ConfiguracaoProva(
        titulo_prova="GABARITO EVALBEE",
        subtitulo="Ensino Fundamental I - 1º ao 3º Ano",
        grids=[
            GridConfig("FREQ.", "", 0.17, 0.25, 0.60, 0.81, 10, 2, ["D", "U"], 0, COR_EVALBEE),
            GridConfig("BLOCO 1", "", 0.35, 0.55, 0.63, 0.81, 9, 4, ["A","B","C","D"], 1, COR_EVALBEE),
            GridConfig("BLOCO 2", "", 0.63, 0.83, 0.63, 0.81, 9, 4, ["A","B","C","D"], 10, COR_EVALBEE),
        ]
    )
}
