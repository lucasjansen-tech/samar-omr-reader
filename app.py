import streamlit as st

# O comando set_page_config DEVE ser o primeiro
st.set_page_config(page_title="SAMAR DEBUG", layout="centered")

st.title("🛠️ MODO DE DIAGNÓSTICO SAMAR")

st.write("Se você está lendo isso, o Streamlit está funcionando!")

# Tenta importar as bibliotecas e mostra o erro na tela se falhar
try:
    import cv2
    st.success("✅ OpenCV carregado com sucesso!")
except Exception as e:
    st.error(f"❌ Erro ao carregar OpenCV: {e}")

try:
    import numpy as np
    st.success("✅ Numpy carregado com sucesso!")
except Exception as e:
    st.error(f"❌ Erro ao carregar Numpy: {e}")

try:
    from pdf2image import convert_from_bytes
    st.success("✅ PDF2Image carregado com sucesso!")
except Exception as e:
    st.error(f"❌ Erro ao carregar PDF2Image: {e}")

st.info("Verifique se as mensagens acima estão em verde.")
