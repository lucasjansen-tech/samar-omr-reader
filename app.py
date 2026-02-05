import streamlit as st
import pandas as pd
from pdf2image import convert_from_bytes
from omr_engine import tratar_entrada, alinhar_gabarito, extrair_respostas

st.set_page_config(page_title="SAMAR OMR - Raposa", layout="wide")

try:
    st.image("Frame 18.png")
except:
    st.title("SISTEMA SAMAR - SEMED RAPOSA")

st.sidebar.header("Configuração de Correção")
entrada_gab = st.text_input("Gabarito Oficial (ex: ABCD...)", "").upper()

upload = st.file_uploader("Suba o PDF com os gabaritos", type=["pdf", "jpg", "png"])

if upload:
    if upload.type == "application/pdf":
        paginas = convert_from_bytes(upload.read(), dpi=200)
    else:
        from PIL import Image
        paginas = [Image.open(upload)]
    
    resultados = []
    for i, pagina in enumerate(paginas):
        img = tratar_entrada(pagina)
        alinhada = alinhar_gabarito(img)
        if alinhada is not None:
            res = extrair_respostas(alinhada)
            res["ID_Gabarito"] = i + 1
            resultados.append(res)
    
    if resultados:
        df = pd.DataFrame(resultados)
        st.subheader("📋 Resultados Extraídos")
        st.dataframe(df)
        st.download_button("Baixar CSV", df.to_csv(index=False).encode('utf-8'), "samar_resultados.csv")
