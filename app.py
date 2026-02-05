import streamlit as st
import pandas as pd
from pdf2image import convert_from_bytes
from omr_engine import tratar_entrada, alinhar_gabarito, extrair_dados

st.set_page_config(page_title="SAMAR OMR - SEMED Raposa", layout="wide")
st.title("📊 SAMAR - Sistema de Auditoria de Gabaritos")

# Configuração do Gabarito Raiz
with st.sidebar:
    st.header("⚙️ Gabarito Oficial")
    c1, c2 = st.columns(2)
    gab_raiz = {}
    for i in range(1, 53):
        with (c1 if i <= 26 else c2):
            gab_raiz[i] = st.selectbox(f"Q{i}", ["A","B","C","D"], key=f"r{i}")

upload = st.file_uploader("Upload TESTE OMR.pdf", type=["pdf"])

if upload:
    paginas = convert_from_bytes(upload.read(), dpi=200)
    resultados = []

    for i, pag in enumerate(paginas):
        img_orig = tratar_entrada(pag)
        alinhada, img_diag = alinhar_gabarito(img_orig)
        
        if alinhada is not None:
            dados, img_vis = extrair_dados(alinhada, gab_raiz)
            acertos = sum(1 for q, r in dados["respostas"].items() if r == gab_raiz.get(q))
            
            res_row = {"Página": i+1, "Frequência": dados["frequencia"], "Acertos": acertos, "Nota": f"{(acertos/52)*100:.1f}%"}
            res_row.update(dados["respostas"])
            resultados.append(res_row)
            
            # Layout de Auditoria
            st.write(f"### Página {i+1} | Frequência Detectada: **{dados['frequencia']}**")
            st.image(img_vis, use_container_width=True)
        else:
            st.error(f"Página {i+1}: Erro de alinhamento. Mostrando diagnóstico:")
            st.image(img_diag, width=500)

    if resultados:
        df = pd.DataFrame(resultados)
        st.subheader("📋 Relatório Consolidado")
        st.dataframe(df)

        # Exportação para Excel (Configuração Brasil)
        csv = df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button("📥 Baixar Resultados para Excel", csv, "relatorio_samar.csv", "text/csv")
