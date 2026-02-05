import streamlit as st
import pandas as pd
from pdf2image import convert_from_bytes
from omr_engine import tratar_entrada, alinhar_gabarito, extrair_dados

st.set_page_config(page_title="SAMAR OMR", layout="wide")
st.title("📊 Auditoria SAMAR - SEMED Raposa")

with st.sidebar:
    st.header("⚙️ Gabarito Oficial")
    gab_oficial = {i: st.selectbox(f"Q{i}", ["A","B","C","D"], key=f"q{i}") for i in range(1, 53)}

upload = st.file_uploader("Upload TESTE OMR.pdf", type=["pdf"])

if upload:
    paginas = convert_from_bytes(upload.read(), dpi=200)
    resultados = []

    for i, pag in enumerate(paginas):
        img = tratar_entrada(pag)
        alinhada, img_diag = alinhar_gabarito(img)
        
        if alinhada is not None:
            dados, img_vis = extrair_dados(alinhada, gab_oficial)
            acertos = sum(1 for q, r in dados["respostas"].items() if r == gab_oficial.get(q))
            
            row = {"ID": i+1, "Freq": dados["frequencia"], "Acertos": acertos, "Nota": f"{(acertos/52)*100:.1f}%"}
            row.update(dados["respostas"])
            resultados.append(row)
            
            st.subheader(f"Página {i+1} | Frequência: {dados['frequencia']}")
            st.image(img_vis, use_container_width=True)
        else:
            st.error(f"Erro no alinhamento da página {i+1}.")
            st.image(img_diag, width=500, caption="Diagnóstico de Âncoras")

    if resultados:
        df = pd.DataFrame(resultados)
        st.subheader("📋 Relatório Consolidado")
        st.dataframe(df)
        csv = df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button("📥 Baixar Planilha para Excel", csv, "resultado_samar.csv", "text/csv")
