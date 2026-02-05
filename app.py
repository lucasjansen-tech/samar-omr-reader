import streamlit as st
import pandas as pd
from pdf2image import convert_from_bytes
from layout_samar import TIPOS_PROVA
from gerador import gerar_pdf
from omr_engine import processar_gabarito

st.set_page_config(layout="wide", page_title="SAMAR Dinâmico")
st.title("🖨️ e 📷 Sistema SAMAR - Malha Fechada")

# 1. SELETOR DE TIPO DE PROVA
tipo_selecionado = st.selectbox("Selecione o Modelo de Prova:", list(TIPOS_PROVA.keys()))
conf_atual = TIPOS_PROVA[tipo_selecionado]

# 2. ABA DE GERAÇÃO
with st.expander("1. Gerar Folha de Resposta (PDF)", expanded=True):
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write(f"**Título:** {conf_atual.titulo_prova}")
        st.write(f"**Estrutura:** {len(conf_atual.blocos)} blocos de questões.")
    with col2:
        if st.button("Gerar PDF"):
            filename = f"Gabarito_{tipo_selecionado}.pdf"
            gerar_pdf(conf_atual, filename)
            with open(filename, "rb") as f:
                st.download_button("📥 Baixar PDF", f, filename)

st.divider()

# 3. ABA DE CORREÇÃO
st.header("2. Correção Digital")
st.info(f"O sistema usará a máscara do modelo: **{tipo_selecionado}**")

# Monta gabarito dinâmico na tela
total_questoes = sum(b.quantidade for b in conf_atual.blocos)
with st.sidebar:
    st.header("Gabarito Oficial")
    gab_oficial = {}
    # Gera inputs apenas para as questões existentes nesse modelo
    q_counter = 1
    for bloco in conf_atual.blocos:
        st.caption(bloco.titulo)
        for _ in range(bloco.quantidade):
            gab_oficial[q_counter] = st.selectbox(f"Q{q_counter}", ["A","B","C","D"], key=f"gab_{q_counter}")
            q_counter += 1

upload = st.file_uploader("Upload Provas", type=["pdf", "jpg"])

if upload:
    if upload.type == "application/pdf":
        paginas = convert_from_bytes(upload.read(), dpi=200)
    else:
        from PIL import Image
        paginas = [Image.open(upload)]
    
    resultados = []
    
    for i, pag in enumerate(paginas):
        # Aqui a mágica acontece: Passamos a 'conf_atual' para o motor
        img_cv = np.array(pag)
        if img_cv.ndim == 2: img_cv = cv2.cvtColor(img_cv, cv2.COLOR_GRAY2BGR)
        else: img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)

        res, img_mask = processar_gabarito(img_cv, conf_atual, gab_oficial)
        
        acertos = sum(1 for q, r in res["respostas"].items() if r == gab_oficial.get(q))
        
        resultados.append({
            "Página": i+1,
            "Freq": res["frequencia"],
            "Acertos": acertos,
            "Nota": f"{(acertos/total_questoes)*100:.1f}%"
        })
        
        with st.expander(f"Aluno {i+1} - Freq: {res['frequencia']}", expanded=(i==0)):
            st.image(img_mask, use_container_width=True)
            
    if resultados:
        df = pd.DataFrame(resultados)
        st.dataframe(df)
