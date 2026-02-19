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

st.set_page_config(layout="wide", page_title="SAMAR GRID PRO")

# ====================================================================
# INICIALIZAÇÃO DO BANCO DE USUÁRIOS E SESSÃO (NOVO!)
# ====================================================================
DB_USUARIOS = "usuarios_samar.csv"
if not os.path.exists(DB_USUARIOS):
    # Cria o banco com um usuário de teste padrão caso não exista
    pd.DataFrame([{"Nome": "Digitador Teste", "Email": "teste@samar", "Senha": "123"}]).to_csv(DB_USUARIOS, index=False, sep=";")

if 'usuario_logado' not in st.session_state:
    st.session_state['usuario_logado'] = None
    st.session_state['nome_logado'] = None

# ====================================================================
# MENU LATERAL: CONTROLE DE ACESSO (HIERARQUIA E LOGIN)
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
elif perfil == "👨‍💻 Digitador (Transcrição)":
    # Se já estiver logado, mostra o botão de sair na lateral
    if st.session_state['usuario_logado']:
        st.sidebar.success(f"Logado como:\n**{st.session_state['nome_logado']}**")
        if st.sidebar.button("🚪 Sair (Logout)"):
            st.session_state['usuario_logado'] = None
            st.session_state['nome_logado'] = None
            st.rerun()

st.title("🖨️ Sistema SAMAR - Operação Descentralizada")

# BLOQUEIO DE TELA DE LOGIN PARA DIGITADORES
if perfil == "👨‍💻 Digitador (Transcrição)" and not st.session_state['usuario_logado']:
    st.markdown("### 🔒 Acesso Restrito")
    st.info("Insira suas credenciais fornecidas pela Coordenação para iniciar as transcrições.")
    
    with st.container(border=True):
        email_input = st.text_input("E-mail de Acesso:")
        senha_input = st.text_input("Senha:", type="password")
        
        if st.button("Entrar no Sistema", type="primary"):
            df_users = pd.read_csv(DB_USUARIOS, sep=";", dtype=str)
            # Verifica se e-mail e senha batem
            match = df_users[(df_users['Email'] == email_input) & (df_users['Senha'] == senha_input)]
            
            if not match.empty:
                st.session_state['usuario_logado'] = email_input
                st.session_state['nome_logado'] = match.iloc[0]['Nome']
                st.rerun()
            else:
                st.error("❌ E-mail ou Senha incorretos. Tente novamente.")
    st.stop() # Trava o sistema inteiro aqui até fazer o login

modelo = st.selectbox("Selecione o Modelo de Prova:", list(TIPOS_PROVA.keys()))
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

