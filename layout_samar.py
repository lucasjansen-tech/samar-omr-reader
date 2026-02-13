from dataclasses import dataclass
from typing import List

# Cores Oficiais (Corrigidas conforme sua imagem)
COR_AZUL = "#2980b9"    # Blocos 1 e 2 (Português)
COR_LARANJA = "#e67e22" # Blocos 3 e 4 (Matemática)

@dataclass
class GridConfig:
    titulo: str
    # Coordenadas em PORCENTAGEM (0.0 a 1.0 da página)
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
    # Resolução base para cálculos internos (A4 alta resolução)
    REF_W = 1240 
    REF_H = 1754
    MARGIN_PCT = 0.05 

# --- MODELO 52 QUESTÕES (Alinhamento Visual Exato) ---
# Definindo as alturas úteis baseadas no cabeçalho e rodapé da sua imagem
Y_TOP = 0.32  # Começa logo abaixo do cabeçalho
Y_BOT = 0.91  # Vai até perto do rodapé

TIPOS_PROVA = {
    "52_Questoes_Grid": ConfiguracaoProva(
        titulo_prova="AVALIAÇÃO DE APRENDIZAGEM",
        subtitulo="Ensino Fundamental II - 7º ao 9º Ano",
        grids=[
            # FREQUÊNCIA (Coluna Estreita à Esquerda - Laranja)
            GridConfig("FREQ.", 0.05, 0.12, Y_TOP, 0.62, 10, 2, ["D", "U"], 0, COR_LARANJA),
            
            # BLOCO 1 (Português - AZUL)
            GridConfig("BLOCO 1", 0.16, 0.33, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 1, COR_AZUL),
            
            # BLOCO 2 (Português - AZUL)
            GridConfig("BLOCO 2", 0.37, 0.54, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 14, COR_AZUL),
            
            # BLOCO 3 (Matemática - LARANJA)
            GridConfig("BLOCO 3", 0.58, 0.75, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 27, COR_LARANJA),
            
            # BLOCO 4 (Matemática - LARANJA)
            GridConfig("BLOCO 4", 0.79, 0.96, Y_TOP, Y_BOT, 13, 4, ["A","B","C","D"], 40, COR_LARANJA),
        ]
    )
}
