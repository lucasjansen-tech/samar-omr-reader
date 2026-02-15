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
# GEOMETRIA: SISTEMA SAMAR NATIVO (INTOCADA E VALIDADA)
# =========================================================
Y_TOP = 0.35
Y_BOT = 0.85 
ALTURA_BLOCO = Y_BOT - Y_TOP

Y_END_FREQ_13 = Y_TOP + ((ALTURA_BLOCO / 13) * 10) 
Y_END_FREQ_11 = Y_TOP + ((ALTURA_BLOCO / 11) * 10) 
Y_END_FREQ_09 = Y_BOT 

# =========================================================
# GEOMETRIA: PADRÃO EVALBEE
# =========================================================

# --- EVALBEE 52 QUESTÕES ---
Y_TOP_EV52 = 0.48
Y_BOT_EV52 = 0.78
H_EV52 = Y_BOT_EV52 - Y_TOP_EV52

# --- EVALBEE 44 QUESTÕES ---
Y_TOP_EV44 = 0.48
Y_BOT_EV44 = 0.73
H_EV44 = Y_BOT_EV44 - Y_TOP_EV44

# =========================================================
# EVALBEE 18 QUESTÕES (CALIBRAÇÃO FINAL - IMAGEM RAIO-X)
# =========================================================

# FREQUÊNCIA: Mais curta, pois não tem salto. Termina exatamente na bolinha 9.
Y_TOP_FREQ = 0.631
Y_BOT_FREQ = 0.796

# BLOCOS DE QUESTÕES (Com o salto exato de uma linha entre a 5 e a 6)
Y_TOP_PT1 = 0.647  # Empurrado para baixo para não ler o texto "A B C D"
Y_BOT_PT1 = 0.730  

Y_TOP_PT2 = 0.747  # Inicia logo após o salto
Y_BOT_PT2 = 0.813  # Puxado sutilmente para cima para não vazar a bolinha

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
    # PADRÕES IMPORTADOS DO EVALBEE
    # ---------------------------------------------------------
    "EVALBEE_52_Questoes": ConfiguracaoProva(
        titulo_prova="GABARITO EVALBEE",
        subtitulo="Ensino Fundamental II - 7º ao 9º Ano",
        grids=[
            GridConfig("FREQ.", "", 0.10, 0.15, Y_TOP_EV52, Y_TOP_EV52 + ((H_EV52/13)*10), 10, 2, ["D", "U"], 0, COR_EVALBEE),
            GridConfig("BLOCO 1", "", 0.26, 0.36, Y_TOP_EV52, Y_BOT_EV52, 13, 4, ["A","B","C","D"], 1, COR_EVALBEE),
            GridConfig("BLOCO 2", "", 0.44, 0.54, Y_TOP_EV52, Y_BOT_EV52, 13, 4, ["A","B","C","D"], 14, COR_EVALBEE),
            GridConfig("BLOCO 3", "", 0.62, 0.72, Y_TOP_EV52, Y_BOT_EV52, 13, 4, ["A","B","C","D"], 27, COR_EVALBEE),
            GridConfig("BLOCO 4", "", 0.80, 0.90, Y_TOP_EV52, Y_BOT_EV52, 13, 4, ["A","B","C","D"], 40, COR_EVALBEE),
        ]
    ),

    "EVALBEE_44_Questoes": ConfiguracaoProva(
        titulo_prova="GABARITO EVALBEE",
        subtitulo="Ensino Fundamental - 4º ao 6º Ano",
        grids=[
            GridConfig("FREQ.", "", 0.10, 0.15, Y_TOP_EV44, Y_TOP_EV44 + ((H_EV44/11)*10), 10, 2, ["D", "U"], 0, COR_EVALBEE),
            GridConfig("BLOCO 1", "", 0.26, 0.36, Y_TOP_EV44, Y_BOT_EV44, 11, 4, ["A","B","C","D"], 1, COR_EVALBEE),
            GridConfig("BLOCO 2", "", 0.44, 0.54, Y_TOP_EV44, Y_BOT_EV44, 11, 4, ["A","B","C","D"], 12, COR_EVALBEE),
            GridConfig("BLOCO 3", "", 0.62, 0.72, Y_TOP_EV44, Y_BOT_EV44, 11, 4, ["A","B","C","D"], 23, COR_EVALBEE),
            GridConfig("BLOCO 4", "", 0.80, 0.90, Y_TOP_EV44, Y_BOT_EV44, 11, 4, ["A","B","C","D"], 34, COR_EVALBEE),
        ]
    ),

    "EVALBEE_18_Questoes": ConfiguracaoProva(
        titulo_prova="GABARITO EVALBEE",
        subtitulo="Ensino Fundamental I - 1º ao 3º Ano",
        grids=[
            # Frequência isolada com a altura exata
            GridConfig("FREQ.", "", 0.22, 0.28, Y_TOP_FREQ, Y_BOT_FREQ, 10, 2, ["D", "U"], 0, COR_EVALBEE),
            
            # Bloco 1 (Português)
            GridConfig("BLOCO 1A", "", 0.44, 0.55, Y_TOP_PT1, Y_BOT_PT1, 5, 4, ["A","B","C","D"], 1, COR_EVALBEE), 
            GridConfig("BLOCO 1B", "", 0.44, 0.55, Y_TOP_PT2, Y_BOT_PT2, 4, 4, ["A","B","C","D"], 6, COR_EVALBEE), 
            
            # Bloco 2 (Matemática)
            GridConfig("BLOCO 2A", "", 0.65, 0.76, Y_TOP_PT1, Y_BOT_PT1, 5, 4, ["A","B","C","D"], 10, COR_EVALBEE), 
            GridConfig("BLOCO 2B", "", 0.65, 0.76, Y_TOP_PT2, Y_BOT_PT2, 4, 4, ["A","B","C","D"], 15, COR_EVALBEE), 
        ]
    )
}
