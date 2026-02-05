# layout_samar.py
from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class BlocoQuestao:
    titulo: str
    questao_inicial: int
    quantidade: int
    colunas: int = 4 # A, B, C, D

@dataclass
class ConfiguracaoProva:
    titulo_prova: str
    subtitulo: str
    blocos: List[BlocoQuestao]
    tem_frequencia: bool = True
    
    # --- CONSTANTES GEOMÉTRICAS (Ajuste Fino) ---
    # Tamanho do PDF em pontos (A4)
    PAGE_W = 595
    PAGE_H = 842
    
    # Margens e Âncoras
    ANCORA_SIZE = 20
    MARGIN = 30
    HEADER_HEIGHT = 150 # Espaço reservado para cabeçalho/orientações
    
    # Coordenadas do bloco de Frequência
    FREQ_X = 50
    FREQ_Y_START = PAGE_H - 220
    
    # Grid de Questões
    GRID_START_Y = PAGE_H - 220
    GRID_COL_W = 110 # Largura da coluna de um bloco
    GRID_X_START = 140 # Onde começam os blocos (após a frequência)

# DEFINIÇÃO DOS 3 TIPOS DE PROVA (Personalize aqui)
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
    "Reduzida_20": ConfiguracaoProva(
        titulo_prova="AVALIAÇÃO PARCIAL",
        subtitulo="Matemática e Português - 20 Questões",
        blocos=[
            BlocoQuestao("MATEMÁTICA", 1, 10),
            BlocoQuestao("PORTUGUÊS", 11, 10)
        ]
    ),
    "Simulado_Total": ConfiguracaoProva(
        titulo_prova="SIMULADO GERAL",
        subtitulo="Todas as matérias",
        blocos=[
            BlocoQuestao("LINGUAGENS", 1, 15),
            BlocoQuestao("CIÊNCIAS", 16, 15),
            BlocoQuestao("HUMANAS", 31, 15)
        ]
    )
}
