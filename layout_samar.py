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
    tem_frequencia: bool = True
    
    # --- GEOMETRIA DE SEGURANÇA ---
    PAGE_W = 595
    PAGE_H = 842
    
    # Aumentei para 45 para garantir que a impressora não corte a âncora
    MARGIN = 45  
    ANCORA_SIZE = 25
    
    # Posições (Ajustadas para subir o conteúdo)
    FREQ_X = 40
    GRID_START_Y = 670 # Subi para 670 para fugir das âncoras de baixo
    GRID_X_START = 110
    GRID_COL_W = 120

# --- CONFIGURAÇÃO DOS CABEÇALHOS E ANOS ---
# Aqui você define exatamente o que aparece escrito no topo da prova
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
            BlocoQuestao("BLOCO 1", "LÍNGUA PORTUGUESA", 1, 11, COR_AZUL),
            BlocoQuestao("BLOCO 2", "LÍNGUA PORTUGUESA", 12, 11, COR_AZUL),
            BlocoQuestao("BLOCO 3", "MATEMÁTICA", 23, 11, COR_LARANJA),
            BlocoQuestao("BLOCO 4", "MATEMÁTICA", 34, 11, COR_LARANJA)
        ]
    ),
    "7_ao_9_Ano_52Q": ConfiguracaoProva(
        titulo_prova="AVALIAÇÃO DE APRENDIZAGEM - 7º AO 9º ANO",
        subtitulo="Ensino Fundamental II - Rede Municipal",
        blocos=[
            BlocoQuestao("BLOCO 1", "LÍNGUA PORTUGUESA", 1, 13, COR_AZUL),
            BlocoQuestao("BLOCO 2", "LÍNGUA PORTUGUESA", 14, 13, COR_AZUL),
            BlocoQuestao("BLOCO 3", "MATEMÁTICA", 27, 13, COR_LARANJA),
            BlocoQuestao("BLOCO 4", "MATEMÁTICA", 40, 13, COR_LARANJA)
        ]
    )
}
