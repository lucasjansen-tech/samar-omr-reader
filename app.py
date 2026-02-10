import streamlit as st
import pandas as pd
from pdf2image import convert_from_bytes
from layout_samar import TIPOS_PROVA
# Se der erro aqui, é porque o arquivo gerador.py não foi salvo na pasta correta
from gerador import gerar_pdf 
from omr_engine import processar_gabarito
import cv2
import numpy as np

st.set_page_config(layout="wide", page_title="SAMAR PRO")
st.title("🖨️ Sistema SAMAR - Gerador e Corretor")

# 1. GERADOR COM EDIÇÃO
with st.expander("1. Gerar Folha de Resposta", expanded=True):
    col1, col2 = st.columns([1, 1])
    
    with col1:
        modelo = st.selectbox("Selecione o Padrão:", list(TIPOS_PROVA.keys()))
        conf_atual = TIPOS_PROVA[modelo]
        
        st.subheader("Personalizar Cabeçalho")
        # Campos editáveis
        novo_titulo = st.text_input("Nome da Avaliação:", value=conf_atual.titulo_prova)
        novo_subtitulo = st.text_input("Etapa / Detalhes:", value=conf_atual.subtitulo)
        
        # Aplica alterações
        conf_atual.titulo_prova = novo_titulo
        conf_atual.subtitulo = novo_subtitulo

    with col2:
        st.info(f"Configuração: {sum(b.quantidade for b in conf_atual.blocos)} questões.")
        st.warning("Clique abaixo para baixar o PDF com o novo cabeçalho.")
        
        if st.button("📄 Gerar PDF Personalizado"):
            filename = f"Gabarito_{modelo}.pdf"
            gerar_pdf(conf_atual, filename)
            with open(filename, "rb") as f:
                st.download_button("📥 Baixar PDF", f, filename)

st.divider()

# 2. CORRETOR
st.header("2. Correção de Provas")
st.info(f"Usando máscara do modelo: **{modelo}**")

with st.sidebar:
    st.header("Gabarito Oficial")
    gab_oficial = {}
    idx = 1
    for bloco in conf_atual.blocos:
        st.caption(f"{bloco.titulo}")
        for _ in range(bloco.quantidade):
            gab_oficial[idx] = st.selectbox(f"Q{idx}", ["A","B","C","D"], key=f"g{idx}")
            idx += 1

upload = st.file_uploader("Upload das Provas (PDF/IMG)", type=["pdf", "jpg", "png"])

if upload:
    if upload.type == "application/pdf":
        paginas = convert_from_bytes(upload.read(), dpi=200)
    else:
        from PIL import Image
        paginas = [Image.open(upload)]
    
    resultados = []
    
    for i, pag in enumerate(paginas):
        img_cv = np.array(pag)
        if img_cv.ndim == 2: img_cv = cv2.cvtColor(img_cv, cv2.COLOR_GRAY2BGR)
        else: img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)

        res, img_mask = processar_gabarito(img_cv, conf_atual, gab_oficial)
        
        total_q = sum(b.quantidade for b in conf_atual.blocos)
        acertos = sum(1 for q, r in res["respostas"].items() if r == gab_oficial.get(q))
        
        resultados.append({
            "Página": i+1,
            "Freq": res["frequencia"],
            "Acertos": acertos,
            "Nota": f"{(acertos/total_q)*100:.1f}%"
        })
        
        with st.expander(f"Aluno {i+1} (Freq: {res['frequencia']})", expanded=(i==0)):
            st.image(img_mask, use_container_width=True)
            
    if resultados:
        df = pd.DataFrame(resultados)
        st.dataframe(df)
        csv = df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button("📥 Baixar Planilha Final", csv, "Notas_SAMAR.csv")
