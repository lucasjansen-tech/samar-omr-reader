from dataclasses import dataclass
from typing import List, Tuple

# Cores
COR_AZUL = "#2980b9"
COR_LARANJA = "#e67e22"

@dataclass
class GridConfig:
    titulo: str
    x_start_pct: float  # Onde começa (0.0 a 1.0 da largura)
    x_end_pct: float    # Onde termina
    y_start_pct: float  # Onde começa a primeira bolinha
    y_end_pct: float    # Onde termina a última bolinha
    rows: int
    cols: int           # 4 para questões (ABCD), 2 para freq (DU)
    labels: List[str]   # Ex: ["A", "B", "C", "D"]
    questao_inicial: int = 0
    cor_hex: str = "#000000"

@dataclass
class ConfiguracaoProva:
    titulo_prova: str
    subtitulo: str
    grids: List[GridConfig]
    
    # Proporção A4 (Largura/Altura = 0.707)
    # Usaremos uma base de alta resolução para cálculos, mas a lógica é %
    REF_W = 1240
    REF_H = 1754
    
    MARGIN_PCT = 0.05 # 5% de margem para as âncoras

# --- DEFINIÇÃO DO MODELO 52 QUESTÕES (Baseado no seu A4 - 9.jpg) ---
# A altura útil para as questões vai de 32% (topo) a 90% (fundo) da página
Y_TOP = 0.32
Y_BOT = 0.90

TIPOS_PROVA = {
    "52_Questoes_Grid": ConfiguracaoProva(
        titulo_prova="AVALIAÇÃO DE APRENDIZAGEM",
        subtitulo="Ensino Fundamental - 4º ao 6º Ano",
        grids=[
            # GRID FREQUÊNCIA (Esquerda)
            GridConfig("FREQ.", 0.06, 0.14, Y_TOP, 0.60, 10, 2, ["D", "U"], 0, COR_AZUL),
            
            # GRID BLOCO 1 (Questões 01-13)
            GridConfig("BLOCO 1", 0.18, 0.35, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 1, COR_LARANJA),
            
            # GRID BLOCO 2 (Questões 14-26)
            GridConfig("BLOCO 2", 0.39, 0.56, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 14, COR_LARANJA),
            
            # GRID BLOCO 3 (Questões 27-39)
            GridConfig("BLOCO 3", 0.60, 0.77, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 27, COR_AZUL),
            
            # GRID BLOCO 4 (Questões 40-52)
            GridConfig("BLOCO 4", 0.81, 0.98, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 40, COR_AZUL),
        ]
    )
}
