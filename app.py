import streamlit as st
import os

# Configuração da página deve ser a PRIMEIRA linha
st.set_page_config(page_title="SAMAR OMR", layout="centered")

st.title("📊 SISTEMA SAMAR - SEMED RAPOSA")

# Teste Simples de Interface
st.write("Se você está vendo esta mensagem, a interface carregou com sucesso!")

# Verificação de arquivos críticos
col1, col2 = st.columns(2)
with col1:
    if os.path.exists("omr_engine.py"):
        st.success("Motor OMR: OK")
    else:
        st.error("Motor OMR: Faltando")

with col2:
    if os.path.exists("Frame 18.png"):
        st.success("Logo: OK")
    else:
        st.warning("Logo: Faltando")

# Botão de Upload para teste
arquivo = st.file_uploader("Teste de Upload", type=['pdf', 'jpg', 'png'])

if arquivo:
    st.write(f"Arquivo '{arquivo.name}' recebido com sucesso!")
