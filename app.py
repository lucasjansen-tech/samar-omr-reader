import streamlit as st
import os

# Configuração da página deve ser a PRIMEIRA linha de Streamlit
st.set_page_config(page_title="SAMAR OMR - Raposa", layout="wide")

st.title("📊 SISTEMA SAMAR - SEMED RAPOSA")

# Diagnóstico de Arquivos
st.sidebar.header("Status do Sistema")
arquivos_presentes = os.listdir('.')
if "omr_engine.py" in arquivos_presentes:
    st.sidebar.success("✅ omr_engine.py encontrado")
else:
    st.sidebar.error("❌ omr_engine.py NÃO encontrado")

# Tenta carregar as bibliotecas principais
try:
    import cv2
    import numpy as np
    import pandas as pd
    from pdf2image import convert_from_bytes
    st.sidebar.success("✅ OpenCV e PDF2Image carregados")
except Exception as e:
    st.sidebar.error(f"❌ Erro de biblioteca: {e}")

# Interface de Upload
upload = st.file_uploader("Suba o PDF ou Imagem dos Gabaritos", type=["pdf", "jpg", "png"])

if upload:
    st.write(f"Arquivo recebido: {upload.name}")
    # O processamento virá aqui após a tela carregar
