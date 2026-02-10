from dataclasses import dataclass
from typing import List

# --- CORES OFICIAIS (Identidade Visual) ---
COR_AZUL = "#2980b9"    # Língua Portuguesa
COR_LARANJA = "#e67e22" # Matemática

@dataclass
class BlocoQuestao:
    titulo: str          # Ex: "BLOCO 1"
    componente: str      # Ex: "LÍNGUA PORTUGUESA"
    questao_inicial: int
    quantidade: int
    cor_hex: str         # Cor do cabeçalho

@dataclass
class ConfiguracaoProva:
    titulo_prova: str
    subtitulo: str
    blocos: List[BlocoQuestao]
    tem_frequencia: bool = True
    
    # --- GEOMETRIA DA FOLHA (A4: 595 x 842 pontos) ---
    PAGE_W = 595
    PAGE_H = 842
    
    # MARGEM DE SEGURANÇA AUMENTADA (45pts)
    # Isso move as âncoras para cima, longe da borda da impressora.
    MARGIN = 45       
    ANCORA_SIZE = 25  
    
    # Posições dos Elementos
    FREQ_X = 40                 
    GRID_START_Y = 660          # Subi um pouco para caber tudo com folga
    GRID_X_START = 110          
    GRID_COL_W = 120            

# --- DEFINIÇÃO DOS 3 PADRÕES DE ENSINO ---
TIPOS_PROVA = {
    "2_e_3_Ano_18Q": ConfiguracaoProva(
        titulo_prova="AVALIAÇÃO DE APRENDIZAGEM - 2º E 3º ANO",
        subtitulo="Ensino Fundamental I - Rede Municipal",
        blocos=[
            BlocoQuestao("BLOCO 1", "LÍNGUA PORTUGUESA", 1, 9, COR_AZUL),
            BlocoQuestao("BLOCO 2", "MATEMÁTICA", 10, 9, COR_LARANJA)
        ]
    ),
    "4_ao_6_Ano_44Q": ConfiguracaoProva(
        titulo_prova="AVALIAÇÃO DE APRENDIZAGEM - 4º AO 6º ANO",
        subtitulo="Ensino Fundamental - Rede Municipal",
        blocos=[
            # 22 de Português
            BlocoQuestao("BLOCO 1", "LÍNGUA PORTUGUESA", 1, 11, COR_AZUL),
            BlocoQuestao("BLOCO 2", "LÍNGUA PORTUGUESA", 12, 11, COR_AZUL),
            # 22 de Matemática
            BlocoQuestao("BLOCO 3", "MATEMÁTICA", 23, 11, COR_LARANJA),
            BlocoQuestao("BLOCO 4", "MATEMÁTICA", 34, 11, COR_LARANJA)
        ]
    ),
    "7_ao_9_Ano_52Q": ConfiguracaoProva(
        titulo_prova="AVALIAÇÃO DE APRENDIZAGEM - 7º AO 9º ANO",
        subtitulo="Ensino Fundamental II - Rede Municipal",
        blocos=[
            # 26 de Português
            BlocoQuestao("BLOCO 1", "LÍNGUA PORTUGUESA", 1, 13, COR_AZUL),
            BlocoQuestao("BLOCO 2", "LÍNGUA PORTUGUESA", 14, 13, COR_AZUL),
            # 26 de Matemática
            BlocoQuestao("BLOCO 3", "MATEMÁTICA", 27, 13, COR_LARANJA),
            BlocoQuestao("BLOCO 4", "MATEMÁTICA", 40, 13, COR_LARANJA)
        ]
    )
}
