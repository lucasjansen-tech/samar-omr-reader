import streamlit as st
import pandas as pd
from pdf2image import convert_from_bytes
from omr_engine import tratar_entrada, alinhar_gabarito, extrair_respostas

st.set_page_config(page_title="SAMAR OMR - Raposa", layout="wide")

# Exibição da Logo
try:
    st.image("Frame 18.png")
except:
    st.title("📊 SISTEMA SAMAR - RAPOSA")

st.write("### 📝 Configuração do Gabarito Oficial")

# Quadro de Seleção Dinâmico
with st.expander("Clique aqui para definir as respostas corretas", expanded=False):
    st.info("Selecione a alternativa correta para cada uma das 52 questões.")
    
    # Criamos colunas para organizar o quadro (4 colunas de 13 questões)
    cols = st.columns(4)
    gabarito_oficial = {}
    
    letras = ["A", "B", "C", "D"]
    
    for i in range(1, 53):
        col_idx = (i - 1) // 13
        with cols[col_idx]:
            gabarito_oficial[i] = st.selectbox(f"Q{i}", letras, key=f"q{i}")

# Upload de Arquivos
st.divider()
upload = st.file_uploader("Suba o PDF ou Imagens dos Gabaritos", type=["pdf", "png", "jpg"], accept_multiple_files=True)

if upload:
    todos_resultados = []
    
    for arq in upload:
        # Lógica para tratar PDF ou Imagem individual
        if arq.type == "application/pdf":
            paginas = convert_from_bytes(arq.read(), dpi=200)
        else:
            from PIL import Image
            paginas = [Image.open(arq)]

        for i, pagina_pil in enumerate(paginas):
            img_cv = tratar_entrada(pagina_pil)
            alinhada = alinhar_gabarito(img_cv)
            
            if alinhada is not None:
                resp_aluno = extrair_respostas(alinhada)
                
                # Comparação Automática com o Quadro de Seleção
                acertos = 0
                for q_num, marcacao in resp_aluno.items():
                    if marcacao == gabarito_oficial.get(q_num):
                        acertos += 1
                
                # Consolidação de dados
                dados_final = {
                    "Arquivo": arq.name,
                    "Pag": i + 1,
                    "Acertos": acertos,
                    "Nota %": f"{(acertos/52)*100:.1f}%"
                }
                # Adiciona as marcações do aluno para conferência
                dados_final.update(resp_aluno)
                todos_resultados.append(dados_final)
                st.success(f"✅ {arq.name} (Pág {i+1}) processado!")
            else:
                st.error(f"❌ Erro ao alinhar {arq.name} (Pág {i+1})")

    if todos_resultados:
        st.subheader("📊 Relatório Consolidado")
        df = pd.DataFrame(todos_resultados)
        st.dataframe(df)
        
        # Download para Excel/CSV
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Baixar Planilha Completa", csv, "resultado_samar_raposa.csv", "text/csv")
