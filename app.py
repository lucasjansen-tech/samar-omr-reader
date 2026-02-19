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
st.title("🖨️ Sistema SAMAR - Leitura OMR e Transcrição")

modelo = st.selectbox("Selecione o Modelo de Prova:", list(TIPOS_PROVA.keys()))
conf = TIPOS_PROVA[modelo]

# Adicionamos a 3ª Aba no painel!
tab1, tab2, tab3 = st.tabs(["1. Gerador de PDF", "2. Leitura por Imagem (Robô)", "3. Digitação Manual (Auto-Save)"])

# ====================================================================
# ABA 1: GERADOR COM PERSONALIZAÇÃO (Intocável)
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
            logos_dict = {'esq': logo_esq, 'cen': logo_cen, 'dir': logo_dir}
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
# ABA 2: LEITURA, CORREÇÃO E ANÁLISE ESTATÍSTICA (Intocável)
# ====================================================================
with tab2:
    st.markdown("### 📝 Passo 1: Configurar Gabarito Oficial")
    
    modo_gab = st.radio("Como deseja inserir o gabarito?", 
                        ["Texto Rápido (Copiar/Colar)", "Preenchimento Manual (Por Bloco)"], 
                        horizontal=True, key="modo_gab_t2")
    
    gab_oficial = {}
    total_questoes = int(modelo.split('_')[1])
    blocos = len([g for g in conf.grids if g.questao_inicial > 0])
    questoes_por_bloco = total_questoes // blocos if blocos > 0 else 0
    
    mapa_disciplinas = {}
    total_por_disciplina = {}
    for g in conf.grids:
        if g.questao_inicial > 0:
            disc = g.texto_extra if g.texto_extra else "Geral"
            if disc not in total_por_disciplina: total_por_disciplina[disc] = 0
            total_por_disciplina[disc] += g.rows
            for r in range(g.rows): mapa_disciplinas[g.questao_inicial + r] = disc

    if "Texto Rápido" in modo_gab:
        gabarito_str = st.text_input(f"Cole as {total_questoes} respostas sem espaços:", value="A" * total_questoes, key="gab_t2").upper().strip()
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
    st.markdown("### 📸 Passo 2: Analisar Prova(s) Preenchida(s)")
    up = st.file_uploader("Faça o Upload do PDF ou Imagens:", type=["pdf", "png", "jpg"], accept_multiple_files=True)
    
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
                acertos_disciplina = {disc: 0 for disc in total_por_disciplina}
                
                for q_num in range(1, total_questoes + 1):
                    resp_str = res["respostas"].get(q_num, ".")
                    aluno_dados[f"Letra_Q{q_num:02d}"] = "Múltiplas" if resp_str == "*" else resp_str
                    status = res.get("correcao_detalhada", {}).get(q_num, {}).get("Status", "")
                    is_correct = 1 if "Correto" in status else 0
                    aluno_dados[f"Q{q_num:02d}"] = is_correct
                    
                    disc = mapa_disciplinas.get(q_num)
                    if disc and is_correct: acertos_disciplina[disc] += 1
                
                aluno_dados["Total_Acertos_Geral"] = acertos
                aluno_dados["%_Acerto_Geral"] = round((acertos / total_questoes) * 100, 2) if total_questoes > 0 else 0
                
                for disc, total in total_por_disciplina.items():
                    qtd_acertos = acertos_disciplina[disc]
                    perc = (qtd_acertos / total) * 100 if total > 0 else 0
                    aluno_dados[f"Acertos_{disc.replace(' ', '_')}"] = qtd_acertos
                    aluno_dados[f"%_{disc.replace(' ', '_')}"] = round(perc, 2)
                
                resultados_lote.append(aluno_dados)
                
                st.write(f"#### Resultados - Aluno: {freq}")
                c1, c2 = st.columns([1, 1])
                with c1: st.image(vis, caption="Correção Visual", use_container_width=True)
                with c2:
                    st.info(f"**ID do Aluno:** {freq}")
                    st.success(f"**Geral:** {acertos} / {len(gab_oficial)} ({aluno_dados['%_Acerto_Geral']}%)")
                    for disc in total_por_disciplina.keys():
                        st.write(f"**{disc}:** {acertos_disciplina[disc]} / {total_por_disciplina[disc]} ({aluno_dados[f'%_{disc.replace(chr(32), chr(95))}']}%)")
                        
        if resultados_lote:
            st.markdown("---")
            df_export = pd.DataFrame(resultados_lote)
            df_export['Ordem_Num'] = pd.to_numeric(df_export['Frequencia'], errors='coerce')
            df_export = df_export.sort_values(by='Ordem_Num', ascending=True, na_position='last').drop(columns=['Ordem_Num']) 
            st.write("Prévia dos dados:")
            st.dataframe(df_export)
            st.download_button("📥 Baixar CSV (Calculadora)", df_export.to_csv(index=False, sep=";"), f"samar_leitor_robo_{modelo}.csv", "text/csv", type="primary")

