import streamlit as st
import pandas as pd
from pdf2image import convert_from_bytes
from omr_engine import tratar_entrada, alinhar_gabarito, extrair_dados

st.set_page_config(page_title="SAMAR OMR", layout="wide")
st.title("📊 Correção SAMAR - Raposa")

with st.sidebar:
    st.header("📝 Gabarito")
    gab = {i: st.selectbox(f"Q{i}", ["A","B","C","D"], key=f"q{i}") for i in range(1, 53)}

upload = st.file_uploader("📂 Upload Provas (PDF)", type=["pdf"])

if upload:
    paginas = convert_from_bytes(upload.read(), dpi=200)
    resultados = []

    st.write(f"Processando {len(paginas)} páginas...")
    
    # ABAS DE CONTROLE
    tab_res, tab_diag = st.tabs(["✅ Resultados & Máscaras", "🛠️ Diagnóstico de Âncoras"])
    
    debug_imgs = []

    with tab_res:
        for i, pag in enumerate(paginas):
            img_in = tratar_entrada(pag)
            
            # Alinhamento
            warped, img_ancora_debug = alinhar_gabarito(img_in)
            debug_imgs.append(img_ancora_debug)
            
            # Leitura
            dados, img_mask = extrair_dados(warped, gab)
            
            acertos = sum(1 for q, r in dados["respostas"].items() if r == gab.get(q))
            
            linha = {"Pág": i+1, "Freq": dados["frequencia"], "Acertos": acertos, "Nota": f"{(acertos/52)*100:.1f}%"}
            linha.update(dados["respostas"])
            resultados.append(linha)

            with st.expander(f"Aluno {i+1} (Freq: {dados['frequencia']})", expanded=(i==0)):
                st.image(img_mask, caption="Máscara de Correção", use_container_width=True)

        if resultados:
            df = pd.DataFrame(resultados)
            
            # Download
            csv = df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
            st.download_button("📥 Baixar Planilha (.csv)", csv, "Resultado_SAMAR.csv", "text/csv")
            
            st.divider()
            st.dataframe(df)

    with tab_diag:
        st.warning("Verifique aqui se os quadrados pretos foram detectados (Amarelo) e selecionados (Azul).")
        col1, col2 = st.columns(2)
        for idx, img in enumerate(debug_imgs):
            with (col1 if idx % 2 == 0 else col2):
                st.image(img, caption=f"Página {idx+1}", use_container_width=True)
