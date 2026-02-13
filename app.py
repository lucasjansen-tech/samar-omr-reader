import streamlit as st
import pandas as pd
from pdf2image import convert_from_bytes
from layout_samar import TIPOS_PROVA
from gerador import gerar_pdf
from omr_engine import processar_gabarito
import cv2
import numpy as np
import os

st.set_page_config(layout="wide", page_title="SAMAR PRO GRID")
st.title("🖨️ Sistema SAMAR - Tecnologia Grid")

modelo = st.selectbox("Modelo:", list(TIPOS_PROVA.keys()))
conf = TIPOS_PROVA[modelo]

tab1, tab2 = st.tabs(["1. Gerar Prova", "2. Leitura"])

with tab1:
    if st.button("Gerar PDF"):
        fn = f"Gabarito_{modelo}.pdf"
        gerar_pdf(conf, fn)
        with open(fn, "rb") as f:
            st.download_button("Baixar PDF", f, fn, "application/pdf")

with tab2:
    gab = {i: "A" for i in range(1, 53)} # Gabarito dummy
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
