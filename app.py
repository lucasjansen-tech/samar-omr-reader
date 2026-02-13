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

tab1, tab2 = st.tabs(["1. Gerar Prova", "2. Leitura"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        fmt = st.radio("Formato:", ["PDF", "PNG", "JPEG"], horizontal=True)
    with col2:
        if st.button("Gerar Arquivo"):
            ext = fmt.split()[0].lower()
            fn = f"Gabarito_{modelo}.{ext}"
            
            success = False
            if ext == "pdf":
                gerar_pdf(conf, fn)
                mime = "application/pdf"
                success = True
            else:
                res = gerar_imagem_a4(conf, fn, ext)
                if res:
                    mime = f"image/{ext}"
                    success = True
                else:
                    st.error("Erro ao gerar imagem.")

            if success and os.path.exists(fn):
                with open(fn, "rb") as f:
                    st.download_button("Baixar", f, fn, mime)

with tab2:
    gab = {i: "A" for i in range(1, 53)} 
    up = st.file_uploader("Upload", type=["pdf", "png", "jpg"])
    
    if up:
        if up.type == "application/pdf": pages = convert_from_bytes(up.read(), dpi=200)
        else: from PIL import Image; pages = [Image.open(up)]
        
        for i, p in enumerate(pages):
            img = np.array(p)
            if img.ndim==2: img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            else: img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            
            res, vis, _ = processar_gabarito(img, conf, gab)
            st.image(vis, caption=f"Leitura Grid - Pág {i+1}")
            st.json(res)
