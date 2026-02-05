import streamlit as st
import pandas as pd
from pdf2image import convert_from_bytes
from omr_engine import tratar_entrada, alinhar_gabarito, extrair_dados

st.set_page_config(page_title="SAMAR OMR", layout="wide")
st.title("📊 Correção SAMAR - SEMED Raposa")

with st.sidebar:
    st.header("📝 Gabarito Oficial")
    gab = {i: st.selectbox(f"Q{i}", ["A","B","C","D"], key=f"q{i}") for i in range(1, 53)}

upload = st.file_uploader("📂 Upload Provas (PDF)", type=["pdf"])

if upload:
    paginas = convert_from_bytes(upload.read(), dpi=200)
    resultados = []

    st.write(f"Analisando {len(paginas)} páginas...")
    
    for i, pag in enumerate(paginas):
        img_in = tratar_entrada(pag)
        # Processamento
        warped = alinhar_gabarito(img_in)
        dados, img_mask = extrair_dados(warped, gab)
        
        # Notas
        acertos = sum(1 for q, r in dados["respostas"].items() if r == gab.get(q))
        
        # Tabela
        linha = {"Página": i+1, "Frequência": dados["frequencia"], "Acertos": acertos, "Nota": f"{(acertos/52)*100:.1f}%"}
        linha.update(dados["respostas"])
        resultados.append(linha)

        # Exibição
        with st.expander(f"Aluno {i+1} (Freq: {dados['frequencia']}) - Acertos: {acertos}", expanded=(i==0)):
            c1, c2 = st.columns([1, 2])
            with c1:
                st.info("Legenda da Máscara:")
                st.markdown("🟢 **Verde Cheio:** Acerto")
                st.markdown("🔴 **Vermelho Cheio:** Erro")
                st.markdown("⭕ **Anel Verde:** Era a correta")
            with c2:
                st.image(img_mask, caption="Máscara de Correção", use_container_width=True)

    if resultados:
        st.divider()
        df = pd.DataFrame(resultados)
        
        # Ordenação de colunas
        cols = ["Página", "Frequência", "Acertos", "Nota"] + [i for i in range(1, 53)]
        cols = [c for c in cols if c in df.columns]
        st.dataframe(df[cols])
        
        # Download
        csv = df[cols].to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button("📥 Baixar Planilha (.csv)", csv, "Resultado_SAMAR.csv", "text/csv")
