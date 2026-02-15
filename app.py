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

modelo = st.selectbox("Selecione o Modelo de Prova:", list(TIPOS_PROVA.keys()))
conf = TIPOS_PROVA[modelo]

tab1, tab2 = st.tabs(["1. Gerador de PDF", "2. Leitura, Correção e Exportação"])

# ====================================================================
# ABA 1: GERADOR COM PERSONALIZAÇÃO (Títulos e Logos)
# ====================================================================
with tab1:
    st.markdown("### 🎨 Personalização do Cabeçalho")
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        custom_titulo = st.text_input("Título da Avaliação:", conf.titulo_prova)
    with col_t2:
        custom_sub = st.text_input("Etapa/Ano (Subtítulo):", conf.subtitulo)

    st.markdown("**Logos (Opcional - Recomenda-se arquivos PNG com fundo transparente)**")
    col_l1, col_l2, col_l3 = st.columns(3)
    with col_l1:
        logo_esq = st.file_uploader("Logo Esquerda", type=["png", "jpg"])
    with col_l2:
        logo_cen = st.file_uploader("Logo Centro", type=["png", "jpg"])
    with col_l3:
        logo_dir = st.file_uploader("Logo Direita", type=["png", "jpg"])

    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        fmt = st.radio("Formato de Saída:", ["PDF", "PNG", "JPEG"], horizontal=True)
    with col2:
        st.write("")
        if st.button("🚀 Gerar Arquivo Pronto para Impressão"):
            # Empacota as logos para enviar ao gerador
            logos_dict = {
                'esq': logo_esq,
                'cen': logo_cen,
                'dir': logo_dir
            }
            
            ext = fmt.split()[0].lower()
            fn = f"Gabarito_{modelo}.{ext}"
            
            success = False
            if ext == "pdf":
                gerar_pdf(conf, fn, custom_titulo, custom_sub, logos_dict)
                mime = "application/pdf"
                success = True
            else:
                res = gerar_imagem_a4(conf, fn, ext, custom_titulo, custom_sub, logos_dict)
                if res:
                    mime = f"image/{ext}"
                    success = True
                else:
                    st.error("Erro ao gerar imagem. Verifique o poppler.")

            if success and os.path.exists(fn):
                with open(fn, "rb") as f:
                    st.download_button(f"📥 Baixar Arquivo {ext.upper()}", f, fn, mime)

# ====================================================================
# ABA 2: LEITURA E CORREÇÃO (O motor original, inalterado)
# ====================================================================
with tab2:
    st.markdown("### 📝 Passo 1: Configurar Gabarito Oficial")
    
    modo_gab = st.radio("Como deseja inserir o gabarito?", 
                        ["Texto Rápido (Copiar/Colar)", "Preenchimento Manual (Por Bloco)"], 
                        horizontal=True)
    
    gab_oficial = {}
    total_questoes = int(modelo.split('_')[1])
    blocos = len([g for g in conf.grids if g.questao_inicial > 0])
    questoes_por_bloco = total_questoes // blocos if blocos > 0 else 0
    
    if "Texto Rápido" in modo_gab:
        st.info("💡 **Dica:** Digite 'X' ou 'N' para sinalizar uma Questão Nula (Todos ganham ponto).")
        gabarito_str = st.text_input(
            f"Cole as {total_questoes} respostas sem espaços (Ex: ABCDABCD...):", 
            value="A" * total_questoes
        ).upper().strip()
        
        q_count = 1
        for char in gabarito_str:
            if char in "ABCDXN":
                gab_oficial[q_count] = "NULA" if char in ["X", "N"] else char
                q_count += 1
    else:
        cols = st.columns(blocos)
        for bloco in range(blocos):
            with cols[bloco]:
                st.markdown(f"**Bloco {bloco+1}**")
                for q in range(questoes_por_bloco):
                    q_num = (bloco * questoes_por_bloco) + q + 1
                    gab_oficial[q_num] = st.selectbox(
                        f"Q.{q_num:02d}", 
                        ["A", "B", "C", "D", "NULA"], 
                        key=f"q_{q_num}"
                    )

    st.markdown("---")
    st.markdown("### 📸 Passo 2: Analisar Prova(s) Preenchida(s)")
    up = st.file_uploader("Faça o Upload do PDF (Múltiplas páginas) ou Imagens:", type=["pdf", "png", "jpg"], accept_multiple_files=True)
    
    if up:
        resultados_lote = []
        
        for arquivo in up:
            if arquivo.type == "application/pdf": 
                pages = convert_from_bytes(arquivo.read(), dpi=200)
            else: 
                from PIL import Image
                pages = [Image.open(arquivo)]
            
            for i, p in enumerate(pages):
                img = np.array(p)
                if img.ndim == 2: img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                else: img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                
                res, vis, _ = processar_gabarito(img, conf, gab_oficial)
                
                freq = res.get("frequencia", "00")
                acertos = res.get("total_acertos", 0)
                
                aluno_dados = {"Frequencia": freq}
                for q_num in range(1, total_questoes + 1):
                    resp_str = res["respostas"].get(q_num, ".")
                    aluno_dados[f"Q{q_num:02d}"] = "Múltiplas" if resp_str == "*" else resp_str
                aluno_dados["Total_Acertos"] = acertos
                
                resultados_lote.append(aluno_dados)
                
                st.write(f"#### Resultados - Aluno: {freq}")
                c1, c2 = st.columns([1, 1])
                
                with c1:
                    st.image(vis, caption="🟢 Correto | 🔴 Errado | 🟠 Múltiplas | 🔵 Anulada", use_container_width=True)
                    
                with c2:
                    st.info(f"**ID do Aluno (Frequência):** {freq}")
                    st.success(f"**Pontuação:** {acertos} / {len(gab_oficial)} Acertos")
                    
                    if "correcao_detalhada" in res:
                        with st.expander("Ver Correção Detalhada"):
                            df_detalhe = pd.DataFrame.from_dict(res["correcao_detalhada"], orient="index")
                            def color_status(val):
                                if val == 'Correto': return 'color: #2e7d32; font-weight: bold'
                                elif val == 'Correto (Anulada)': return 'color: #0288d1; font-weight: bold'
                                elif val == 'Incorreto' or val == 'Múltiplas Marcações': return 'color: #d32f2f; font-weight: bold'
                                return 'color: #f57c00' 
                            st.dataframe(df_detalhe.style.map(color_status, subset=['Status']), use_container_width=True)
                        
        if resultados_lote:
            st.markdown("---")
            st.markdown("### 📊 Exportação de Dados para a Calculadora")
            
            df_export = pd.DataFrame(resultados_lote)
            
            df_export['Ordem_Num'] = pd.to_numeric(df_export['Frequencia'], errors='coerce')
            df_export = df_export.sort_values(by='Ordem_Num', ascending=True, na_position='last')
            df_export = df_export.drop(columns=['Ordem_Num']) 
            
            st.write("Prévia dos dados formatados (Ordenados por Frequência):")
            st.dataframe(df_export)
            
            csv_dados = df_export.to_csv(index=False, sep=";")
            st.download_button(
                label="📥 Baixar Dados Ordenados (CSV)",
                data=csv_dados,
                file_name="analise_samar_dados.csv",
                mime="text/csv",
                type="primary"
            )
