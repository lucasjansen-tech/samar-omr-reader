import streamlit as st
import pandas as pd
from pdf2image import convert_from_bytes
from omr_engine import tratar_entrada, alinhar_gabarito, extrair_dados

st.set_page_config(page_title="SAMAR OMR", layout="wide")
st.title("📊 Auditoria SAMAR - Corte por Âncoras")

with st.sidebar:
    st.header("⚙️ Gabarito Oficial")
    gab = {i: st.selectbox(f"Q{i}", ["A","B","C","D"], key=f"q{i}") for i in range(1, 53)}

upload = st.file_uploader("Upload PDF (TesteOMR.pdf)", type=["pdf"])

if upload:
    paginas = convert_from_bytes(upload.read(), dpi=200)
    resultados = []

    # Abas para organizar a tela
    tab1, tab2 = st.tabs(["🔍 Diagnóstico Visual", "📋 Tabela de Notas"])

    with tab1:
        for i, pag in enumerate(paginas):
            img_in = tratar_entrada(pag)
            warped, debug_ancoras = alinhar_gabarito(img_in)
            
            if warped is not None:
                dados, visual_final = extrair_dados(warped, gab)
                
                # Cálculos
                acertos = sum(1 for q, r in dados["respostas"].items() if r == gab.get(q))
                res_row = {"Pág": i+1, "Freq": dados["frequencia"], "Acertos": acertos}
                res_row.update(dados["respostas"])
                resultados.append(res_row)

                st.markdown(f"**Página {i+1}** | Frequência: `{dados['frequencia']}`")
                
                # Mostra o antes e depois lado a lado
                c1, c2 = st.columns(2)
                c1.image(debug_ancoras, caption="1. Detecção das 4 Âncoras (Vermelho)", use_container_width=True)
                c2.image(visual_final, caption="2. Leitura Recortada (Verde=Aluno)", use_container_width=True)
                st.divider()
            else:
                st.error(f"Falha na Pág {i+1}: Não encontrei os 4 quadrados pretos.")
                st.image(debug_ancoras, width=400)

    with tab2:
        if resultados:
            df = pd.DataFrame(resultados)
            st.dataframe(df)
            csv = df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button("📥 Baixar Relatório (Excel)", csv, "samar_notas.csv", "text/csv")
