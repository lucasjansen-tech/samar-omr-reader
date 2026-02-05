import streamlit as st
import os

# Configuração da página deve ser SEMPRE o primeiro comando Streamlit
st.set_page_config(page_title="SAMAR OMR - Raposa", layout="wide")

st.title("📊 SISTEMA SAMAR - SEMED RAPOSA")

# Verificação de arquivos no repositório
st.sidebar.header("Status do Servidor")
if os.path.exists("omr_engine.py"):
    st.sidebar.success("✅ omr_engine.py carregado")
else:
    st.sidebar.error("❌ omr_engine.py não encontrado no GitHub")

# Tentativa de carregar a imagem da logo com segurança
if os.path.exists("Frame 18.png"):
    st.image("Frame 18.png")
else:
    st.warning("⚠️ Logo 'Frame 18.png' não encontrada. Verifique o nome do arquivo no GitHub.")

# Interface de Upload
st.write("### Envio de Gabaritos")
upload = st.file_uploader("Suba o PDF ou Imagem dos Gabaritos", type=["pdf", "jpg", "png"])

if upload:
    st.info(f"Arquivo recebido: {upload.name}. Iniciando processamento...")
    # Aqui chamaremos a função do omr_engine.py após confirmarmos que a tela abriu.
