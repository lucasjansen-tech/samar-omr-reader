from dataclasses import dataclass
from typing import List

# CORES
COR_AZUL = "#2980b9"
COR_LARANJA = "#e67e22"

@dataclass
class BlocoQuestao:
    titulo: str
    componente: str
    questao_inicial: int
    quantidade: int
    cor_hex: str

@dataclass
class ConfiguracaoProva:
    titulo_prova: str
    subtitulo: str
    blocos: List[BlocoQuestao]
    
    # GEOMETRIA A4 (Pontos)
    PAGE_W = 595
    PAGE_H = 842
    MARGIN = 30       # Margem segura
    ANCORA_SIZE = 25  
    
    # Layout Padrão
    FREQ_X: int = 40
    GRID_START_Y: int = 580 
    GRID_X_START: int = 110
    GRID_COL_W: int = 120   
    tem_frequencia: bool = True

# --- DEFINIÇÃO DOS MODELOS ---
TIPOS_PROVA = {
    "2_e_3_Ano_18Q": ConfiguracaoProva(
        titulo_prova="AVALIAÇÃO DE APRENDIZAGEM",
        subtitulo="Ensino Fundamental I - 2º e 3º Ano",
        # AJUSTES DE POSIÇÃO:
        GRID_START_Y=480, # Centralizado verticalmente
        FREQ_X=120,       # Frequência mais à direita
        GRID_X_START=200, # AFASTADO DA FREQUÊNCIA (Era muito perto)
        
        blocos=[
            BlocoQuestao("BLOCO 1", "LÍNGUA PORTUGUESA", 1, 9, COR_AZUL),
            BlocoQuestao("BLOCO 2", "MATEMÁTICA", 10, 9, COR_LARANJA)
        ]
    ),
    "4_ao_6_Ano_44Q": ConfiguracaoProva(
        titulo_prova="AVALIAÇÃO DE APRENDIZAGEM",
        subtitulo="Ensino Fundamental - 4º ao 6º Ano",
        GRID_START_Y=580,
        FREQ_X=40,
        GRID_X_START=110,
        blocos=[
            BlocoQuestao("BLOCO 1", "LÍNGUA PORTUGUESA", 1, 11, COR_AZUL),
            BlocoQuestao("BLOCO 2", "LÍNGUA PORTUGUESA", 12, 11, COR_AZUL),
            BlocoQuestao("BLOCO 3", "MATEMÁTICA", 23, 11, COR_LARANJA),
            BlocoQuestao("BLOCO 4", "MATEMÁTICA", 34, 11, COR_LARANJA)
        ]
    ),
    "7_ao_9_Ano_52Q": ConfiguracaoProva(
        titulo_prova="AVALIAÇÃO DE APRENDIZAGEM",
        subtitulo="Ensino Fundamental II - 7º ao 9º Ano",
        GRID_START_Y=580,
        FREQ_X=40,
        GRID_X_START=110,
        blocos=[
            BlocoQuestao("BLOCO 1", "LÍNGUA PORTUGUESA", 1, 13, COR_AZUL),
            BlocoQuestao("BLOCO 2", "LÍNGUA PORTUGUESA", 14, 13, COR_AZUL),
            BlocoQuestao("BLOCO 3", "MATEMÁTICA", 27, 13, COR_LARANJA),
            BlocoQuestao("BLOCO 4", "MATEMÁTICA", 40, 13, COR_LARANJA)
        ]
    )
}
