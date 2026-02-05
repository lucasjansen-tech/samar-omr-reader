import streamlit as st
import pandas as pd
from pdf2image import convert_from_bytes
from omr_engine import tratar_entrada, alinhar_gabarito, extrair_respostas

st.set_page_config(page_title="SAMAR - SEMED Raposa", layout="wide")

# Tenta carregar a logo do repositório
try:
    st.image("Frame 18.png")
except:
    st.title("SISTEMA SAMAR - RAPOSA")

st.sidebar.header("⚙️ Configurações")
gab_oficial_input = st.sidebar.text_area("Insira o Gabarito Oficial (Separado por vírgula ou espaço)", height=150)

upload = st.file_uploader("Suba o arquivo PDF com os gabaritos", type=["pdf", "png", "jpg"])

if upload:
    # Converte PDF para imagens
    if upload.type == "application/pdf":
        paginas = convert_from_bytes(upload.read(), dpi=200)
    else:
        from PIL import Image
        paginas = [Image.open(upload)]

    resultados = []
    
    # Processa cada página/gabarito
    for i, pagina_pil in enumerate(paginas):
        img_cv = tratar_entrada(pagina_pil)
        alinhada = alinhar_gabarito(img_cv)
        
        if alinhada is not None:
            resp_aluno = extrair_respostas(alinhada)
            resp_aluno["Gabarito_ID"] = i + 1
            resultados.append(resp_aluno)
            st.success(f"Gabarito {i+1} processado com sucesso!")
        else:
            st.error(f"Não foi possível localizar as âncoras na página {i+1}")

    if resultados:
        df = pd.DataFrame(resultados)
        st.subheader("📊 Resultados Extraídos")
        st.dataframe(df)
        
        # Exportação
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Baixar Planilha de Resultados", csv, "resultados_samar.csv", "text/csv")
