import streamlit as st
import pandas as pd
from pdf2image import convert_from_bytes
from omr_engine import tratar_entrada, alinhar_gabarito, extrair_dados

st.set_page_config(page_title="SAMAR - SEMED Raposa", layout="wide")

st.title("📊 SAMAR - Processamento e Auditoria Visual")

# Gabarito Raiz
with st.expander("⚙️ Configurar Gabarito Raiz (Respostas Corretas)"):
    c = st.columns(4)
    gab_raiz = {i: c[(i-1)//13].selectbox(f"Q{i}", ["A","B","C","D"], key=f"r{i}") for i in range(1, 53)}

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
            
            res_row = {"Arquivo": upload.name, "Página": i+1, "Freq": dados["frequencia"], "Acertos": acertos}
            res_row.update(dados["respostas"])
            resultados.append(res_row)
            
            # Auditoria Visual
            st.write(f"### Auditoria Página {i+1} (Freq: {dados['frequencia']})")
            col1, col2 = st.columns(2)
            col1.image(img_diag, caption="Diagnóstico de Âncoras (Vermelho)")
            col2.image(img_vis, caption="Validação de Respostas (Verde/Vermelho)")
        else:
            st.error(f"Página {i+1}: Âncoras não encontradas. Verifique se o papel não está cortado.")
            st.image(img_diag, caption="Falha no Alinhamento", width=400)

    if resultados:
        df = pd.DataFrame(resultados)
        st.subheader("📋 Tabela Consolidada")
        st.dataframe(df)

        # EXPORTAÇÃO CORRIGIDA (EXCEL BRASILEIRO)
        # O encoding utf-8-sig resolve caracteres estranhos no Excel
        csv = df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button("📥 Baixar Planilha para Excel", csv, "relatorio_samar.csv", "text/csv")
