import streamlit as st
import pandas as pd
from pdf2image import convert_from_bytes
from layout_samar import TIPOS_PROVA
from gerador import gerar_pdf, gerar_imagem_a4
from omr_engine import processar_gabarito
import cv2
import numpy as np
import os

st.set_page_config(layout="wide", page_title="SAMAR PRO")
st.title("🖨️ Sistema SAMAR")

modelo = st.selectbox("Modelo:", list(TIPOS_PROVA.keys()))
conf_atual = TIPOS_PROVA[modelo]

tab1, tab2 = st.tabs(["1. Gerar", "2. Corrigir"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Dados")
        conf_atual.titulo_prova = st.text_input("Título:", value=conf_atual.titulo_prova)
        conf_atual.subtitulo = st.text_input("Subtítulo:", value=conf_atual.subtitulo)
        fmt = st.radio("Formato:", ["PDF", "PNG", "JPEG"], horizontal=True)
    with col2:
        if st.button("Gerar Arquivo"):
            ext = fmt.split()[0].lower()
            fn = f"Gabarito_{modelo}.{ext}"
            if ext == "pdf": gerar_pdf(conf_atual, fn); mime="application/pdf"
            else: gerar_imagem_a4(conf_atual, fn, ext); mime=f"image/{ext}"
            with open(fn, "rb") as f: st.download_button("Baixar", f, fn, mime)

with tab2:
    c1, c2 = st.columns([1, 2])
    with c1:
        st.write("### Gabarito")
        gab = {}
        idx = 1
        for b in conf_atual.blocos:
            st.caption(b.titulo)
            for _ in range(b.quantidade):
                gab[idx] = st.selectbox(f"Q{idx}", ["A","B","C","D"], key=f"g{idx}")
                idx += 1
        st.divider()
        st.write("### Calibragem")
        off_x = st.slider("X", -50, 50, 0)
        off_y = st.slider("Y", -50, 50, 0)

    with c2:
        up = st.file_uploader("Upload", type=["pdf", "jpg", "png"])
        if up:
            if up.type == "application/pdf": pages = convert_from_bytes(up.read(), dpi=200)
            else: from PIL import Image; pages = [Image.open(up)]
            
            res_list = []
            for i, p in enumerate(pages):
                img = np.array(p)
                if img.ndim == 2: img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                else: img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                
                res, proc, _ = processar_gabarito(img, conf_atual, gab, off_x, off_y)
                total = sum(b.quantidade for b in conf_atual.blocos)
                acertos = sum(1 for q, r in res["respostas"].items() if r == gab.get(q))
                
                res_list.append({"Aluno": i+1, "Freq": res["frequencia"], "Nota": f"{acertos}/{total}"})
                with st.expander(f"Aluno {i+1}", expanded=True):
                    st.image(proc, use_container_width=True)
            
            if res_list: st.dataframe(pd.DataFrame(res_list))
