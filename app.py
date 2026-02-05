import streamlit as st
import pandas as pd
from pdf2image import convert_from_bytes
from omr_engine import tratar_entrada, alinhar_gabarito, extrair_dados

st.set_page_config(page_title="SAMAR Correção", layout="wide")
st.title("📊 Correção de Provas - SAMAR Raposa")

with st.sidebar:
    st.header("📝 Gabarito Oficial")
    st.info("Selecione as respostas corretas abaixo para gerar a máscara de correção.")
    gab = {i: st.selectbox(f"Questão {i}", ["A","B","C","D"], key=f"q{i}") for i in range(1, 53)}

upload = st.file_uploader("📂 Upload do PDF das Provas", type=["pdf"])

if upload:
    # Alta resolução para garantir leitura precisa
    paginas = convert_from_bytes(upload.read(), dpi=200)
    resultados = []

    st.write(f"Processando {len(paginas)} páginas...")
    
    # Container para resultados
    for i, pag in enumerate(paginas):
        img_in = tratar_entrada(pag)
        
        # O alinhamento agora é híbrido (nunca retorna None)
        warped = alinhar_gabarito(img_in)
        
        dados, img_mask = extrair_dados(warped, gab)
        
        # Estatísticas
        acertos = sum(1 for q, r in dados["respostas"].items() if r == gab.get(q))
        
        # Adiciona à lista final
        linha = {
            "Página": i+1,
            "Frequência": dados["frequencia"],
            "Acertos": acertos,
            "Nota": f"{(acertos/52)*100:.1f}%"
        }
        linha.update(dados["respostas"])
        resultados.append(linha)

        # Exibe a Máscara Visual
        with st.expander(f"📄 Aluno {i+1} (Freq: {dados['frequencia']}) - Nota: {acertos}/52", expanded=(i==0)):
            c1, c2 = st.columns([1, 1])
            with c1:
                st.write("**Legenda:**")
                st.success("Verde Cheio: Acerto")
                st.error("Vermelho: Erro do Aluno")
                st.write("Anel Verde: Resposta Correta (quando aluno erra)")
            with c2:
                st.image(img_mask, caption="Máscara de Correção", use_container_width=True)

    if resultados:
        st.divider()
        st.subheader("📥 Relatório Final")
        df = pd.DataFrame(resultados)
        
        # Reordenar colunas para ficar bonito
        cols = ["Página", "Frequência", "Acertos", "Nota"] + [i for i in range(1, 53)]
        # Garante que as colunas existem no DF antes de ordenar
        cols_existentes = [c for c in cols if c in df.columns]
        df = df[cols_existentes]
        
        st.dataframe(df)

        # Botão de Download Configurado para Excel BR
        csv = df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(
            label="📥 Baixar Planilha (.csv)",
            data=csv,
            file_name="Relatorio_SAMAR_Raposa.csv",
            mime="text/csv"
        )
