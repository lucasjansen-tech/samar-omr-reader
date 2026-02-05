import streamlit as st
import pandas as pd
from pdf2image import convert_from_bytes
from omr_engine import tratar_entrada, alinhar_gabarito, extrair_respostas

st.set_page_config(page_title="SAMAR OMR - Raposa", layout="wide")

# Tenta carregar a logo do repositório
try:
    st.image("Frame 18.png")
except:
    st.title("SISTEMA SAMAR - SEMED RAPOSA")

st.sidebar.header("Configurações de Correção")
gabarito_oficial = st.text_input("Gabarito Oficial (ex: ABCD...)", "").upper()

upload = st.file_uploader("Suba o arquivo PDF (com vários gabaritos)", type="pdf")

if upload:
    # Processa PDF em lote (lida com várias páginas/gabaritos)
    paginas = convert_from_bytes(upload.read(), dpi=200)
    resultados = []

    for i, pagina_pil in enumerate(paginas):
        img_cv = tratar_entrada(pagina_pil)
        alinhada = alinhar_gabarito(img_cv)
        
        if alinhada is not None:
            respostas = extrair_respostas(alinhada)
            respostas["Pagina"] = i + 1
            
            # Se houver gabarito oficial, calcula acertos
            if gabarito_oficial and len(gabarito_oficial) >= 52:
                acertos = sum(1 for q, r in respostas.items() if q != "Pagina" and r == gabarito_oficial[q-1])
                respostas["Acertos"] = acertos
            
            resultados.append(respostas)

    if resultados:
        df = pd.DataFrame(resultados)
        st.subheader("📊 Resultados Extraídos")
        st.dataframe(df)
        st.download_button("Baixar Planilha (CSV)", df.to_csv(index=False).encode('utf-8'), "resultados_samar.csv")