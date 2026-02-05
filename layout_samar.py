from dataclasses import dataclass
from typing import List

# --- CORES OFICIAIS (Identidade Visual SEMED Raposa) ---
COR_AZUL = "#2980b9"    # Azul Institucional
COR_LARANJA = "#e67e22" # Laranja de Destaque

@dataclass
class BlocoQuestao:
    titulo: str          # Ex: "BLOCO 1"
    componente: str      # Ex: "Língua Portuguesa"
    questao_inicial: int
    quantidade: int
    cor_hex: str         # Cor do cabeçalho do bloco

@dataclass
class ConfiguracaoProva:
    titulo_prova: str
    subtitulo: str
    blocos: List[BlocoQuestao]
    tem_frequencia: bool = True
    
    # --- GEOMETRIA DA FOLHA (A4: 595 x 842 pontos) ---
    PAGE_W = 595
    PAGE_H = 842
    
    MARGIN = 25       # Margem externa
    ANCORA_SIZE = 25  # Tamanho dos quadrados pretos (âncoras)
    
    # Posições
    FREQ_X = 40                 # Coluna da Frequência
    GRID_START_Y = 630          # Altura onde começam as bolinhas
    GRID_X_START = 110          # Margem esquerda dos blocos de questões
    GRID_COL_W = 120            # Largura da coluna de cada bloco

# --- DEFINIÇÃO DOS MODELOS DE PROVA ---
TIPOS_PROVA = {
    "Padrao_52_Questoes": ConfiguracaoProva(
        titulo_prova="AVALIAÇÃO DE APRENDIZAGEM - SAMAR",
        subtitulo="Ensino Fundamental - Rede Municipal de Raposa",
        blocos=[
            BlocoQuestao("BLOCO 1", "LÍNGUA PORTUGUESA", 1, 13, COR_AZUL),
            BlocoQuestao("BLOCO 2", "MATEMÁTICA", 14, 13, COR_LARANJA),
            BlocoQuestao("BLOCO 3", "CIÊNCIAS / HUMANAS", 27, 13, COR_AZUL),
            BlocoQuestao("BLOCO 4", "LINGUAGENS / ARTE", 40, 13, COR_LARANJA)
        ]
    ),
    "Simulado_Geral_45": ConfiguracaoProva(
        titulo_prova="SIMULADO PREPARATÓRIO SAMAR",
        subtitulo="Avaliação Geral Integrada",
        blocos=[
            BlocoQuestao("LINGUAGENS", "Português, Arte e Inglês", 1, 15, COR_AZUL),
            BlocoQuestao("CIÊNCIAS DA NATUREZA", "Matemática e Ciências", 16, 15, COR_LARANJA),
            BlocoQuestao("CIÊNCIAS HUMANAS", "História e Geografia", 31, 15, COR_AZUL)
        ]
    ),
    "Parcial_20_Questoes": ConfiguracaoProva(
        titulo_prova="AVALIAÇÃO PARCIAL BIMESTRAL",
        subtitulo="Verificação de Aprendizagem Focada",
        blocos=[
            BlocoQuestao("MATEMÁTICA", "Raciocínio Lógico", 1, 10, COR_LARANJA),
            BlocoQuestao("LÍNGUA PORTUGUESA", "Interpretação e Gramática", 11, 10, COR_AZUL)
        ]
    )
}
