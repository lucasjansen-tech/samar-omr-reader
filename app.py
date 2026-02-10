import streamlit as st
import pandas as pd
from pdf2image import convert_from_bytes
from layout_samar import TIPOS_PROVA
# Importando as novas funções
from gerador import gerar_pdf, gerar_imagem_a4
from omr_engine import processar_gabarito
import cv2
import numpy as np
import os

st.set_page_config(layout="wide", page_title="SAMAR PRO")
st.title("🖨️ Sistema SAMAR - Leitura Universal")

# SELEÇÃO DE MODELO
modelo = st.selectbox("Selecione o Padrão do Gabarito:", list(TIPOS_PROVA.keys()))
conf_atual = TIPOS_PROVA[modelo]

tab1, tab2 = st.tabs(["1. Gerador de Folhas", "2. Corretor & Calibragem"])

# --- ABA 1: GERADOR ---
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Personalização")
        conf_atual.titulo_prova = st.text_input("Título da Prova:", value=conf_atual.titulo_prova)
        conf_atual.subtitulo = st.text_input("Subtítulo:", value=conf_atual.subtitulo)
        
        st.subheader("Formato de Exportação")
        formato = st.radio("Escolha o tipo de arquivo:", ["PDF", "PNG (Imagem)", "JPEG (Imagem)"], horizontal=True)

    with col2:
        st.info(f"Modelo selecionado: {modelo} ({sum(b.quantidade for b in conf_atual.blocos)} questões)")
        st.write(" ")
        st.write(" ")
        
        if st.button("🚀 Gerar e Baixar"):
            extensao = formato.split()[0].lower()
            filename = f"Gabarito_{modelo}.{extensao}"
            
            if extensao == "pdf":
                gerar_pdf(conf_atual, filename)
                mime_type = "application/pdf"
            else:
                # Gera imagem A4 alta resolução
                res = gerar_imagem_a4(conf_atual, filename, extensao)
                if not res:
                    st.error("Erro ao gerar imagem. Verifique se o Poppler está instalado.")
                mime_type = f"image/{extensao}"

            if os.path.exists(filename):
                with open(filename, "rb") as f:
                    st.download_button(
                        label=f"📥 Baixar Arquivo {formato}",
                        data=f,
                        file_name=filename,
                        mime=mime_type
                    )

# --- ABA 2: CORRETOR ---
with tab2:
    st.write("---")
    col_config, col_upload = st.columns([1, 2])
    
    with col_config:
        st.header("1. Gabarito Oficial")
        gab_oficial = {}
        idx = 1
        for bloco in conf_atual.blocos:
            st.caption(f"{bloco.titulo}")
            for _ in range(bloco.quantidade):
                gab_oficial[idx] = st.selectbox(f"Q{idx}", ["A","B","C","D"], key=f"g{idx}")
                idx += 1
        
        st.divider()
        st.header("2. Calibragem")
        st.info("Ajuste se o reconhecimento estiver desalinhado.")
        offset_x = st.slider("↔️ Horizontal (X)", -50, 50, 0)
        offset_y = st.slider("↕️ Vertical (Y)", -50, 50, 0)

    with col_upload:
        st.header("3. Upload e Resultado")
        upload = st.file_uploader("Envie as provas preenchidas (PDF ou Foto)", type=["pdf", "jpg", "png"])
        
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

                res, img_mask = processar_gabarito(img_cv, conf_atual, gab_oficial, offset_x, offset_y)
                
                total_q = sum(b.quantidade for b in conf_atual.blocos)
                acertos = sum(1 for q, r in res["respostas"].items() if r == gab_oficial.get(q))
                
                resultados.append({
                    "Aluno": f"ID {i+1}",
                    "Freq": res["frequencia"],
                    "Acertos": acertos,
                    "Nota": f"{(acertos/total_q)*100:.1f}%"
                })
                
                with st.expander(f"Correção Visual - Aluno {i+1}", expanded=True):
                    st.image(img_mask, use_container_width=True)
            
            if resultados:
                st.write("### Notas Finais")
                df = pd.DataFrame(resultados)
                st.dataframe(df)
                csv = df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
                st.download_button("📥 Baixar Planilha CSV", csv, "Notas_SAMAR.csv")
