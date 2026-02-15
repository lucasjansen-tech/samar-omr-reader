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
# GEOMETRIA: PADRÃO EVALBEE (Ajuste Fino Milimétrico)
# =========================================================

# --- EVALBEE 52 QUESTÕES ---
Y_TOP_EV52 = 0.48
Y_BOT_EV52 = 0.78
H_EV52 = Y_BOT_EV52 - Y_TOP_EV52

# --- EVALBEE 44 QUESTÕES ---
Y_TOP_EV44 = 0.48
Y_BOT_EV44 = 0.73
H_EV44 = Y_BOT_EV44 - Y_TOP_EV44

# --- EVALBEE 18 QUESTÕES (Calibrado com a imagem image_e4b8e0.jpg) ---
# Subimos o Y_TOP de 0.635 para 0.615 para parar de cortar a cabeça da primeira linha
Y_TOP_EV18 = 0.615  
Y_BOT_EV18 = 0.840  
H_EV18 = Y_BOT_EV18 - Y_TOP_EV18
Y_END_FREQ_EV18 = Y_TOP_EV18 + ((H_EV18 / 9) * 10)

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
            # FREQ deslocado para a esquerda (0.20 a 0.27) para abraçar as duas colunas
            GridConfig("FREQ.", "", 0.20, 0.27, Y_TOP_EV18, Y_END_FREQ_EV18, 10, 2, ["D", "U"], 0, COR_EVALBEE),
            # Blocos mantiveram o eixo X pois os centros já estavam cravando nas bolinhas na sua última foto
            GridConfig("BLOCO 1", "", 0.44, 0.54, Y_TOP_EV18, Y_BOT_EV18, 9, 4, ["A","B","C","D"], 1, COR_EVALBEE),
            GridConfig("BLOCO 2", "", 0.65, 0.75, Y_TOP_EV18, Y_BOT_EV18, 9, 4, ["A","B","C","D"], 10, COR_EVALBEE),
        ]
    )
}
