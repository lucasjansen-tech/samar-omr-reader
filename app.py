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
import zipfile
import hashlib
import uuid
from datetime import datetime

st.set_page_config(layout="wide", page_title="SAMAR GRID PRO")

# ====================================================================
# FUNÇÃO DE SEGURANÇA E INICIALIZAÇÃO DE BANCOS
# ====================================================================
def hash_senha(senha):
    return hashlib.sha256(senha.encode()).hexdigest()

DB_USUARIOS = "usuarios_samar.csv"
if not os.path.exists(DB_USUARIOS):
    pd.DataFrame([{
        "Nome": "Coordenação Master", 
        "Email": "admin", 
        "Senha": hash_senha("coted2026"),
        "Perfil": "Administrador"
    }]).to_csv(DB_USUARIOS, index=False, sep=";")
else:
    df_check = pd.read_csv(DB_USUARIOS, sep=";", dtype=str)
    if 'Perfil' not in df_check.columns:
        df_check['Perfil'] = 'Digitador'
        df_check.loc[0, 'Perfil'] = 'Administrador' 
        df_check.to_csv(DB_USUARIOS, index=False, sep=";")

# NOVO BANCO DE DADOS: ATAS DE OCORRÊNCIA
DB_OCORRENCIAS = "atas_ocorrencias_samar.csv"
if not os.path.exists(DB_OCORRENCIAS):
    pd.DataFrame(columns=[
        "Data_Registro", "Escola", "Ano_Ensino", "Turma", "Turno", 
        "Aplicador", "Revisor_Digitador", "Ocorrencia"
    ]).to_csv(DB_OCORRENCIAS, index=False, sep=";")

if 'usuario_logado' not in st.session_state:
    st.session_state['usuario_logado'] = None
    st.session_state['nome_logado'] = None
    st.session_state['perfil_logado'] = None

if 'reset_key' not in st.session_state:
    st.session_state['reset_key'] = 0

