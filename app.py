import streamlit as st
import pandas as pd
from pdf2image import convert_from_bytes
from layout_samar import TIPOS_PROVA
from gerador import gerar_pdf, gerar_imagem_a4
from omr_engine import processar_gabarito
import cv2
import numpy as np
import os
import io

st.set_page_config(layout="wide", page_title="SAMAR GRID PRO")

# ====================================================================
# MENU LATERAL: CONTROLE DE ACESSO (HIERARQUIA)
# ====================================================================
st.sidebar.markdown("### 🔐 Controle de Acesso")
perfil = st.sidebar.radio("Selecione seu Perfil:", ["👨‍💻 Digitador (Transcrição)", "⚙️ Coordenação (Admin)"])

if perfil == "⚙️ Coordenação (Admin)":
    senha = st.sidebar.text_input("Senha de Acesso:", type="password")
    if senha != "coted2026": 
        st.sidebar.warning("Digite a senha da coordenação para liberar as ferramentas de Admin.")
        st.title("🖨️ Sistema SAMAR")
        st.info("👈 Por favor, autentique-se no menu lateral para acessar as configurações.")
        st.stop()

st.title("🖨️ Sistema SAMAR - Operação Descentralizada")

modelo = st.selectbox("Selecione o Modelo de Prova:", list(TIPOS_PROVA.keys()))
conf = TIPOS_PROVA[modelo]

# Variáveis Globais
total_q_global = int(modelo.split('_')[1])
ARQUIVO_TEMP = f"temp_transcricao_{modelo}.csv"

# Mapeamento Dinâmico de Disciplinas (Usado pelo Robô e pela Correção Admin)
mapa_disc_global = {}
tot_disc_global = {}
for g in conf.grids:
    if g.questao_inicial > 0:
        disc = g.texto_extra if g.texto_extra else "Geral"
        if disc not in tot_disc_global: tot_disc_global[disc] = 0
        tot_disc_global[disc] += g.rows
        for r in range(g.rows): mapa_disc_global[g.questao_inicial + r] = disc

