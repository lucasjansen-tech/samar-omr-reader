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
st.title("🖨️ Sistema SAMAR - Tecnologia Grid OTSU")

modelo = st.selectbox("Modelo:", list(TIPOS_PROVA.keys()))
conf = TIPOS_PROVA[modelo]

tab1, tab2 = st.tabs(["1. Gerar Prova", "2. Leitura e Correção"])

# --- ABA 1: GERADOR ---
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
                    st.error("Erro ao gerar imagem. Verifique o poppler.")

            if success and os.path.exists(fn):
                with open(fn, "rb") as f:
                    st.download_button("Baixar Arquivo", f, fn, mime)

# --- ABA 2: LEITURA E ANÁLISE ---
with tab2:
    st.markdown("### Configuração da Correção")
    
    # Campo rápido para o professor inserir o gabarito
    gabarito_str = st.text_input(
        "Digite o Gabarito Oficial (Ex: 52 letras juntas sem espaços):", 
        value="A" * 52 # Valor padrão para testes
    ).upper().strip()
    
    # Monta o dicionário do gabarito oficial (Ignora caracteres inválidos)
    gab_oficial = {}
    q_count = 1
    for char in gabarito_str:
        if char in "ABCD":
            gab_oficial[q_count] = char
            q_count += 1

    st.markdown("---")
    up = st.file_uploader("Upload da Prova Preenchida", type=["pdf", "png", "jpg"])
    
    if up:
        if up.type == "application/pdf": pages = convert_from_bytes(up.read(), dpi=200)
        else: from PIL import Image; pages = [Image.open(up)]
        
        for i, p in enumerate(pages):
            img = np.array(p)
            if img.ndim == 2: img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
            else: img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            
            # Passa a imagem e o dicionário oficial para o motor
            res, vis, _ = processar_gabarito(img, conf, gab_oficial)
            
            st.write(f"### Resultado da Correção - Página {i+1}")
            c1, c2 = st.columns([1, 1])
            
            with c1:
                st.image(vis, caption="Scanner OTSU - Validação Visual", use_container_width=True)
                
            with c2:
                freq = res.get("frequencia", "00")
                acertos = res.get("total_acertos", 0)
                
                # Exibe o sumário com destaque
                st.info(f"**Identificação (Frequência):** {freq}")
                st.success(f"**Pontuação:** {acertos} de {len(gab_oficial)} Acertos")
                
                # Exibe a tabela de correção detalhada
                if "correcao_detalhada" in res:
                    df = pd.DataFrame.from_dict(res["correcao_detalhada"], orient="index")
                    
                    # Formatação de cores condicional para o Streamlit
                    def color_status(val):
                        if val == 'Correto': return 'color: #2e7d32; font-weight: bold'
                        elif val == 'Incorreto': return 'color: #d32f2f; font-weight: bold'
                        return 'color: #f57c00' # Em branco
                    
                    st.dataframe(df.style.map(color_status, subset=['Status']), height=600, use_container_width=True)
