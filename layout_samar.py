from dataclasses import dataclass
from typing import List

# Cores
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
    
    # GEOMETRIA A4
    PAGE_W = 595
    PAGE_H = 842
    
    # Margem e Tamanho da Âncora
    MARGIN = 35       
    ANCORA_SIZE = 30  
    
    # --- AJUSTES FINOS (Baseado no print image_2baf9f) ---
    # Empurrei a frequência para a direita (estava cortando a borda esquerda)
    FREQ_X: int = 42  
    
    # Baixei levemente a altura inicial (de 580 para 572) para centralizar na bolinha
    GRID_START_Y: int = 572 
    
    GRID_X_START: int = 115
    GRID_COL_W: int = 118   
    tem_frequencia: bool = True

# --- MODELOS ---
TIPOS_PROVA = {
    "2_e_3_Ano_18Q": ConfiguracaoProva(
        titulo_prova="AVALIAÇÃO DE APRENDIZAGEM",
        subtitulo="Ensino Fundamental I - 2º e 3º Ano",
        # Centralizado Verticalmente
        GRID_START_Y=450, 
        # Frequência centralizada
        FREQ_X=135,       
        GRID_X_START=210,
        blocos=[
            BlocoQuestao("BLOCO 1", "LÍNGUA PORTUGUESA", 1, 9, COR_AZUL),
            BlocoQuestao("BLOCO 2", "MATEMÁTICA", 10, 9, COR_LARANJA)
        ]
    ),
    "4_ao_6_Ano_44Q": ConfiguracaoProva(
        titulo_prova="AVALIAÇÃO DE APRENDIZAGEM",
        subtitulo="Ensino Fundamental - 4º ao 6º Ano",
        GRID_START_Y=572,
        FREQ_X=42, # Ajustado
        GRID_X_START=115,
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
        GRID_START_Y=572,
        FREQ_X=42, # Ajustado
        GRID_X_START=115,
        blocos=[
            BlocoQuestao("BLOCO 1", "LÍNGUA PORTUGUESA", 1, 13, COR_AZUL),
            BlocoQuestao("BLOCO 2", "LÍNGUA PORTUGUESA", 14, 13, COR_AZUL),
            BlocoQuestao("BLOCO 3", "MATEMÁTICA", 27, 13, COR_LARANJA),
            BlocoQuestao("BLOCO 4", "MATEMÁTICA", 40, 13, COR_LARANJA)
        ]
    )
}