# ====================================================================
# RENDERIZAÇÃO DE ABAS POR PERFIL
# ====================================================================
if perfil == "⚙️ Coordenação (Admin)":
    tab1, tab2, tab3, tab4 = st.tabs([
        "1. Gerador de PDF", 
        "2. Leitura por Imagem", 
        "3. Cartão Digital", 
        "4. 🛠️ Motor de Correção (CSVs)"
    ])
    
    # --- ABA 1: GERADOR DE PDF (INTOCÁVEL) ---
    with tab1:
        st.markdown("### 🎨 Personalização do Cabeçalho")
        col_t1, col_t2 = st.columns(2)
        with col_t1: custom_titulo = st.text_input("Título da Avaliação:", conf.titulo_prova)
        with col_t2: custom_sub = st.text_input("Etapa/Ano (Subtítulo):", conf.subtitulo)
        
        col_l1, col_l2, col_l3 = st.columns(3)
        with col_l1: logo_esq = st.file_uploader("Logo Esquerda", type=["png", "jpg"])
        with col_l2: logo_cen = st.file_uploader("Logo Centro", type=["png", "jpg"])
        with col_l3: logo_dir = st.file_uploader("Logo Direita", type=["png", "jpg"])

        col1, col2 = st.columns(2)
        with col1: fmt = st.radio("Formato de Saída:", ["PDF", "PNG", "JPEG"], horizontal=True)
        with col2:
            st.write("")
            if st.button("🚀 Gerar Arquivo Pronto para Impressão"):
                logos_dict = {'esq': logo_esq, 'cen': logo_cen, 'dir': logo_dir}
                ext = fmt.split()[0].lower()
                fn = f"Gabarito_{modelo}.{ext}"
                
                success = False
                if ext == "pdf":
                    gerar_pdf(conf, fn, custom_titulo, custom_sub, logos_dict)
                    mime, success = "application/pdf", True
                else:
                    if gerar_imagem_a4(conf, fn, ext, custom_titulo, custom_sub, logos_dict):
                        mime, success = f"image/{ext}", True

                if success and os.path.exists(fn):
                    with open(fn, "rb") as f:
                        st.download_button(f"📥 Baixar Arquivo {ext.upper()}", f, fn, mime)

    # --- ABA 2: LEITURA POR IMAGEM (INTOCÁVEL) ---
    with tab2:
        st.markdown("### 📝 Passo 1: Configurar Gabarito de Correção")
        modo_gab = st.radio("Como deseja inserir o gabarito?", ["Texto Rápido", "Preenchimento Manual"], horizontal=True, key="modo_gab_t2")
        
        gab_oficial = {}
        blocos = len([g for g in conf.grids if g.questao_inicial > 0])
        questoes_por_bloco = total_q_global // blocos if blocos > 0 else 0
        
        if "Texto Rápido" in modo_gab:
            gabarito_str = st.text_input(f"Cole as {total_q_global} respostas:", value="A" * total_q_global, key="gab_t2").upper().strip()
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
                        gab_oficial[q_num] = st.selectbox(f"Q.{q_num:02d}", ["A", "B", "C", "D", "NULA"], key=f"q_t2_{q_num}")

        st.markdown("---")
        st.markdown("### 📸 Passo 2: Analisar Provas")
        up = st.file_uploader("Upload das Imagens/PDF:", type=["pdf", "png", "jpg"], accept_multiple_files=True)
        
        if up:
            resultados_lote = []
            for arquivo in up:
                if arquivo.type == "application/pdf": pages = convert_from_bytes(arquivo.read(), dpi=200)
                else: 
                    from PIL import Image
                    pages = [Image.open(arquivo)]
                
                for i, p in enumerate(pages):
                    img = np.array(p)
                    if img.ndim == 2: img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
                    else: img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                    
                    res, vis, _ = processar_gabarito(img, conf, gab_oficial)
                    freq, acertos = res.get("frequencia", "00"), res.get("total_acertos", 0)
                    aluno_dados = {"Frequencia": freq}
                    acertos_disciplina = {disc: 0 for disc in tot_disc_global}
                    
                    for q_num in range(1, total_q_global + 1):
                        resp_str = res["respostas"].get(q_num, ".")
                        aluno_dados[f"Letra_Q{q_num:02d}"] = "Múltiplas" if resp_str == "*" else resp_str
                        is_correct = 1 if "Correto" in res.get("correcao_detalhada", {}).get(q_num, {}).get("Status", "") else 0
                        aluno_dados[f"Q{q_num:02d}"] = is_correct
                        if mapa_disc_global.get(q_num) and is_correct: acertos_disciplina[mapa_disc_global[q_num]] += 1
                    
                    aluno_dados["Total_Acertos_Geral"] = acertos
                    aluno_dados["%_Acerto_Geral"] = round((acertos / total_q_global) * 100, 2) if total_q_global > 0 else 0
                    
                    for disc, total in tot_disc_global.items():
                        qtd_acertos = acertos_disciplina[disc]
                        aluno_dados[f"Acertos_{disc.replace(' ', '_')}"] = qtd_acertos
                        aluno_dados[f"%_{disc.replace(' ', '_')}"] = round((qtd_acertos / total) * 100, 2) if total > 0 else 0
                    
                    resultados_lote.append(aluno_dados)
                    
                    st.write(f"#### Aluno: {freq}")
                    c1, c2 = st.columns([1, 1])
                    with c1: st.image(vis, use_container_width=True)
                    with c2: st.success(f"**Geral:** {acertos} / {len(gab_oficial)}")
                            
            if resultados_lote:
                df_export = pd.DataFrame(resultados_lote)
                df_export['Ordem_Num'] = pd.to_numeric(df_export['Frequencia'], errors='coerce')
                df_export = df_export.sort_values(by='Ordem_Num', ascending=True, na_position='last').drop(columns=['Ordem_Num']) 
                st.download_button("📥 Baixar CSV Corrigido", df_export.to_csv(index=False, sep=";"), f"samar_robo_{modelo}.csv", "text/csv", type="primary")

    # --- NOVA ABA 4: MOTOR DE CORREÇÃO EM LOTE PARA CSVs DOS DIGITADORES ---
    with tab4:
        st.markdown("### 🛠️ Corretor de Arquivos Brutos (Digitadores)")
        st.info("Pegue os arquivos '.csv' que os digitadores te enviaram, defina o Gabarito e deixe o sistema processar as notas e porcentagens de todo mundo.")
        
        st.markdown("#### 1. Gabarito Oficial da Turma/Escola")
        gabarito_admin = st.text_input(f"Letras do Gabarito Oficial ({total_q_global} questões):", value="A"*total_q_global, key="gab_t4").upper().strip()
        gab_dict_admin = {}
        if len(gabarito_admin) >= total_q_global:
            for i, char in enumerate(gabarito_admin[:total_q_global]):
                gab_dict_admin[i+1] = "NULA" if char in ["X", "N"] else char

        st.markdown("#### 2. Processar Lotes")
        lote_bruto = st.file_uploader("Suba os arquivos 'samar_respostas_brutas.csv' gerados pela equipe:", type=["csv"], accept_multiple_files=True)
        
        if lote_bruto and st.button("⚙️ Corrigir Lotes e Gerar CSV Final"):
            todos_resultados = []
            
            for arq in lote_bruto:
                df_bruto = pd.read_csv(arq, sep=";", dtype=str)
                # Garante coluna nome
                if "Nome_Aluno" not in df_bruto.columns: df_bruto["Nome_Aluno"] = ""
                df_bruto["Nome_Aluno"] = df_bruto["Nome_Aluno"].fillna("")
                
                for index, row in df_bruto.iterrows():
                    aluno_f = row["Frequencia"]
                    aluno_nome = row["Nome_Aluno"]
                    respostas_brutas = row["Respostas_Brutas"]
                    
                    aluno_processado = {"Frequencia": aluno_f, "Nome": aluno_nome}
                    acertos_geral = 0
                    acertos_disc = {disc: 0 for disc in tot_disc_global}
                    
                    for q in range(1, total_q_global + 1):
                        letra_marcada = respostas_brutas[q-1] if (pd.notna(respostas_brutas) and q-1 < len(respostas_brutas)) else "-"
                        gabarito_certo = gab_dict_admin.get(q, "NULA")
                        aluno_processado[f"Letra_Q{q:02d}"] = letra_marcada
                        
                        is_correct = 1 if gabarito_certo == "NULA" or letra_marcada == gabarito_certo else 0
                        if is_correct:
                            acertos_geral += 1
                            if mapa_disc_global.get(q): acertos_disc[mapa_disc_global[q]] += 1
                        aluno_processado[f"Q{q:02d}"] = is_correct
                    
                    aluno_processado["Total_Acertos_Geral"] = acertos_geral
                    aluno_processado["%_Acerto_Geral"] = round((acertos_geral / total_q_global) * 100, 2) if total_q_global > 0 else 0
                    
                    for disc, total in tot_disc_global.items():
                        qtd_acertos = acertos_disc[disc]
                        aluno_processado[f"Acertos_{disc.replace(' ', '_')}"] = qtd_acertos
                        aluno_processado[f"%_{disc.replace(' ', '_')}"] = round((qtd_acertos / total) * 100, 2) if total > 0 else 0
                        
                    todos_resultados.append(aluno_processado)

            if todos_resultados:
                df_final_admin = pd.DataFrame(todos_resultados)
                df_final_admin['Ordem_Num'] = pd.to_numeric(df_final_admin['Frequencia'], errors='coerce')
                df_final_admin = df_final_admin.sort_values(by='Ordem_Num', ascending=True, na_position='last').drop(columns=['Ordem_Num']) 
                
                st.success(f"✅ Sucesso! {len(df_final_admin)} alunos foram corrigidos.")
                st.download_button("📥 Baixar CSV Consolidado (Pronto para a Calculadora)", df_final_admin.to_csv(index=False, sep=";"), f"samar_dados_consolidados_{modelo}.csv", "text/csv", type="primary")

