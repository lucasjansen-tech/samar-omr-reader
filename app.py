import streamlit as st
import pandas as pd
from pdf2image import convert_from_bytes
from layout_samar import TIPOS_PROVA
from gerador import gerar_pdf, gerar_imagem_a4
from omr_engine import processar_gabarito
import cv2
import numpy as np
import os

st.set_page_config(layout="wide", page_title="SAMAR GRID PRO")
st.title("🖨️ Sistema SAMAR - Tecnologia Grid")

modelo = st.selectbox("Modelo:", list(TIPOS_PROVA.keys()))
conf = TIPOS_PROVA[modelo]

tab1, tab2 = st.tabs(["1. Gerar Prova", "2. Leitura e Correção"])

# ABA 1: GERADOR
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        fmt = st.radio("Formato de Saída:", ["PDF", "PNG", "JPEG"], horizontal=True)
    with col2:
        if st.button("🚀 Gerar Arquivo"):
            ext = fmt.split()[0].lower()
            fn = f"Gabarito_{modelo}.{ext}"
            
            sucesso = False
            if ext == "pdf":
                gerar_pdf(conf, fn)
                mime_type = "application/pdf"
                sucesso = True
            else:
                res = gerar_imagem_a4(conf, fn, ext)
                if res:
                    mime_type = f"image/{ext}"
                    sucesso = True
                else:
                    st.error("⚠️ Não foi possível gerar a imagem. Verifique se o 'Poppler' está instalado no servidor.")

            if sucesso and os.path.exists(fn):
                with open(fn, "rb") as f:
                    st.download_button(f"📥 Baixar {ext.upper()}", f, fn, mime_type)

# ABA 2: LEITURA
with tab2:
    st.write("---")
    # Simulando um gabarito dummy para teste
    gab = {i: "A" for i in range(1, 53)} 
    
    up = st.file_uploader("Upload da Prova Digitalizada", type=["pdf", "png", "jpg"])
    
    if up:
        if up.type == "application/pdf": 
            pages = convert_from_bytes(up.read(), dpi=200)
        else: 
            from PIL import Image
            pages = [Image.open(up)]
        
        for i, p in enumerate(pages):
            img = np.array(p)
            if img.ndim == 2: img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            else: img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            
            # Processamento
            res, vis, _ = processar_gabarito(img, conf, gab)
            
            # Exibição
            st.image(vis, caption=f"Leitura Grid - Página {i+1}", use_container_width=True)
            st.json(res)
