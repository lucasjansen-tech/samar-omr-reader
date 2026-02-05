import streamlit as st
import pandas as pd
from pdf2image import convert_from_bytes
from omr_engine import tratar_entrada, alinhar_gabarito, extrair_dados
import io

st.set_page_config(page_title="SAMAR OMR - Raposa", layout="wide")

st.title("📊 SAMAR - Teste Inicial de Leitura")

# Quadro de Seleção do Gabarito Raiz
with st.expander("⚙️ Definir Gabarito Oficial", expanded=False):
    cols = st.columns(4)
    gabarito_raiz = {}
    for i in range(1, 53):
        with cols[(i-1)//13]:
            gabarito_raiz[i] = st.selectbox(f"Q{i}", ["A", "B", "C", "D"], key=f"gr{i}")

upload = st.file_uploader("Suba o arquivo TESTE OMR.pdf", type=["pdf"])

if upload:
    conteudo = upload.read()
    paginas = convert_from_bytes(conteudo, dpi=200)
    lista_final = []

    for i, pag in enumerate(paginas):
        img_cv = tratar_entrada(pag)
        alinhada = alinhar_gabarito(img_cv)
        
        if alinhada is not None:
            dados, img_debug = extrair_dados(alinhada)
            
            # Cálculo de Acertos
            acertos = sum(1 for q, r in dados["respostas"].items() if r == gabarito_raiz.get(q))
            
            info = {
                "Página": i + 1,
                "Frequência": dados["frequencia"],
                "Acertos": acertos,
                "Nota %": f"{(acertos/52)*100:.1f}%"
            }
            info.update(dados["respostas"])
            lista_final.append(info)
            
            st.image(img_debug, caption=f"Conferência Página {i+1}", width=400)
        else:
            st.error(f"Página {i+1}: Erro ao localizar âncoras.")

    if lista_final:
        df = pd.DataFrame(lista_final)
        st.subheader("📋 Resultados da Leitura")
        st.dataframe(df)
        
        # Exportação para CSV (Excel)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Baixar Planilha de Resultados", csv, "resultados_teste_samar.csv", "text/csv")