else:
    # Perfil Digitador (Burro e Ágil)
    tab3 = st.tabs(["📝 Cartão-Resposta Digital"])[0]

# ====================================================================
# ABA 3 COMPARTILHADA: CARTÃO-RESPOSTA DIGITAL (DIGITAÇÃO BRUTA)
# ====================================================================
with tab3:
    st.markdown("### 🖱️ Transcrição do Aluno")
    st.info("Nesta tela, você apenas transfere as marcações da folha para o sistema. As correções de notas serão feitas pela Coordenação posteriormente.")
    
    with st.form("form_digitacao", clear_on_submit=True):
        nome_aluno = st.text_input("👤 Nome do Aluno (Opcional):", max_chars=100)
        
        st.markdown("**📌 Frequência (Marcação)**")
        col_f1, col_f2 = st.columns(2)
        with col_f1: freq_d = st.radio("Dezena (D):", ["0","1","2","3","4","5","6","7","8","9"], horizontal=True)
        with col_f2: freq_u = st.radio("Unidade (U):", ["0","1","2","3","4","5","6","7","8","9"], horizontal=True)
            
        st.markdown("**📝 Respostas (Marcação)**")
        cols_resp = st.columns(3) 
        respostas_marcadas = {}
        
        opcoes_visuais = ["A", "B", "C", "D", "Branco", "Rasura"]
        mapa_valores = {"A":"A", "B":"B", "C":"C", "D":"D", "Branco":"-", "Rasura":"*"}

        for q in range(1, total_q_global + 1):
            col_idx = (q - 1) % 3
            with cols_resp[col_idx]:
                escolha = st.radio(f"Q.{q:02d}", options=opcoes_visuais, index=4, horizontal=True)
                respostas_marcadas[q] = mapa_valores[escolha]
            
        if st.form_submit_button("💾 Salvar Aluno e Avançar"):
            nova_freq = freq_d + freq_u
            resp_str = "".join([respostas_marcadas[q] for q in range(1, total_q_global + 1)])
            novo_dado = {"Frequencia": nova_freq, "Nome_Aluno": nome_aluno, "Respostas_Brutas": resp_str}
            
            df_novo = pd.DataFrame([novo_dado])
            if os.path.exists(ARQUIVO_TEMP): df_novo.to_csv(ARQUIVO_TEMP, mode='a', header=False, index=False, sep=";")
            else: df_novo.to_csv(ARQUIVO_TEMP, index=False, sep=";")
            st.success(f"✅ Aluno(a) salvo(a) com sucesso!")

    st.markdown("---")
    st.markdown("#### Fechamento da Turma")
    
    if os.path.exists(ARQUIVO_TEMP):
        df_temp = pd.read_csv(ARQUIVO_TEMP, sep=";", dtype=str)
        if "Nome_Aluno" not in df_temp.columns: df_temp["Nome_Aluno"] = ""
        df_temp["Nome_Aluno"] = df_temp["Nome_Aluno"].fillna("")
        
        st.write(f"**Total de Alunos Digitados:** {len(df_temp)}")
        st.dataframe(df_temp[["Frequencia", "Nome_Aluno", "Respostas_Brutas"]])
        
        col_exp1, col_exp2 = st.columns(2)
        with col_exp1:
            # O DIGITADOR BAIXA APENAS O ARQUIVO CRU (SEM NOTAS)
            st.download_button(
                label="📥 Baixar Dados da Turma (Entregar à Coordenação)", 
                data=df_temp.to_csv(index=False, sep=";"), 
                file_name=f"respostas_brutas_turma_{modelo}.csv", 
                mime="text/csv", 
                type="primary"
            )
        with col_exp2:
            if st.button("🗑️ Limpar Sessão Atual (Iniciar Nova Turma)"):
                os.remove(ARQUIVO_TEMP)
                st.rerun()
    else:
        st.info("Aguardando inserção de alunos.")
