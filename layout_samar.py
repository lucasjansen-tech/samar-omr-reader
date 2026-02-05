from dataclasses import dataclass
from typing import List

@dataclass
class BlocoQuestao:
    titulo: str
    questao_inicial: int
    quantidade: int

@dataclass
class ConfiguracaoProva:
    titulo_prova: str
    subtitulo: str
    blocos: List[BlocoQuestao]
    tem_frequencia: bool = True
    
    # CONSTANTES GEOMÉTRICAS (A4 em Pontos: 595x842)
    PAGE_W = 595
    PAGE_H = 842
    ANCORA_SIZE = 20
    MARGIN = 30
    
    # Coordenadas Frequência
    FREQ_X = 50
    FREQ_Y_START = 622 # (842 - 220)
    
    # Coordenadas Questões
    GRID_START_Y = 622
    GRID_COL_W = 110
    GRID_X_START = 140

# DEFINIÇÃO DOS MODELOS
TIPOS_PROVA = {
    "Padrao_52": ConfiguracaoProva(
        titulo_prova="AVALIAÇÃO PADRÃO SAMAR",
        subtitulo="Ensino Fundamental - 52 Questões",
        blocos=[
            BlocoQuestao("BLOCO 1", 1, 13),
            BlocoQuestao("BLOCO 2", 14, 13),
            BlocoQuestao("BLOCO 3", 27, 13),
            BlocoQuestao("BLOCO 4", 40, 13)
        ]
    ),
    "Simulado_20": ConfiguracaoProva(
        titulo_prova="SIMULADO RÁPIDO",
        subtitulo="Matemática e Português",
        blocos=[
            BlocoQuestao("MATEMÁTICA", 1, 10),
            BlocoQuestao("PORTUGUÊS", 11, 10)
        ]
    )
}
