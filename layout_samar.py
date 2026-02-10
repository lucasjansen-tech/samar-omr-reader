from dataclasses import dataclass
from typing import List

# Cores da Identidade Visual
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
    
    # --- GEOMETRIA DA FOLHA (Sistema de Coordenadas Universal) ---
    # Baseado em A4 a 72dpi (padrão PDF): 595 x 842 pontos
    PAGE_W = 595
    PAGE_H = 842
    
    # Margem das Âncoras (Essencial para o alinhamento)
    # Aumentado para 35 para afastar da borda física do papel
    MARGIN = 35       
    ANCORA_SIZE = 30  
    
    # Posições Padrão (Podem ser sobrescritas por modelo)
    FREQ_X: int = 40
    GRID_START_Y: int = 580 
    GRID_X_START: int = 110
    GRID_COL_W: int = 120   
    tem_frequencia: bool = True

# --- DEFINIÇÃO DOS 3 PADRÕES DE PROVA ---
TIPOS_PROVA = {
    "2_e_3_Ano_18Q": ConfiguracaoProva(
        titulo_prova="AVALIAÇÃO DIAGNÓSTICA",
        subtitulo="Ensino Fundamental I - 2º e 3º Ano",
        # Centralizado: Abaixamos o Y e empurramos o X
        GRID_START_Y=450, 
        FREQ_X=130,       
        GRID_X_START=200,
        blocos=[
            BlocoQuestao("BLOCO 1", "LÍNGUA PORTUGUESA", 1, 9, COR_AZUL),
            BlocoQuestao("BLOCO 2", "MATEMÁTICA", 10, 9, COR_LARANJA)
        ]
    ),
    "4_ao_6_Ano_44Q": ConfiguracaoProva(
        titulo_prova="AVALIAÇÃO DIAGNÓSTICA",
        subtitulo="Ensino Fundamental - 4º ao 6º Ano",
        GRID_START_Y=570,
        FREQ_X=35,
        GRID_X_START=105,
        blocos=[
            BlocoQuestao("BLOCO 1", "LÍNGUA PORTUGUESA", 1, 11, COR_AZUL),
            BlocoQuestao("BLOCO 2", "LÍNGUA PORTUGUESA", 12, 11, COR_AZUL),
            BlocoQuestao("BLOCO 3", "MATEMÁTICA", 23, 11, COR_LARANJA),
            BlocoQuestao("BLOCO 4", "MATEMÁTICA", 34, 11, COR_LARANJA)
        ]
    ),
    "7_ao_9_Ano_52Q": ConfiguracaoProva(
        titulo_prova="AVALIAÇÃO DIAGNÓSTICA",
        subtitulo="Ensino Fundamental II - 7º ao 9º Ano",
        GRID_START_Y=570,
        FREQ_X=35,
        GRID_X_START=105,
        blocos=[
            BlocoQuestao("BLOCO 1", "LÍNGUA PORTUGUESA", 1, 13, COR_AZUL),
            BlocoQuestao("BLOCO 2", "LÍNGUA PORTUGUESA", 14, 13, COR_AZUL),
            BlocoQuestao("BLOCO 3", "MATEMÁTICA", 27, 13, COR_LARANJA),
            BlocoQuestao("BLOCO 4", "MATEMÁTICA", 40, 13, COR_LARANJA)
        ]
    )
}