# ====================================================================
# ABA 3: DIGITAÇÃO MANUAL (AUTO-SAVE) - A Nova Solução
# ====================================================================
with tab3:
    st.markdown("### ⌨️ Central de Transcrição Rápida")
    st.info("Neste modo, seus dados são salvos no disco rígido a cada aluno. Se o navegador fechar, seu trabalho não será perdido!")
    
    total_q_tab3 = int(modelo.split('_')[1])
    ARQUIVO_TEMP = f"temp_transcricao_{modelo}.csv"

    # Mapeamento de disciplinas (Idêntico ao Robô para o CSV sair perfeito)
    mapa_disc_t3 = {}
    tot_disc_t3 = {}
    for g in conf.grids:
        if g.questao_inicial > 0:
            disc = g.texto_extra if g.texto_extra else "Geral"
            if disc not in tot_disc_t3: tot_disc_t3[disc] = 0
            tot_disc_t3[disc] += g.rows
            for r in range(g.rows): mapa_disc_t3[g.questao_inicial + r] = disc

    # 1. Configurar Gabarito da Sessão
    st.markdown("#### 1. Gabarito da Turma Atual")
    gabarito_dig = st.text_input(f"Letras do Gabarito Oficial ({total_q_tab3} questões juntas):", value="A"*total_q_tab3, key="gab_t3").upper().strip()
    gab_oficial_t3 = {}
    if len(gabarito_dig) >= total_q_tab3:
        for i, char in enumerate(gabarito_dig[:total_q_tab3]):
            gab_oficial_t3[i+1] = "NULA" if char in ["X", "N"] else char

    st.markdown("---")
    st.markdown("#### 2. Digitar Cartões dos Alunos")
    
    # Formulário blindado com Auto-Clear
    with st.form("form_digitacao", clear_on_submit=True):
        col_freq, col_resp = st.columns([1, 4])
        with col_freq:
            nova_freq = st.text_input("Frequência (Ex: 15)", max_chars=3)
        with col_resp:
            novas_resp = st.text_input(f"Respostas do Aluno (Digite as {total_q_tab3} letras juntas. Ex: ABCD...)", max_chars=total_q_tab3)
            
        salvar_btn = st.form_submit_button("Salvar Aluno (Enter) 💾")
        
        if salvar_btn:
            if nova_freq and len(novas_resp) == total_q_tab3:
                # Cria linha do aluno
                novo_dado = {"Frequencia": nova_freq.zfill(2), "Respostas_Brutas": novas_resp.upper()}
                df_novo = pd.DataFrame([novo_dado])
                
                # Auto-Save no HD
                if os.path.exists(ARQUIVO_TEMP):
                    df_novo.to_csv(ARQUIVO_TEMP, mode='a', header=False, index=False, sep=";")
                else:
                    df_novo.to_csv(ARQUIVO_TEMP, index=False, sep=";")
                st.success(f"✅ Aluno {nova_freq} salvo com sucesso no disco!")
            else:
                st.error("⚠️ Preencha a frequência e todas as letras corretamente antes de salvar.")

    # 3. Mostrar os Salvos e Exportar
    st.markdown("---")
    st.markdown("#### 3. Progresso da Turma e Exportação")
    
    if os.path.exists(ARQUIVO_TEMP):
        df_temp = pd.read_csv(ARQUIVO_TEMP, sep=";", dtype=str)
        st.write(f"**Total de Alunos Salvos:** {len(df_temp)}")
        st.dataframe(df_temp)
        
        col_exp1, col_exp2 = st.columns(2)
        with col_exp1:
            if st.button("📊 Corrigir Turma e Gerar Relatório CSV"):
                resultados_dig = []
                
                for index, row in df_temp.iterrows():
                    aluno_f = row["Frequencia"]
                    respostas_brutas = row["Respostas_Brutas"]
                    
                    aluno_processado = {"Frequencia": aluno_f}
                    acertos_geral = 0
                    acertos_disc = {disc: 0 for disc in tot_disc_t3}
                    
                    # Motor de Correção Manual idêntico ao Robô
                    for q in range(1, total_q_tab3 + 1):
                        letra_marcada = respostas_brutas[q-1] if q-1 < len(respostas_brutas) else "-"
                        gabarito_certo = gab_oficial_t3.get(q, "NULA")
                        
                        aluno_processado[f"Letra_Q{q:02d}"] = letra_marcada
                        
                        is_correct = 0
                        if gabarito_certo == "NULA" or letra_marcada == gabarito_certo:
                            is_correct = 1
                            acertos_geral += 1
                            if mapa_disc_t3.get(q): acertos_disc[mapa_disc_t3[q]] += 1
                            
                        aluno_processado[f"Q{q:02d}"] = is_correct
                    
                    # Fechamento Matemático
                    aluno_processado["Total_Acertos_Geral"] = acertos_geral
                    aluno_processado["%_Acerto_Geral"] = round((acertos_geral / total_q_tab3) * 100, 2) if total_q_tab3 > 0 else 0
                    
                    for disc, total in tot_disc_t3.items():
                        qtd_acertos = acertos_disc[disc]
                        perc = (qtd_acertos / total) * 100 if total > 0 else 0
                        aluno_processado[f"Acertos_{disc.replace(' ', '_')}"] = qtd_acertos
                        aluno_processado[f"%_{disc.replace(' ', '_')}"] = round(perc, 2)
                        
                    resultados_dig.append(aluno_processado)

                # Exportação Binária Final
                df_final_dig = pd.DataFrame(resultados_dig)
                df_final_dig['Ordem_Num'] = pd.to_numeric(df_final_dig['Frequencia'], errors='coerce')
                df_final_dig = df_final_dig.sort_values(by='Ordem_Num', ascending=True, na_position='last').drop(columns=['Ordem_Num']) 
                
                csv_dig = df_final_dig.to_csv(index=False, sep=";")
                st.download_button("📥 Baixar CSV da Turma (Calculadora)", csv_dig, f"samar_transcricao_{modelo}.csv", "text/csv", type="primary")
                st.success("Relatório gerado! Você pode fazer o download acima.")

        with col_exp2:
            if st.button("🗑️ Limpar Turma Atual (Iniciar Nova)"):
                os.remove(ARQUIVO_TEMP)
                st.rerun()
    else:
        st.info("Nenhum aluno salvo ainda nesta sessão.")
