import streamlit as st
import pandas as pd
from pdf2image import convert_from_bytes
from omr_engine import tratar_entrada, alinhar_gabarito, extrair_dados

st.set_page_config(page_title="SAMAR OMR", layout="wide")
st.title("📊 Correção SAMAR - SEMED Raposa")

# Sidebar para Gabarito
with st.sidebar:
    st.header("📝 Gabarito Oficial")
    gab = {i: st.selectbox(f"Q{i}", ["A","B","C","D"], key=f"q{i}") for i in range(1, 53)}

upload = st.file_uploader("Upload PDF (Provas)", type=["pdf"])

if upload:
    paginas = convert_from_bytes(upload.read(), dpi=200)
    resultados_finais = []

    # Barra de progresso para arquivos grandes
    progresso = st.progress(0)
    
    for i, pag in enumerate(paginas):
        img_in = tratar_entrada(pag)
        warped = alinhar_gabarito(img_in)
        
        if warped is not None:
            dados, img_mask = extrair_dados(warped, gab)
            
            # Contagem de Acertos
            acertos = sum(1 for q, r in dados["respostas"].items() if r == gab.get(q))
            
            # Dados para a Planilha
            linha_dados = {
                "Página": i+1,
                "Frequência": dados["frequencia"],
                "Acertos": acertos,
                "Nota Final": f"{(acertos/52)*100:.1f}%"
            }
            linha_dados.update(dados["respostas"]) # Adiciona colunas Q1, Q2...
            resultados_finais.append(linha_dados)
            
            # Exibição Visual da "Máscara"
            with st.expander(f"Aluno {i+1} - Frequência: {dados['frequencia']} | Acertos: {acertos}/52", expanded=True):
                st.image(img_mask, caption="Máscara de Correção (Verde=Acerto, Vermelho=Erro)", use_container_width=True)
        
        else:
            st.error(f"Página {i+1}: Falha no reconhecimento das âncoras (Quadrados Pretos).")
        
        # Atualiza barra
        progresso.progress((i + 1) / len(paginas))

    # --- ÁREA DE EXPORTAÇÃO ---
    if resultados_finais:
        st.success("Processamento concluído!")
        df = pd.DataFrame(resultados_finais)
        
        st.subheader("📋 Relatório Geral da Turma")
        st.dataframe(df)
        
        # Botão de Download (Recolocado conforme solicitado)
        csv = df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(
            label="📥 Baixar Planilha Excel (.csv)",
            data=csv,
            file_name="resultado_samar_raposa.csv",
            mime="text/csv"
        )
