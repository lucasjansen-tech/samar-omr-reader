from dataclasses import dataclass
from typing import List, Tuple

# Definição de Cores Oficiais (Hex)
COR_AZUL = "#2980b9"   # Azul Sólido
COR_LARANJA = "#e67e22" # Laranja Sólido

@dataclass
class BlocoQuestao:
    titulo: str
    componente: str # Ex: "Língua Portuguesa"
    questao_inicial: int
    quantidade: int
    cor_hex: str = "#333333" # Cor do cabeçalho do bloco

@dataclass
class ConfiguracaoProva:
    titulo_prova: str
    subtitulo: str
    blocos: List[BlocoQuestao]
    tem_frequencia: bool = True
    
    # --- GEOMETRIA (Ajustada para "juntar" âncoras ao conteúdo) ---
    PAGE_W = 595
    PAGE_H = 842
    
    # Reduzi a margem para 20 (antes 30) para aproximar as âncoras da borda
    # Mas para "juntar ao gabarito", vamos aumentar a área útil.
    MARGIN = 25 
    ANCORA_SIZE = 25 # Âncoras um pouco maiores para facilitar leitura
    
    # Cabeçalho compacto
    HEADER_HEIGHT = 160 
    
    # Coordenadas
    # Frequência mais para a esquerda
    FREQ_X = 45 
    # Começa logo abaixo do cabeçalho
    FREQ_Y_START = 650 
    
    # Grade de Questões (Ajustada para caber blocos lado a lado com cores)
    GRID_START_Y = 650
    GRID_COL_W = 125 # Colunas mais largas para caber o título da matéria
    GRID_X_START = 120 # Espaço após a frequência

# --- DEFINIÇÃO DOS 3 PADRÕES ---
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
    "Reduzida_20_Questoes": ConfiguracaoProva(
        titulo_prova="AVALIAÇÃO PARCIAL",
        subtitulo="Verificação de Aprendizagem Bimestral",
        blocos=[
            BlocoQuestao("MATEMÁTICA", "Raciocínio Lógico", 1, 10, COR_LARANJA),
            BlocoQuestao("PORTUGUÊS", "Interpretação Textual", 11, 10, COR_AZUL)
        ]
    ),
    "Simulado_Geral": ConfiguracaoProva(
        titulo_prova="SIMULADO PREPARATÓRIO",
        subtitulo="Prova Geral - Todas as Disciplinas",
        blocos=[
            BlocoQuestao("LINGUAGENS", "Português e Inglês", 1, 15, COR_AZUL),
            BlocoQuestao("CIÊNCIAS", "Natureza e Matemática", 16, 15, COR_LARANJA),
            BlocoQuestao("HUMANAS", "História e Geografia", 31, 15, COR_AZUL)
        ]
    )
}
