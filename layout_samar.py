from dataclasses import dataclass
from typing import List

# --- CORES OFICIAIS ---
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
    
    # --- GEOMETRIA DA PÁGINA (A4: 595 x 842) ---
    PAGE_W = 595
    PAGE_H = 842
    
    # MARGEM: 40px em cima e 40px embaixo (SIMETRIA DAS ÂNCORAS)
    MARGIN = 40       
    ANCORA_SIZE = 25  
    
    # Posições Padrão
    FREQ_X = 40
    GRID_X_START = 110          
    GRID_COL_W = 120   
    
    # Posição Vertical Personalizada (Define onde começa a grade)
    # Isso permite centralizar provas pequenas e subir provas grandes
    GRID_START_Y: int = 580 
    
    tem_frequencia: bool = True

# --- DEFINIÇÃO DOS 3 PADRÕES ---
TIPOS_PROVA = {
    "2_e_3_Ano_18Q": ConfiguracaoProva(
        titulo_prova="AVALIAÇÃO DE APRENDIZAGEM",
        subtitulo="Ensino Fundamental I",
        # CENTRALIZAÇÃO: Começa em 430 para ficar no MEIO da página
        GRID_START_Y=430, 
        blocos=[
            BlocoQuestao("BLOCO 1", "LÍNGUA PORTUGUESA", 1, 9, COR_AZUL),
            BlocoQuestao("BLOCO 2", "MATEMÁTICA", 10, 9, COR_LARANJA)
        ]
    ),
    "4_ao_6_Ano_44Q": ConfiguracaoProva(
        titulo_prova="AVALIAÇÃO DE APRENDIZAGEM",
        subtitulo="Ensino Fundamental - 4º ao 6º Ano",
        # Começa mais alto para caber as 44 questões
        GRID_START_Y=580, 
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
        # Começa alto para caber 52 questões sem bater no cabeçalho
        GRID_START_Y=580, 
        blocos=[
            BlocoQuestao("BLOCO 1", "LÍNGUA PORTUGUESA", 1, 13, COR_AZUL),
            BlocoQuestao("BLOCO 2", "LÍNGUA PORTUGUESA", 14, 13, COR_AZUL),
            BlocoQuestao("BLOCO 3", "MATEMÁTICA", 27, 13, COR_LARANJA),
            BlocoQuestao("BLOCO 4", "MATEMÁTICA", 40, 13, COR_LARANJA)
        ]
    )
}
