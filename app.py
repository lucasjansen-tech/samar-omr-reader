import streamlit as st
import pandas as pd
from pdf2image import convert_from_bytes
from omr_engine import tratar_entrada, alinhar_gabarito, extrair_dados

st.set_page_config(page_title="SAMAR OMR", layout="wide")
st.title("📊 Correção SAMAR - SEMED Raposa")

with st.sidebar:
    st.header("📝 Gabarito")
    gab = {i: st.selectbox(f"Q{i}", ["A","B","C","D"], key=f"q{i}") for i in range(1, 53)}

upload = st.file_uploader("📂 Upload Provas (PDF)", type=["pdf"])

if upload:
    paginas = convert_from_bytes(upload.read(), dpi=200)
    resultados = []

    st.write(f"Analisando {len(paginas)} páginas...")
    
    # Criação de Abas
    tab_resultado, tab_debug = st.tabs(["✅ Resultados", "🛠️ Diagnóstico de Âncoras"])
    
    imagens_debug = [] # Armazena para mostrar na aba de debug

    with tab_resultado:
        for i, pag in enumerate(paginas):
            img_in = tratar_entrada(pag)
            
            # Tenta alinhar e recebe imagem de debug junto
            warped, img_ancoras_debug = alinhar_gabarito(img_in)
            imagens_debug.append(img_ancoras_debug)
            
            # Extração
            dados, img_mask = extrair_dados(warped, gab)
            
            acertos = sum(1 for q, r in dados["respostas"].items() if r == gab.get(q))
            
            linha = {"Página": i+1, "Freq": dados["frequencia"], "Acertos": acertos, "Nota": f"{(acertos/52)*100:.1f}%"}
            linha.update(dados["respostas"])
            resultados.append(linha)

            with st.expander(f"Aluno {i+1} (Freq: {dados['frequencia']})", expanded=(i==0)):
                st.image(img_mask, caption="Máscara Final", use_container_width=True)

        # Tabela e Download
        if resultados:
            df = pd.DataFrame(resultados)
            st.dataframe(df)
            csv = df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button("📥 Baixar Planilha", csv, "Resultado_SAMAR.csv", "text/csv")

    with tab_debug:
        st.warning("Verifique aqui se os quadrados pretos foram detectados (contorno Amarelo/Azul).")
        col1, col2 = st.columns(2)
        for idx, img in enumerate(imagens_debug):
            with (col1 if idx % 2 == 0 else col2):
                st.image(img, caption=f"Diagnóstico Pág {idx+1}", use_container_width=True)