# ====================================================================
# FUNÇÃO GERADORA DE GABARITOS DIGITAIS PREENCHIDOS
# ====================================================================
def gerar_zip_gabaritos(df, conf_prova, modelo_prova, ano_turma, nome_turma):
    fn_pdf = f"base_temp_{modelo_prova}.pdf"
    gerar_pdf(conf_prova, fn_pdf, conf_prova.titulo_prova, conf_prova.subtitulo, {'esq':None, 'cen':None, 'dir':None})
    with open(fn_pdf, "rb") as f: pages = convert_from_bytes(f.read(), dpi=200)
    base_cv = np.array(pages[0])
    if base_cv.ndim == 2: base_cv = cv2.cvtColor(base_cv, cv2.COLOR_GRAY2BGR)
    else: base_cv = cv2.cvtColor(base_cv, cv2.COLOR_RGB2BGR)
    base_cv = cv2.resize(base_cv, (conf_prova.REF_W, conf_prova.REF_H))
    os.remove(fn_pdf)
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        for _, row in df.iterrows():
            img_aluno = base_cv.copy()
            freq = str(row.get("Frequencia", "00")).zfill(2)
            nome = str(row.get("Nome_Aluno", ""))
            respostas = str(row.get("Respostas_Brutas", ""))
            
            texto_carimbo = f"ARQUIVO DIGITAL SAMAR | Ano: {ano_turma} | Turma: {nome_turma} | Freq: {freq} | Aluno: {nome}"
            cv2.putText(img_aluno, texto_carimbo, (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (150, 0, 0), 2)
            
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
# RENDERIZAÇÃO DE ABAS POR PERFIL
# ====================================================================
if perfil == "⚙️ Coordenação (Admin)":
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "1. Gerador", 
        "2. Leitor Robô", 
        "3. Cartão Digital", 
        "4. Corretor Lotes",
        "5. 👥 Usuários (NOVO)" # Nova aba de controle
    ])
    
    # --- ABA 1: GERADOR DE PDF ---
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
                    with open(fn, "rb") as f: st.download_button(f"📥 Baixar Arquivo {ext.upper()}", f, fn, mime)

    # --- ABA 2: LEITURA POR IMAGEM ---
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
                    with c2: 
                        st.success(f"**Geral:** {acertos} / {len(gab_oficial)}")
                        if "correcao_detalhada" in res:
                            with st.expander("🔍 Ver Correção Detalhada por Questão"):
                                df_detalhe = pd.DataFrame.from_dict(res["correcao_detalhada"], orient="index")
                                def color_status(val):
                                    if val == 'Correto': return 'color: #2e7d32; font-weight: bold'
                                    elif val == 'Correto (Anulada)': return 'color: #0288d1; font-weight: bold'
                                    elif val == 'Incorreto' or val == 'Múltiplas Marcações': return 'color: #d32f2f; font-weight: bold'
                                    return 'color: #f57c00' 
                                st.dataframe(df_detalhe.style.map(color_status, subset=['Status']), use_container_width=True)
                            
            if resultados_lote:
                df_export = pd.DataFrame(resultados_lote)
                df_export['Ordem_Num'] = pd.to_numeric(df_export['Frequencia'], errors='coerce')
                df_export = df_export.sort_values(by='Ordem_Num', ascending=True, na_position='last').drop(columns=['Ordem_Num']) 
                nome_arq_t2 = st.text_input("Nome do arquivo de exportação:", value=f"samar_robo_{modelo}.csv")
                st.download_button("📥 Baixar CSV Corrigido", df_export.to_csv(index=False, sep=";"), nome_arq_t2, "text/csv", type="primary")

    # --- ABA 4: MOTOR DE CORREÇÃO EM LOTE PARA CSVs ---
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
        lote_bruto = st.file_uploader("Suba os arquivos 'respostas_brutas_turma.csv' gerados pela equipe:", type=["csv"], accept_multiple_files=True)
        nome_arq_admin = st.text_input("Nome do arquivo final a ser gerado:", value=f"samar_dados_consolidados_{modelo}.csv")
        
        if lote_bruto and st.button("⚙️ Corrigir Lotes e Gerar CSV Final"):
            todos_resultados = []
            
            for arq in lote_bruto:
                df_bruto = pd.read_csv(arq, sep=";", dtype=str)
                for col in ["Ano_Ensino", "Turma", "Nome_Aluno"]:
                    if col not in df_bruto.columns: df_bruto[col] = ""
                df_bruto = df_bruto.fillna("")
                
                for index, row in df_bruto.iterrows():
                    aluno_ano = row["Ano_Ensino"]
                    aluno_turma = row["Turma"]
                    aluno_f = row["Frequencia"]
                    aluno_nome = row["Nome_Aluno"]
                    respostas_brutas = row["Respostas_Brutas"]
                    
                    aluno_processado = {"Ano_Ensino": aluno_ano, "Turma": aluno_turma, "Frequencia": aluno_f, "Nome": aluno_nome}
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
                df_final_admin = df_final_admin.sort_values(by=['Ano_Ensino', 'Turma', 'Ordem_Num'], ascending=[True, True, True], na_position='last').drop(columns=['Ordem_Num']) 
                st.success(f"✅ Sucesso! {len(df_final_admin)} alunos foram corrigidos.")
                st.download_button("📥 Baixar CSV Consolidado", df_final_admin.to_csv(index=False, sep=";"), nome_arq_admin, "text/csv", type="primary")

    # --- ABA 5 (NOVA!): GESTÃO DE USUÁRIOS E DIGITADORES ---
    with tab5:
        st.markdown("### 👥 Gestão de Digitadores")
        st.info("Cadastre a sua equipe aqui. Cada e-mail e senha registrados darão acesso exclusivo ao painel de Transcrição isolado, evitando que um usuário apague ou altere os dados de outro.")
        
        df_usuarios = pd.read_csv(DB_USUARIOS, sep=";", dtype=str)
        st.markdown("#### Usuários Ativos")
        st.dataframe(df_usuarios[["Nome", "Email"]], use_container_width=True)
        
        st.markdown("---")
        st.markdown("#### Adicionar Novo Digitador")
        with st.form("form_add_user", clear_on_submit=True):
            col_u1, col_u2, col_u3 = st.columns(3)
            with col_u1: novo_nome = st.text_input("Nome Completo:")
            with col_u2: novo_email = st.text_input("E-mail de Acesso (Login):")
            with col_u3: nova_senha = st.text_input("Senha:", type="password")
            
            if st.form_submit_button("Cadastrar Usuário"):
                if novo_nome and novo_email and nova_senha:
                    # Verifica se e-mail já existe
                    if novo_email in df_usuarios['Email'].values:
                        st.error("⚠️ Este e-mail já está cadastrado!")
                    else:
                        novo_user = pd.DataFrame([{"Nome": novo_nome, "Email": novo_email, "Senha": nova_senha}])
                        novo_user.to_csv(DB_USUARIOS, mode='a', header=False, index=False, sep=";")
                        st.success(f"✅ Usuário '{novo_nome}' cadastrado com sucesso!")
                        st.rerun()
                else:
                    st.error("Preencha todos os campos para cadastrar.")

else:
    # Perfil Digitador (Acesso restrito, agora protegido por login)
    tab3 = st.tabs(["📝 Cartão-Resposta Digital"])[0]

# ====================================================================
# ABA 3 COMPARTILHADA: CARTÃO-