# ====================================================================
# FUNÇÃO GERADORA DE GABARITOS DIGITAIS (ZIP)
# ====================================================================
def gerar_zip_gabaritos(df, conf_prova, modelo_prova):
    id_unico = uuid.uuid4().hex
    fn_pdf = f"base_temp_{modelo_prova}_{id_unico}.pdf"
    
    gerar_pdf(conf_prova, fn_pdf, conf_prova.titulo_prova, conf_prova.subtitulo, {'esq':None, 'cen':None, 'dir':None})
    with open(fn_pdf, "rb") as f: pages = convert_from_bytes(f.read(), dpi=200)
    base_cv = np.array(pages[0])
    
    if base_cv.ndim == 2: base_cv = cv2.cvtColor(base_cv, cv2.COLOR_GRAY2BGR)
    else: base_cv = cv2.cvtColor(base_cv, cv2.COLOR_RGB2BGR)
    base_cv = cv2.resize(base_cv, (conf_prova.REF_W, conf_prova.REF_H))
    
    try: os.remove(fn_pdf)
    except: pass
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        for _, row in df.iterrows():
            img_aluno = base_cv.copy()
            escola = str(row.get("Escola", ""))
            ano = str(row.get("Ano_Ensino", ""))
            turma = str(row.get("Turma", ""))
            turno = str(row.get("Turno", ""))
            freq = str(row.get("Frequencia", "00")).zfill(2)
            nome = str(row.get("Nome_Aluno", ""))
            respostas = str(row.get("Respostas_Brutas", ""))
            
            cor_caneta = (139, 0, 0) 
            cv2.putText(img_aluno, f"ESCOLA: {escola}", (45, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.7, cor_caneta, 2)
            cv2.putText(img_aluno, f"ALUNO(A): {nome}", (45, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, cor_caneta, 2)
            cv2.putText(img_aluno, f"ANO: {ano}   TURMA: {turma}   TURNO: {turno}   FREQ: {freq}", (45, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.7, cor_caneta, 2)
            
            for grid in conf_prova.grids:
                x1, x2 = int(grid.x_start * conf_prova.REF_W), int(grid.x_end * conf_prova.REF_W)
                y1, y2 = int(grid.y_start * conf_prova.REF_H), int(grid.y_end * conf_prova.REF_H)
                cell_w, cell_h = (x2 - x1) / grid.cols, (y2 - y1) / grid.rows
                raio = int(min(cell_w, cell_h) * 0.25)
                
                for r in range(grid.rows):
                    marcada_col = -1
                    if grid.labels == ["D", "U"]:
                        if len(freq) == 2:
                            if r == int(freq[0]): marcada_col = 0
                            if r == int(freq[1]): marcada_col = 1
                    else:
                        q_idx = (grid.questao_inicial + r) - 1
                        if q_idx < len(respostas) and respostas[q_idx] in grid.labels:
                            marcada_col = grid.labels.index(respostas[q_idx])
                    
                    if marcada_col != -1:
                        cx, cy = int(x1 + (marcada_col * cell_w) + (cell_w / 2)), int(y1 + (r * cell_h) + (cell_h / 2))
                        cv2.circle(img_aluno, (cx, cy), raio + 4, (0, 0, 0), -1) 
            
            is_success, buffer = cv2.imencode(".jpg", img_aluno)
            if is_success:
                nome_arq = nome.replace(" ", "_") if nome else "Sem_Nome"
                zf.writestr(f"Gabarito_F{freq}_{nome_arq}.jpg", buffer.tobytes())
    return zip_buffer.getvalue()

# ====================================================================
# TELA CENTRAL DE LOGIN UNIFICADO
# ====================================================================
if not st.session_state['usuario_logado']:
    st.title("🖨️ Sistema SAMAR - Acesso Restrito")
    st.info("Insira suas credenciais corporativas. O sistema identificará automaticamente o seu nível de acesso.")
    
    with st.container(border=True):
        email_input = st.text_input("E-mail ou Usuário:")
        senha_input = st.text_input("Senha:", type="password")
        
        if st.button("Entrar no Sistema 🚀", type="primary"):
            df_users = pd.read_csv(DB_USUARIOS, sep=";", dtype=str)
            senha_criptografada = hash_senha(senha_input)
            match = df_users[(df_users['Email'] == email_input) & (df_users['Senha'] == senha_criptografada)]
            
            if not match.empty:
                st.session_state['usuario_logado'] = email_input
                st.session_state['nome_logado'] = match.iloc[0]['Nome']
                st.session_state['perfil_logado'] = match.iloc[0]['Perfil']
                st.rerun()
            else:
                if email_input == "admin" and senha_input == "coted2026":
                    st.session_state['usuario_logado'] = "admin"
                    st.session_state['nome_logado'] = "Coordenação Master"
                    st.session_state['perfil_logado'] = "Administrador"
                    st.rerun()
                else:
                    st.error("❌ Usuário ou Senha incorretos.")
    st.stop()

# ====================================================================
# BARRA LATERAL PARA USUÁRIOS LOGADOS
# ====================================================================
st.sidebar.markdown("### 👤 Sessão Ativa")
st.sidebar.success(f"**{st.session_state['nome_logado']}**\n\nNível: {st.session_state['perfil_logado']}")
if st.sidebar.button("🚪 Sair do Sistema (Logout)"):
    st.session_state.clear()
    st.rerun()

is_admin = (st.session_state['perfil_logado'] == "Administrador")

# ====================================================================
# CARREGAMENTO DO MODELO DE PROVA
# ====================================================================
st.title("🖨️ Sistema SAMAR - Operação Descentralizada")

modelos_disponiveis = list(TIPOS_PROVA.keys())
idx_padrao = next((i for i, m in enumerate(modelos_disponiveis) if "18" in m), 0)

modelo = st.selectbox("Selecione o Modelo de Prova:", modelos_disponiveis, index=idx_padrao)
conf = TIPOS_PROVA[modelo]
total_q_global = int(modelo.split('_')[1])

mapa_disc_global = {}
tot_disc_global = {}
for g in conf.grids:
    if g.questao_inicial > 0:
        disc = g.texto_extra if g.texto_extra else "Geral"
        if disc not in tot_disc_global: tot_disc_global[disc] = 0
        tot_disc_global[disc] += g.rows
        for r in range(g.rows): mapa_disc_global[g.questao_inicial + r] = disc

if is_admin:
    # A NOVA ABA 6 PARA ATAS FOI INCLUÍDA AQUI:
    tabs = st.tabs(["1. Gerador", "2. Leitor Robô", "3. Cartão Digital", "4. Corretor Lotes", "5. 👥 Usuários", "6. 📋 Atas Registradas"])
    tab1, tab2, tab3, tab4, tab5, tab6 = tabs
else:
    tabs = st.tabs(["📝 Cartão-Resposta Digital (Área de Transcrição)"])
    tab3 = tabs[0]

# ====================================================================
# ABA 1: GERADOR DE PDF (Admin)
# ====================================================================
if is_admin:
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
            if st.button("🚀 Gerar Arquivo Pronto para Impressão", use_container_width=True):
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
                    with open(fn, "rb") as f: st.download_button(f"📥 Baixar Arquivo {ext.upper()}", f, fn, mime, use_container_width=True)

# ====================================================================
# ABA 2: LEITURA POR IMAGEM (Admin)
# ====================================================================
if is_admin:
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
                try:
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
                        
                        st.markdown("---")
                        st.write(f"#### Resultados - Aluno da Frequência: {freq}")
                        
                        c1, c2 = st.columns([1, 1])
                        with c1: st.image(vis, use_container_width=True)
                        with c2: 
                            st.success(f"**Acertos Totais:** {acertos} de {len(gab_oficial)} questões")
                            for disc in tot_disc_global.keys():
                                st.info(f"**{disc}:** {acertos_disciplina[disc]} acertos")
                        
                        if "correcao_detalhada" in res:
                            with st.expander(f"🔍 Abrir Correção Detalhada por Questão (Aluno {freq})"):
                                df_detalhe = pd.DataFrame.from_dict(res["correcao_detalhada"], orient="index")
                                def color_status(val):
                                    if val == 'Correto': return 'color: #2e7d32; font-weight: bold'
                                    elif val == 'Correto (Anulada)': return 'color: #0288d1; font-weight: bold'
                                    elif val == 'Incorreto' or val == 'Múltiplas Marcações': return 'color: #d32f2f; font-weight: bold'
                                    return 'color: #f57c00' 
                                st.dataframe(df_detalhe.style.map(color_status, subset=['Status']), use_container_width=True)
                except Exception as e:
                    st.error(f"Erro ao ler o arquivo {arquivo.name}. Certifique-se de que é uma imagem legível ou um PDF válido.")
                            
            if resultados_lote:
                st.markdown("---")
                df_export = pd.DataFrame(resultados_lote)
                df_export['Ordem_Num'] = pd.to_numeric(df_export['Frequencia'], errors='coerce')
                df_export = df_export.sort_values(by='Ordem_Num', ascending=True, na_position='last').drop(columns=['Ordem_Num']) 
                nome_arq_t2 = st.text_input("Nome do arquivo de exportação final:", value=f"samar_robo_{modelo}.csv")
                st.download_button("📥 Baixar CSV Corrigido", df_export.to_csv(index=False, sep=";"), nome_arq_t2, "text/csv", type="primary")

# ====================================================================
# ABA 4: MOTOR DE CORREÇÃO EM LOTE PARA CSVs (Admin)
# ====================================================================
if is_admin:
    with tab4:
        st.markdown("### 🛠️ Corretor de Arquivos Brutos (Digitadores)")
        st.info("Pegue os arquivos '.csv' que os digitadores te enviaram, defina o Gabarito e deixe o sistema processar as notas e porcentagens.")
        
        st.markdown("#### 1. Gabarito Oficial da Turma/Escola")
        gabarito_admin = st.text_input(f"Letras do Gabarito Oficial ({total_q_global} questões):", value="A"*total_q_global, key="gab_t4").upper().strip()
        gab_dict_admin = {}
        if len(gabarito_admin) >= total_q_global:
            for i, char in enumerate(gabarito_admin[:total_q_global]):
                gab_dict_admin[i+1] = "NULA" if char in ["X", "N"] else char

        st.markdown("#### 2. Processar Lotes")
        lote_bruto = st.file_uploader("Suba os arquivos CSVs gerados pela equipe:", type=["csv"], accept_multiple_files=True)
        nome_arq_admin = st.text_input("Nome do arquivo final a ser gerado:", value=f"samar_dados_consolidados_{modelo}.csv")
        
        if lote_bruto and st.button("⚙️ Corrigir Lotes e Gerar CSV Final", type="primary"):
            todos_resultados = []
            arquivos_com_erro = 0
            
            for arq in lote_bruto:
                try:
                    df_bruto = pd.read_csv(arq, sep=";", dtype=str)
                    
                    if "Respostas_Brutas" not in df_bruto.columns or "Frequencia" not in df_bruto.columns:
                        st.error(f"⚠️ Arquivo ignorado: '{arq.name}' não possui as colunas padrão do SAMAR.")
                        arquivos_com_erro += 1
                        continue
                        
                    for col in ["Escola", "Ano_Ensino", "Turma", "Turno", "Nome_Aluno"]:
                        if col not in df_bruto.columns: df_bruto[col] = ""
                    df_bruto = df_bruto.fillna("")
                    
                    for index, row in df_bruto.iterrows():
                        aluno_escola = row["Escola"]
                        aluno_ano = row["Ano_Ensino"]
                        aluno_turma = row["Turma"]
                        aluno_turno = row["Turno"] 
                        aluno_f = row["Frequencia"]
                        aluno_nome = row["Nome_Aluno"]
                        respostas_brutas = row["Respostas_Brutas"]
                        
                        aluno_processado = {
                            "Escola": aluno_escola, 
                            "Ano_Ensino": aluno_ano, 
                            "Turma": aluno_turma, 
                            "Turno": aluno_turno, 
                            "Frequencia": aluno_f, 
                            "Nome": aluno_nome
                        }
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
                except Exception as e:
                    st.error(f"⚠️ O arquivo '{arq.name}' falhou durante a leitura.")
                    arquivos_com_erro += 1

            if todos_resultados:
                df_final_admin = pd.DataFrame(todos_resultados)
                df_final_admin['Ordem_Num'] = pd.to_numeric(df_final_admin['Frequencia'], errors='coerce')
                df_final_admin = df_final_admin.sort_values(by=['Escola', 'Ano_Ensino', 'Turma', 'Turno', 'Ordem_Num'], ascending=[True, True, True, True, True], na_position='last').drop(columns=['Ordem_Num']) 
                
                if arquivos_com_erro == 0:
                    st.success(f"✅ Sucesso absoluto! {len(df_final_admin)} alunos foram processados sem nenhum erro.")
                else:
                    st.warning(f"⚠️ Parcial: {len(df_final_admin)} alunos foram processados, mas {arquivos_com_erro} arquivo(s) apresentaram erros.")
                    
                st.download_button("📥 Baixar CSV Consolidado", df_final_admin.to_csv(index=False, sep=";"), nome_arq_admin, "text/csv", type="primary")

# ====================================================================
# ABA 5: GESTÃO DE USUÁRIOS (Admin)
# ====================================================================
if is_admin:
    with tab5:
        st.markdown("### 👥 Controle de Usuários e Permissões")
        st.info("Crie acessos para Administradores (acesso total) ou Digitadores (apenas transcrição).")
        
        df_usuarios = pd.read_csv(DB_USUARIOS, sep=";", dtype=str)
        st.dataframe(df_usuarios[["Nome", "Email", "Perfil"]], use_container_width=True)
        
        st.markdown("---")
        col_add, col_edit = st.columns(2)
        
        with col_add:
            with st.container(border=True):
                st.markdown("#### ➕ Criar Novo Usuário")
                with st.form("form_add_user", clear_on_submit=True):
                    novo_nome = st.text_input("Nome Completo:")
                    novo_email = st.text_input("E-mail (Login):")
                    nova_senha = st.text_input("Senha:", type="password")
                    novo_perfil = st.selectbox("Nível de Acesso:", ["Digitador", "Administrador"])
                    
                    if st.form_submit_button("Cadastrar Usuário", type="primary", use_container_width=True):
                        if novo_nome and novo_email and nova_senha:
                            if novo_email in df_usuarios['Email'].values:
                                st.error("⚠️ Este e-mail já está cadastrado!")
                            else:
                                novo_user = pd.DataFrame([{"Nome": novo_nome, "Email": novo_email, "Senha": hash_senha(nova_senha), "Perfil": novo_perfil}])
                                novo_user.to_csv(DB_USUARIOS, mode='a', header=False, index=False, sep=";")
                                st.success(f"✅ Usuário '{novo_nome}' cadastrado como {novo_perfil}!")
                                st.rerun()
                        else:
                            st.error("Preencha todos os campos.")

        with col_edit:
            with st.container(border=True):
                st.markdown("#### ✏️ Editar / Excluir Usuário")
                if not df_usuarios.empty:
                    user_to_edit = st.selectbox("Selecione o E-mail do Usuário:", df_usuarios['Email'].tolist())
                    nova_senha_edit = st.text_input("Nova Senha (deixe em branco para não alterar):", type="password")
                    
                    col_btn1, col_btn2 = st.columns(2)
                    with col_btn1:
                        if st.button("💾 Atualizar Senha", use_container_width=True):
                            if nova_senha_edit:
                                df_usuarios.loc[df_usuarios['Email'] == user_to_edit, 'Senha'] = hash_senha(nova_senha_edit)
                                df_usuarios.to_csv(DB_USUARIOS, index=False, sep=";")
                                st.success("Senha atualizada com sucesso!")
                                st.rerun()
                            else:
                                st.warning("Digite a nova senha.")
                    with col_btn2:
                        if st.button("🗑️ Excluir", use_container_width=True):
                            if len(df_usuarios) > 1:
                                df_usuarios = df_usuarios[df_usuarios['Email'] != user_to_edit]
                                df_usuarios.to_csv(DB_USUARIOS, index=False, sep=";")
                                st.success("Usuário excluído!")
                                st.rerun()
                            else:
                                st.error("Você não pode excluir o último usuário do sistema.")
                else:
                    st.info("Nenhum usuário cadastrado.")

# ====================================================================
# NOVA ABA 6: ATAS DE OCORRÊNCIA (Admin)
# ====================================================================
if is_admin:
    with tab6:
        st.markdown("### 📋 Livro de Atas e Ocorrências")
        st.info("Painel central de monitoramento de problemas físicos das provas relatados pelos digitadores em tempo real.")

        if os.path.exists(DB_OCORRENCIAS):
            df_atas = pd.read_csv(DB_OCORRENCIAS, sep=";", dtype=str)
            if not df_atas.empty:
                st.dataframe(df_atas, use_container_width=True)
                st.download_button(
                    label="📥 Exportar Livro de Atas (Excel/CSV)",
                    data=df_atas.to_csv(index=False, sep=";"),
                    file_name=f"atas_ocorrencias_samar_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    type="primary"
                )
            else:
                st.success("Nenhuma ocorrência registrada até o momento.")
        else:
            st.success("Nenhuma ocorrência registrada até o momento.")

# ====================================================================
# ABA 3 COMPARTILHADA: CARTÃO-RESPOSTA DIGITAL E ATA (TRANSCRIÇÃO)
# ====================================================================
with tab3:
    nome_operador = st.session_state['nome_logado']
    nome_arquivo_seguro = st.session_state['usuario_logado'].replace("@", "_").replace(".", "_")
    ARQUIVO_TEMP = f"temp_transcricao_{modelo}_{nome_arquivo_seguro}.csv"
    st.session_state['ARQUIVO_TEMP'] = ARQUIVO_TEMP
    
    # RECUPERAÇÃO MÁGICA
    if os.path.exists(ARQUIVO_TEMP):
        try:
            df_recuperacao = pd.read_csv(ARQUIVO_TEMP, sep=";", dtype=str)
            if not df_recuperacao.empty:
                ultima_linha = df_recuperacao.iloc[-1]
                if not st.session_state.get("escola_val") and "Escola" in ultima_linha:
                    st.session_state.escola_val = str(ultima_linha["Escola"])
                if not st.session_state.get("ano_val") and "Ano_Ensino" in ultima_linha:
                    st.session_state.ano_val = str(ultima_linha["Ano_Ensino"])
                if not st.session_state.get("turma_val") and "Turma" in ultima_linha:
                    st.session_state.turma_val = str(ultima_linha["Turma"])
                if not st.session_state.get("turno_val") and "Turno" in ultima_linha:
                    st.session_state.turno_val = str(ultima_linha["Turno"])
        except: pass

    # MEMÓRIA PERSISTENTE E CALLBACKS
    for k in ["escola_val", "ano_val", "turma_val", "turno_val"]:
        if k not in st.session_state: st.session_state[k] = ""
        
    def sync_header():
        rk = st.session_state.reset_key
        if f"_escola_{rk}" in st.session_state: st.session_state.escola_val = st.session_state[f"_escola_{rk}"]
        if f"_ano_{rk}" in st.session_state: st.session_state.ano_val = st.session_state[f"_ano_{rk}"]
        if f"_turma_{rk}" in st.session_state: st.session_state.turma_val = st.session_state[f"_turma_{rk}"]
        if f"_turno_{rk}" in st.session_state: st.session_state.turno_val = st.session_state[f"_turno_{rk}"]

    mapa_valores_global = {"A":"A", "B":"B", "C":"C", "D":"D", "Branco":"-", "Rasura":"*"}
    
    def salvar_e_limpar_callback():
        sync_header() 
        
        if not st.session_state.escola_val or not st.session_state.ano_val or not st.session_state.turma_val or not st.session_state.turno_val:
            st.session_state.msg_erro = "⚠️ Atenção: Preencha a 'Escola', o 'Ano', a 'Turma' e o 'Turno' no topo antes de salvar."
            return
            
        nova_freq = st.session_state.freq_d + st.session_state.freq_u
        resp_str = "".join([mapa_valores_global[st.session_state[f"q_{q}"]] for q in range(1, total_q_global + 1)])
        
        novo_dado = {
            "Escola": st.session_state.escola_val, 
            "Ano_Ensino": st.session_state.ano_val, 
            "Turma": st.session_state.turma_val, 
            "Turno": st.session_state.turno_val, 
            "Frequencia": nova_freq, 
            "Nome_Aluno": st.session_state.nome_aluno_input, 
            "Respostas_Brutas": resp_str
        }
        df_novo = pd.DataFrame([novo_dado])
        
        arq = st.session_state.ARQUIVO_TEMP
        if os.path.exists(arq): df_novo.to_csv(arq, mode='a', header=False, index=False, sep=";")
        else: df_novo.to_csv(arq, index=False, sep=";")
        
        st.session_state.msg_sucesso = f"✅ O Aluno de Frequência {nova_freq} foi gravado com sucesso!"
        
        st.session_state.nome_aluno_input = ""
        st.session_state.freq_d = "0"
        st.session_state.freq_u = "0"
        for q in range(1, total_q_global + 1):
            st.session_state[f"q_{q}"] = "Branco"

    if "freq_d" not in st.session_state: st.session_state.freq_d = "0"
    if "freq_u" not in st.session_state: st.session_state.freq_u = "0"
    if "nome_aluno_input" not in st.session_state: st.session_state.nome_aluno_input = ""
    for q in range(1, 100): 
        if f"q_{q}" not in st.session_state: st.session_state[f"q_{q}"] = "Branco"

    st.markdown("### 🖱️ Transcrição Intuitiva do Aluno")
    st.info(f"Olá, **{nome_operador}**. Os dados que você digitar aqui serão salvos com segurança em sua sessão exclusiva.")
    
    if "msg_erro" in st.session_state:
        st.error(st.session_state.msg_erro)
        del st.session_state.msg_erro
    if "msg_sucesso" in st.session_state:
        st.success(st.session_state.msg_sucesso)
        del st.session_state.msg_sucesso

    rk = st.session_state.reset_key 
    
    with st.container(border=True):
        st.markdown("#### 🏫 1. Identificação da Turma e Escola")
        st.text_input("Nome da Escola:", value=st.session_state.escola_val, placeholder="Ex: Escola Municipal...", key=f"_escola_{rk}", on_change=sync_header)
        
        col_t1, col_t2, col_t3 = st.columns(3)
        
        anos_lista = ["", "1º Ano", "2º Ano", "3º Ano", "4º Ano", "5º Ano", "6º Ano", "7º Ano", "8º Ano", "9º Ano"]
        idx_ano = anos_lista.index(st.session_state.ano_val) if st.session_state.ano_val in anos_lista else 0
        with col_t1: st.selectbox("Ano de Ensino:", anos_lista, index=idx_ano, key=f"_ano_{rk}", on_change=sync_header)
        
        turmas_lista = ["", "A", "B", "C", "D", "E", "F", "G", "H", "Única"]
        idx_turma = turmas_lista.index(st.session_state.turma_val) if st.session_state.turma_val in turmas_lista else 0
        with col_t2: st.selectbox("Turma:", turmas_lista, index=idx_turma, key=f"_turma_{rk}", on_change=sync_header)
        
        turnos_lista = ["", "Manhã", "Tarde", "Integral", "Noite"]
        idx_turno = turnos_lista.index(st.session_state.turno_val) if st.session_state.turno_val in turnos_lista else 0
        with col_t3: st.selectbox("Turno:", turnos_lista, index=idx_turno, key=f"_turno_{rk}", on_change=sync_header)

    st.write("")

    with st.container(border=True):
        st.markdown("#### 👤 2. Preenchimento do Cartão-Resposta")
        st.text_input("Nome do Aluno (Opcional, mas recomendado para o arquivo visual):", max_chars=100, key="nome_aluno_input")
        
        st.divider()
        
        st.markdown("##### 📌 Frequência do Aluno")
        col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
        with col_f1: 
            st.radio("Dezena (D):", ["0","1","2","3","4","5","6","7","8","9"], horizontal=True, key="freq_d")
        with col_f2: 
            st.radio("Unidade (U):", ["0","1","2","3","4","5","6","7","8","9"], horizontal=True, key="freq_u")
        with col_f3:
            st.markdown(
                f"<div style='text-align: center; border: 2px dashed #4CAF50; border-radius: 10px; padding: 10px;'>"
                f"<p style='margin:0; font-size: 14px; font-weight: bold;'>Número Selecionado:</p>"
                f"<h1 style='margin:0; font-size: 3.5rem; color: #4CAF50;'>{st.session_state.freq_d}{st.session_state.freq_u}</h1>"
                f"</div>", 
                unsafe_allow_html=True
            )
            
        st.divider()
        
        st.markdown("##### 📝 Respostas (Marque de acordo com a prova física)")
        
        blocos_prova = [g for g in conf.grids if g.questao_inicial > 0]
        cols_blocos = st.columns(len(blocos_prova)) 
        opcoes_visuais = ["A", "B", "C", "D", "Branco", "Rasura"]

        for i, bloco in enumerate(blocos_prova):
            with cols_blocos[i]:
                with st.container(border=True):
                    st.markdown(f"**{bloco.titulo}**")
                    st.caption(bloco.texto_extra)
                    for r in range(bloco.rows):
                        q = bloco.questao_inicial + r
                        st.radio(f"Questão {q:02d}", options=opcoes_visuais, horizontal=True, key=f"q_{q}")
            
        st.write("")
        st.button("💾 Salvar Cartão deste Aluno e Limpar Tela", type="primary", use_container_width=True, on_click=salvar_e_limpar_callback)

    st.markdown("---")
    st.markdown("#### 📁 Progresso da Turma e Fechamento")
    
    if os.path.exists(ARQUIVO_TEMP):
        df_temp = pd.read_csv(ARQUIVO_TEMP, sep=";", dtype=str)
        for col in ["Escola", "Ano_Ensino", "Turma", "Turno", "Nome_Aluno", "Frequencia", "Respostas_Brutas"]:
            if col not in df_temp.columns: df_temp[col] = ""
        df_temp = df_temp.fillna("")
        
        for q in range(1, total_q_global + 1):
            df_temp[f"Q{q:02d}"] = df_temp["Respostas_Brutas"].apply(lambda x: x[q-1] if isinstance(x, str) and len(x) >= q else "-")
        
        col_info, col_save = st.columns([4, 1])
        with col_info:
            st.write(f"**Total de Alunos Transcritos nesta sessão:** {len(df_temp)}")
            st.info("💡 **Dica de Edição:** Dê dois cliques na célula da questão abaixo para corrigir a letra. O cabeçalho fica fixo se você rolar a tabela!")
        
        colunas_exibir = ["Escola", "Ano_Ensino", "Turma", "Turno", "Frequencia", "Nome_Aluno"] + [f"Q{q:02d}" for q in range(1, total_q_global + 1)]
        
        config_colunas = {
            "Frequencia": st.column_config.TextColumn("Freq.", max_chars=2, width="small"),
            "Escola": st.column_config.TextColumn(width="medium"),
            "Nome_Aluno": st.column_config.TextColumn("Nome", width="medium"),
        }
        for q in range(1, total_q_global + 1):
            config_colunas[f"Q{q:02d}"] = st.column_config.SelectboxColumn(f"Q{q:02d}", options=["A", "B", "C", "D", "-", "*"], width="small", required=True)

        df_editado_ui = st.data_editor(
            df_temp[colunas_exibir], 
            use_container_width=True,
            num_rows="dynamic", 
            column_config=config_colunas,
            height=400, 
            key=f"editor_{nome_arquivo_seguro}"
        )
        
        df_salvar = df_editado_ui.copy()
        if not df_salvar.empty:
            df_salvar["Respostas_Brutas"] = df_salvar[[f"Q{q:02d}" for q in range(1, total_q_global + 1)]].agg(lambda x: ''.join(x.astype(str)), axis=1)
        else:
            df_salvar["Respostas_Brutas"] = pd.Series(dtype=str)
            
        df_salvar = df_salvar[["Escola", "Ano_Ensino", "Turma", "Turno", "Frequencia", "Nome_Aluno", "Respostas_Brutas"]]
        
        with col_save:
            st.write("")
            if st.button("💾 Salvar Edições na Tabela", use_container_width=True):
                df_salvar.to_csv(ARQUIVO_TEMP, index=False, sep=";")
                st.success("Tabela atualizada com sucesso!")
                st.rerun()
        
        st.write("")
        escola_str = st.session_state.escola_val.replace(" ", "_") if st.session_state.escola_val else "Escola"
        nome_sugerido = f"respostas_brutas_{escola_str}_{st.session_state.ano_val.replace(' ', '_')}_{st.session_state.turma_val}_{st.session_state.turno_val}.csv"
        nome_arq_dig = st.text_input("Nome do arquivo de dados que será baixado:", value=nome_sugerido)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.download_button(
                label="📊 Baixar Dados (CSV)", 
                data=df_salvar.to_csv(index=False, sep=";"), 
                file_name=nome_arq_dig, 
                mime="text/csv", 
                type="primary",
                use_container_width=True
            )
        with c2:
            if st.button("🖼️ Gerar Gabaritos Digitais (ZIP)", use_container_width=True):
                with st.spinner("Gerando backup em imagens..."):
                    zip_data = gerar_zip_gabaritos(df_salvar, conf, modelo) 
                    st.download_button(
                        label="📥 Download Completo (ZIP)",
                        data=zip_data,
                        file_name=f"Gabaritos_Imagens_{escola_str}_{st.session_state.ano_val}_{st.session_state.turma_val}_{st.session_state.turno_val}.zip",
                        mime="application/zip",
                        type="primary",
                        use_container_width=True
                    )
        with c3:
            with st.expander("🗑️ Iniciar Nova Turma", expanded=False):
                st.markdown("<p style='font-size:14px; color:#d32f2f;'><b>⚠️ Atenção:</b> Verifique se você já fez o download do CSV e do ZIP acima antes de prosseguir!</p>", unsafe_allow_html=True)
                
                if st.button("🚨 Apagar Turma e Limpar Tela", use_container_width=True):
                    try: os.remove(ARQUIVO_TEMP)
                    except Exception: pass
                    
                    for campo in ["escola_val", "ano_val", "turma_val", "turno_val"]:
                        st.session_state[campo] = ""
                        
                    st.session_state.reset_key += 1
                    st.rerun()

        # ====================================================================
        # NOVIDADE: ATA DE OCORRÊNCIAS DIGITAL (NO FIM DA PÁGINA)
        # ====================================================================
        st.markdown("---")
        st.markdown("#### 📋 Registrar Ocorrência da Turma (Ata)")
        with st.expander("Clique aqui para relatar problemas com as provas desta turma", expanded=False):
            st.info("Relate provas rasgadas, alunos que assinaram mas não fizeram a prova, ou falta de material.")
            
            with st.form("form_ata", clear_on_submit=True):
                nome_aplicador = st.text_input("Nome do Aplicador da Prova (Físico):")
                texto_ata = st.text_area("Descreva a Ocorrência detalhadamente:")
                
                if st.form_submit_button("💾 Assinar e Enviar Ata de Ocorrência", type="primary"):
                    if not st.session_state.escola_val or not st.session_state.turma_val:
                        st.error("⚠️ Preencha pelo menos a Escola e a Turma no topo da página antes de registrar a ata.")
                    elif not nome_aplicador or not texto_ata:
                        st.error("⚠️ Preencha o nome do Aplicador e a descrição da Ocorrência.")
                    else:
                        nova_ata = {
                            "Data_Registro": datetime.now().strftime("%d/%m/%Y %H:%M"),
                            "Escola": st.session_state.escola_val,
                            "Ano_Ensino": st.session_state.ano_val,
                            "Turma": st.session_state.turma_val,
                            "Turno": st.session_state.turno_val,
                            "Aplicador": nome_aplicador,
                            "Revisor_Digitador": nome_operador,
                            "Ocorrencia": texto_ata
                        }
                        df_ata = pd.DataFrame([nova_ata])
                        df_ata.to_csv(DB_OCORRENCIAS, mode='a', header=False, index=False, sep=";")
                        st.success("✅ Ata de Ocorrência gravada com sucesso! A Coordenação já tem acesso a este registro.")
    else:
        st.info("O painel de controle da turma aparecerá aqui após o registro do primeiro aluno.")
