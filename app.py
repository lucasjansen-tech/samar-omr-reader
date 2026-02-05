import streamlit as st
import pandas as pd
from pdf2image import convert_from_bytes
from omr_engine import tratar_entrada, alinhar_gabarito, extrair_dados

st.set_page_config(page_title="SAMAR OMR", layout="wide")
st.title("📊 Auditoria SAMAR - SEMED Raposa")

with st.sidebar:
    st.header("⚙️ Gabarito Oficial")
    gab_oficial = {i: st.selectbox(f"Q{i}", ["A","B","C","D"], key=f"q{i}") for i in range(1, 53)}

upload = st.file_uploader("Suba o PDF (TesteOMR.7-9.pdf)", type=["pdf"])

if upload:
    # Aumentando DPI para garantir qualidade na conversão
    paginas = convert_from_bytes(upload.read(), dpi=200) 
    resultados = []

    for i, pag in enumerate(paginas):
        # Passo 1: Pré-processamento
        img = tratar_entrada(pag)
        
        # Passo 2: Alinhamento Robusto
        warped, edged_debug = alinhar_gabarito(img)
        
        # Passo 3: Extração com Grade Visual
        dados, img_vis = extrair_dados(warped, gab_oficial)
        
        # Estatísticas
        acertos = sum(1 for q, r in dados["respostas"].items() if r == gab_oficial.get(q))
        nota = (acertos/52)*100
        
        # Salvando dados
        res_row = {
            "ID": i+1, 
            "Frequência": dados["frequencia"], 
            "Acertos": acertos, 
            "Nota": f"{nota:.1f}%"
        }
        res_row.update(dados["respostas"])
        resultados.append(res_row)
        
        # --- ÁREA DE AUDITORIA VISUAL ---
        with st.expander(f"Página {i+1} - Frequência: {dados['frequencia']} (Clique para ver detalhes)", expanded=True):
            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(edged_debug, caption="Detecção de Bordas (Diagnóstico)", use_container_width=True)
                st.info("A imagem acima mostra o que o computador 'enxerga' para alinhar a folha.")
            with col2:
                st.image(img_vis, caption="Leitura da Grade (Verde=Aluno, Vermelho=Gabarito)", use_container_width=True)

    if resultados:
        st.divider()
        df = pd.DataFrame(resultados)
        st.subheader("📋 Relatório Final Consolidado")
        st.dataframe(df)
        
        csv = df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button("📥 Baixar Planilha (Excel)", csv, "relatorio_samar_raposa.csv", "text/csv")
