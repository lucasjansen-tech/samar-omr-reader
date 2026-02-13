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
st.title("🖨️ Sistema SAMAR - Leitura OMR Inteligente")

modelo = st.selectbox("Modelo de Prova:", list(TIPOS_PROVA.keys()))
conf = TIPOS_PROVA[modelo]

tab1, tab2 = st.tabs(["1. Gerador de PDF", "2. Leitura e Correção"])

# --- ABA 1: GERADOR ---
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        fmt = st.radio("Formato de Saída:", ["PDF", "PNG", "JPEG"], horizontal=True)
    with col2:
        st.write("")
        if st.button("🚀 Gerar Arquivo em Branco"):
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
                    st.download_button(f"📥 Baixar {ext.upper()}", f, fn, mime)

# --- ABA 2: LEITURA E CORREÇÃO ---
with tab2:
    st.markdown("### 📝 Passo 1: Configurar Gabarito Oficial")
    
    modo_gab = st.radio("Como deseja inserir o gabarito?", 
                        ["Texto Rápido (Copiar/Colar)", "Preenchimento Manual (Por Bloco)"], 
                        horizontal=True)
    
    gab_oficial = {}
    
    if "Texto Rápido" in modo_gab:
        gabarito_str = st.text_input(
            "Cole as respostas sem espaços (Ex: ABCDABCD...)", 
            value="A" * 52
        ).upper().strip()
        
        q_count = 1
        for char in gabarito_str:
            if char in "ABCD":
                gab_oficial[q_count] = char
                q_count += 1
    else:
        # Preenchimento Intuitivo por Blocos
        cols = st.columns(4)
        for bloco in range(4):
            with cols[bloco]:
                st.markdown(f"**Bloco {bloco+1}**")
                for q in range(13):
                    q_num = (bloco * 13) + q + 1
                    gab_oficial[q_num] = st.selectbox(
                        f"Q.{q_num:02d}", 
                        ["A", "B", "C", "D"], 
                        key=f"q_{q_num}"
                    )

    st.markdown("---")
    st.markdown("### 📸 Passo 2: Analisar Prova Preenchida")
    up = st.file_uploader("Faça o Upload do PDF ou Imagem escaneada:", type=["pdf", "png", "jpg"])
    
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
            
            res, vis, _ = processar_gabarito(img, conf, gab_oficial)
            
            st.write(f"#### Resultados - Página {i+1}")
            c1, c2 = st.columns([1, 1])
            
            with c1:
                # Imagem exibe os círculos Verdes/Vermelhos!
                st.image(vis, caption="🟢 Acertos | 🔴 Erros | ⚪ Em Branco", use_container_width=True)
                
            with c2:
                freq = res.get("frequencia", "00")
                acertos = res.get("total_acertos", 0)
                
                st.info(f"**ID do Aluno (Frequência):** {freq}")
                st.success(f"**Pontuação:** {acertos} / {len(gab_oficial)} Acertos")
                
                if "correcao_detalhada" in res:
                    df = pd.DataFrame.from_dict(res["correcao_detalhada"], orient="index")
                    
                    def color_status(val):
                        if val == 'Correto': return 'color: #2e7d32; font-weight: bold'
                        elif val == 'Incorreto': return 'color: #d32f2f; font-weight: bold'
                        return 'color: #f57c00' 
                    
                    st.dataframe(df.style.map(color_status, subset=['Status']), height=500, use_container_width=True)
