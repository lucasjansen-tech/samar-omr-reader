import streamlit as st
import pandas as pd
from pdf2image import convert_from_bytes
from omr_engine import tratar_entrada, alinhar_gabarito, extrair_dados

st.set_page_config(page_title="SAMAR OMR", layout="wide")
st.title("📊 Correção SAMAR - Versão Final Ajustada")

with st.sidebar:
    st.header("⚙️ Configurações")
    modo_debug = st.checkbox("Modo Debug (Ver Grade)", value=False)
    st.divider()
    st.header("📝 Gabarito")
    gab = {i: st.selectbox(f"Q{i}", ["A","B","C","D"], key=f"q{i}") for i in range(1, 53)}

upload = st.file_uploader("📂 Upload Provas (PDF)", type=["pdf"])

if upload:
    paginas = convert_from_bytes(upload.read(), dpi=200)
    resultados = []

    st.write(f"Processando {len(paginas)} páginas...")
    
    for i, pag in enumerate(paginas):
        img_in = tratar_entrada(pag)
        
        # Alinhamento
        warped = alinhar_gabarito(img_in)
        
        # Extração
        dados, img_mask = extrair_dados(warped, gab)
        
        acertos = sum(1 for q, r in dados["respostas"].items() if r == gab.get(q))
        
        linha = {
            "Página": i+1, 
            "Frequência": dados["frequencia"], 
            "Acertos": acertos, 
            "Nota": f"{(acertos/52)*100:.1f}%"
        }
        linha.update(dados["respostas"])
        resultados.append(linha)

        # Visualização
        with st.expander(f"Aluno {i+1} (Freq: {dados['frequencia']}) - Nota: {acertos}/52", expanded=(i==0)):
            if modo_debug:
                 # Mostra a imagem alinhada crua para ver se está torta
                 st.image(warped, caption="Imagem Alinhada (Crua)", width=400)
            st.image(img_mask, caption="Máscara de Correção", use_container_width=True)

    if resultados:
        st.divider()
        df = pd.DataFrame(resultados)
        
        # Ordenação Colunas
        cols_fixas = ["Página", "Frequência", "Acertos", "Nota"]
        cols_questoes = [i for i in range(1, 53) if i in df.columns] # Garante que existem
        df = df[cols_fixas + cols_questoes]
        
        st.dataframe(df)
        
        csv = df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button("📥 Baixar Planilha (.csv)", csv, "Resultado_SAMAR.csv", "text/csv")
