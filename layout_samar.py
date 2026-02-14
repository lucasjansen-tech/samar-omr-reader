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

# --- GEOMETRIA BLINDADA (Validada) ---
Y_TOP = 0.35
Y_BOT = 0.85 

ALTURA_BLOCO = Y_BOT - Y_TOP

# --- CÁLCULOS DE SINCRONIA DA FREQUÊNCIA ---
# A altura da Frequência muda dependendo de quantas linhas tem a prova,
# para que os números de 0 a 9 fiquem perfeitamente alinhados com as questões.
Y_END_FREQ_13 = Y_TOP + ((ALTURA_BLOCO / 13) * 10) # Para prova de 52 (13 por bloco)
Y_END_FREQ_11 = Y_TOP + ((ALTURA_BLOCO / 11) * 10) # Para prova de 44 (11 por bloco)
Y_END_FREQ_09 = Y_BOT # Para prova de 18 (9 por bloco, a freq de 10 ocupa tudo)

TIPOS_PROVA = {
    # ---------------------------------------------------------
    # 1. PADRÃO 52 QUESTÕES (7º ao 9º Ano)
    # ---------------------------------------------------------
    "52_Questoes": ConfiguracaoProva(
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

    # ---------------------------------------------------------
    # 2. PADRÃO 44 QUESTÕES (Ex: 4º ao 6º Ano) - 11 por bloco
    # ---------------------------------------------------------
    "44_Questoes": ConfiguracaoProva(
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

    # ---------------------------------------------------------
    # 3. PADRÃO 18 QUESTÕES (Ex: 1º ao 3º Ano) - 9 por bloco
    # ---------------------------------------------------------
    "18_Questoes": ConfiguracaoProva(
        titulo_prova="AVALIAÇÃO DE APRENDIZAGEM",
        subtitulo="Ensino Fundamental I - 1º ao 3º Ano",
        grids=[
            # Como são apenas 2 blocos de matérias, eles foram mais centralizados na página
            GridConfig("FREQ.", "", 0.15, 0.22, Y_TOP, Y_END_FREQ_09, 10, 2, ["D", "U"], 0, COR_LARANJA),
            GridConfig("BLOCO 1", "LÍNGUA PORTUGUESA", 0.32, 0.52, Y_TOP, Y_BOT, 9, 4, ["A","B","C","D"], 1, COR_AZUL),
            GridConfig("BLOCO 2", "MATEMÁTICA", 0.58, 0.78, Y_TOP, Y_BOT, 9, 4, ["A","B","C","D"], 10, COR_LARANJA),
        ]
    )
}
