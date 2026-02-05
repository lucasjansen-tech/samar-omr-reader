import streamlit as st
import pandas as pd
from pdf2image import convert_from_bytes
from omr_engine import tratar_entrada, alinhar_gabarito, extrair_dados

st.set_page_config(page_title="SAMAR - SEMED Raposa", layout="wide")
st.title("📊 SAMAR - Processamento e Conferência")

# Gabarito Raiz
with st.expander("⚙️ Configurar Gabarito Raiz"):
    c = st.columns(4)
    gab_raiz = {i: c[(i-1)//13].selectbox(f"Q{i}", ["A","B","C","D"], key=f"r{i}") for i in range(1, 53)}

upload = st.file_uploader("Upload TESTE OMR.pdf", type=["pdf"])

if upload:
    paginas = convert_from_bytes(upload.read(), dpi=200)
    resultados = []

    for i, pag in enumerate(paginas):
        alinhada = alinhar_gabarito(tratar_entrada(pag))
        if alinhada is not None:
            dados, img_vis = extrair_dados(alinhada)
            acertos = sum(1 for q, r in dados["respostas"].items() if r == gab_raiz.get(q))
            
            res_row = {"Página": i+1, "Freq": dados["frequencia"], "Acertos": acertos}
            res_row.update(dados["respostas"])
            resultados.append(res_row)
            
            # Mostra a imagem de conferência ampliada para validar os pontos
            st.image(img_vis, caption=f"Verificação Visual - Página {i+1}", use_container_width=True)
        else:
            st.error(f"Página {i+1}: Erro de alinhamento das âncoras.")

    if resultados:
        df = pd.DataFrame(resultados)
        st.subheader("📋 Tabela de Resultados")
        st.dataframe(df)

        # EXPORTAÇÃO CORRIGIDA PARA EXCEL/CSV BRASIL
        csv = df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button("📥 Baixar Planilha Corrigida (Excel)", csv, "resultados_samar.csv", "text/csv")
