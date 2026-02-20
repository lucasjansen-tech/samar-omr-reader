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
import base64
from datetime import datetime

# ====================================================================
# INJEÇÃO DE DESIGN (CORES SEGURAS PARA AÇÃO)
# ====================================================================
st.set_page_config(layout="wide", page_title="SAMAR GRID PRO")

st.markdown("""
    <style>
    /* Muda a cor dos botões principais para Azul Seguro */
    div.stButton > button[kind="primary"] {
        background-color: #0d6efd !important;
        color: white !important;
        border: 1px solid #0d6efd !important;
        font-weight: bold !important;
        border-radius: 6px !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #0b5ed7 !important;
        border: 1px solid #0b5ed7 !important;
    }
    .stDataFrame { font-size: 14px !important; }
    </style>
""", unsafe_allow_html=True)

# ====================================================================
# CONEXÃO COM O BANCO DE DADOS EM NUVEM (SUPABASE)
# ====================================================================
try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False

SUPABASE_URL = "https://lbcweuwgjivdexzbanjt.supabase.co"
SUPABASE_KEY = "sb_publishable_BccjjvXAWyTFm2uQ6P5qbg_LlFPFw0e"

usa_nuvem = False
if HAS_SUPABASE:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        usa_nuvem = True
    except Exception: pass

if not HAS_SUPABASE: st.error("⚠️ Atenção: A biblioteca do Supabase não foi carregada.")

# ====================================================================
# LISTAS OFICIAIS E BANCOS LOCAIS
# ====================================================================
ESCOLAS_SAMAR = [
    "", "COLÉGIO MILITAR TIRADENTES XII", "UNIDADE ESCOLAR JOSÉ LISBOA", "UNIDADE ESCOLAR MANOEL BATISTA",
    "UNIDADE ESCOLAR NOVA ARAÇAGI", "UNIDADE ESCOLAR SOCORRO MAGALHÃES", "UNIDADE ESCOLAR SÃO JOAQUIM",
    "UNIDADE ESCOLAR VILA NOVA", "UNIDADE ESCOLAR VILA SÃO JOÃO", "UNIDADE INTEGRADA CRIANÇA ESPERANÇA",
    "UNIDADE INTEGRADA HENRIQUE DE LA ROQUE", "UNIDADE INTEGRADA JARBAS PASSARINHO", "UNIDADE INTEGRADA MARCONE CALDAS",
    "UNIDADE INTEGRADA PROFESSORA MARIA ROSA REIS TRINDADE", "UNIDADE INTEGRADA RURAL BOA ESPERANÇA",
    "UNIDADE INTEGRADA SANTO ANTÔNIO", "UNIDADE INTEGRADA SARNEY FILHO"
]

ANOS_ENSINO = ["", "1º Ano", "2º Ano", "3º Ano", "4º Ano", "5º Ano", "6º Ano", "7º Ano", "8º Ano", "9º Ano"]
TURMAS_DISP = ["", "A", "B", "C", "D", "E", "F", "G", "H", "Única"]
TURNOS_DISP = ["", "Manhã", "Tarde", "Integral", "Noite"]

def hash_senha(senha): return hashlib.sha256(senha.encode()).hexdigest()

DB_USUARIOS = "usuarios_samar.csv"
if not os.path.exists(DB_USUARIOS): pd.DataFrame([{"Nome": "Coordenação Master", "Email": "admin", "Senha": hash_senha("coted2026"), "Perfil": "Administrador"}]).to_csv(DB_USUARIOS, index=False, sep=";")
else:
    df_check = pd.read_csv(DB_USUARIOS, sep=";", dtype=str)
    if 'Perfil' not in df_check.columns:
        df_check['Perfil'] = 'Digitador'
        df_check.loc[0, 'Perfil'] = 'Administrador' 
        df_check.to_csv(DB_USUARIOS, index=False, sep=";")

DB_OCORRENCIAS = "atas_ocorrencias_samar.csv"
if not os.path.exists(DB_OCORRENCIAS): pd.DataFrame(columns=["etapa", "Data_Registro", "Escola", "Ano_Ensino", "Turma", "Turno", "Aplicador", "Revisor_Digitador", "Ocorrencia"]).to_csv(DB_OCORRENCIAS, index=False, sep=";")

DB_ETAPAS = "etapas_samar.csv"
if not os.path.exists(DB_ETAPAS): pd.DataFrame([{"Nome_Etapa": "Avaliação Diagnóstica"}]).to_csv(DB_ETAPAS, index=False, sep=";")

if 'usuario_logado' not in st.session_state:
    st.session_state['usuario_logado'] = None
    st.session_state['nome_logado'] = None
    st.session_state['perfil_logado'] = None

if 'turma_confirmada' not in st.session_state: st.session_state['turma_confirmada'] = False

# ====================================================================
# GERADORES DE DOCUMENTOS
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

def gerar_html_ata(etapa, escola, ano, turma, turno, aplicador, ocorrencia, revisor, data):
    logo_html = ""
    img_path = "Frame 18.png"
    if os.path.exists(img_path):
        try:
            with open(img_path, "rb") as img_file:
                encoded_string = base64.b64encode(img_file.read()).decode()
                logo_html = f'<div style="text-align: center; margin-bottom: 30px;"><img src="data:image/png;base64,{encoded_string}" style="max-width: 100%; height: auto; border-radius: 8px; box-shadow: 0px 4px 6px rgba(0,0,0,0.1);" /></div>'
        except Exception: pass

    html = f"""
    <html><head><meta charset="UTF-8"><title>Ata - {escola}</title><style>body {{ font-family: Arial; margin: 40px; line-height: 1.6; max-width: 800px; margin: auto; padding: 20px; }} .header {{ text-align: center; font-weight: bold; font-size: 20px; text-decoration: underline; margin-bottom: 20px; }} .sub-header {{ text-align: center; font-size: 16px; font-weight: bold; margin-bottom: 40px; color: #444; }} .linha {{ margin-bottom: 15px; font-size: 16px; border-bottom: 1px dotted #ccc; padding-bottom: 5px; }} .label {{ font-weight: bold; color: #333; }} .caixa-ocorrencia {{ border: 1px solid #000; padding: 20px; min-height: 250px; margin-top: 10px; margin-bottom: 50px; white-space: pre-wrap; background-color: #fcfcfc; }} .assinatura {{ margin-top: 80px; text-align: center; }} .linha-assinatura {{ border-top: 1px solid #000; width: 400px; margin: 0 auto; margin-bottom: 10px; }} .sub-info {{ font-size: 12px; color: #555; margin-top: 5px; }}</style></head><body>{logo_html}<div class="header">ATA DE OCORRÊNCIAS DE CORREÇÃO DO SAMAR</div><div class="sub-header">ETAPA AVALIADA: {etapa.upper()}</div><div class="linha"><span class="label">ESCOLA:</span> {escola}</div><div class="linha"><span class="label">TURMA / ANO:</span> {turma} - {ano} ({turno})</div><div class="linha"><span class="label">APLICADOR:</span> {aplicador}</div><div style="margin-top: 40px;"><span class="label">OCORRÊNCIAS:</span></div><div class="caixa-ocorrencia">{ocorrencia}</div><div class="assinatura"><div class="linha-assinatura"></div><div class="label">ASSINATURA DO REVISOR</div><div style="font-size: 18px; font-family: 'Courier New'; margin-top: 10px;">{revisor}</div><div class="sub-info">Documento gerado digitalmente pelo Sistema SAMAR GRID PRO em {data}</div></div></body></html>
    """
    return html

def gerar_zip_atas(df_atas):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        for idx, row in df_atas.iterrows():
            eta = str(row.get("etapa", "Padrão"))
            esc, tur, ano, tur_no = str(row.get("Escola", "")), str(row.get("Turma", "")), str(row.get("Ano_Ensino", "")), str(row.get("Turno", ""))
            apl, oco, rev, dat = str(row.get("Aplicador", "")), str(row.get("Ocorrencia", "")), str(row.get("Revisor_Digitador", "")), str(row.get("Data_Registro", ""))
            html_content = gerar_html_ata(eta, esc, ano, tur, tur_no, apl, oco, rev, dat)
            nome_arq = f"Ata_{eta.replace(' ', '_')}_{esc.replace(' ', '_')}_{tur.replace(' ', '_')}_{idx}.html"
            zf.writestr(nome_arq, html_content.encode('utf-8'))
    return zip_buffer.getvalue()

# ====================================================================
# TELA CENTRAL DE LOGIN
# ====================================================================
if not st.session_state['usuario_logado']:
    st.title("🖨️ Sistema SAMAR - Acesso Restrito")
    st.info("Insira suas credenciais corporativas para acessar a nuvem.")
    with st.container(border=True):
        email_input = st.text_input("E-mail ou Usuário:")
        senha_input = st.text_input("Senha:", type="password")
        if st.button("Entrar no Sistema", type="primary"):
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
# BARRA LATERAL E INICIALIZAÇÃO DE VARIÁVEIS GLOBAIS
# ====================================================================
st.sidebar.markdown("### 👤 Sessão Ativa")
st.sidebar.success(f"**{st.session_state['nome_logado']}**\n\nNível: {st.session_state['perfil_logado']}")
if usa_nuvem: st.sidebar.caption("🟢 Conectado ao Banco em Nuvem")
else: st.sidebar.caption("🔴 Banco em Nuvem Offline")

if st.sidebar.button("🚪 Sair do Sistema"):
    st.session_state.clear()
    st.rerun()

is_admin = (st.session_state['perfil_logado'] == "Administrador")

df_etapas_lidas = pd.read_csv(DB_ETAPAS, sep=";", dtype=str)
LISTA_ETAPAS = df_etapas_lidas['Nome_Etapa'].tolist() if not df_etapas_lidas.empty else ["Avaliação Padrão"]

st.title("🖨️ Sistema SAMAR - Operação em Nuvem")

modelos_disponiveis = list(TIPOS_PROVA.keys())
idx_padrao = next((i for i, m in enumerate(modelos_disponiveis) if "18" in m), 0)
modelo = st.selectbox("Modelo da Prova / Gabarito:", modelos_disponiveis, index=idx_padrao)
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
    tabs = st.tabs(["1. Gerador", "2. Leitor Robô", "3. Cartão Digital", "4. Controle Nuvem (Motor)", "5. 👥 Usuários", "6. 📋 Atas", "7. ⚙️ Ciclos Avaliativos"])
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = tabs
else:
    tabs = st.tabs(["📝 Área de Transcrição Digital"])
    tab3 = tabs[0]

# ====================================================================
# ABA 7 (ADMIN): CRIAÇÃO DE ETAPAS AVALIATIVAS
# ====================================================================
if is_admin:
    with tab7:
        st.markdown("### ⚙️ Configuração de Ciclos / Etapas Avaliativas")
        st.info("Defina aqui os períodos avaliativos (Ex: 1º Bimestre, Diagnóstica). Isso organizará todo o banco de dados e os filtros de pesquisa.")
        
        st.dataframe(df_etapas_lidas, use_container_width=True)
        
        c_eta1, c_eta2 = st.columns(2)
        with c_eta1:
            nova_etapa = st.text_input("Criar Nova Etapa de Avaliação:")
            if st.button("➕ Adicionar Etapa", type="primary"):
                if nova_etapa and nova_etapa not in LISTA_ETAPAS:
                    pd.DataFrame([{"Nome_Etapa": nova_etapa}]).to_csv(DB_ETAPAS, mode='a', header=False, index=False, sep=";")
                    st.success("Etapa adicionada com sucesso!")
                    st.rerun()
        with c_eta2:
            etapa_excluir = st.selectbox("Selecione para Excluir:", LISTA_ETAPAS)
            if st.button("🗑️ Remover Etapa"):
                if len(LISTA_ETAPAS) > 1:
                    df_etapas_lidas[df_etapas_lidas['Nome_Etapa'] != etapa_excluir].to_csv(DB_ETAPAS, index=False, sep=";")
                    st.success("Etapa removida!")
                    st.rerun()
                else:
                    st.warning("Você precisa ter pelo menos 1 etapa ativa.")

# ====================================================================
# ABA 4 (ADMIN): TORRE DE CONTROLE NUVEM (COM FILTRO DE ETAPA)
# ====================================================================
if is_admin:
    with tab4:
        st.markdown("### ☁️ Torre de Controle do Supabase")
        st.info("Selecione a **Etapa Avaliativa** e a hierarquia da escola para visualizar ou corrigir as turmas cadastradas pelos digitadores.")

        if usa_nuvem:
            res_nuvem = supabase.table("respostas_geral").select("*").execute()
            if res_nuvem.data:
                df_master = pd.DataFrame(res_nuvem.data)
                colunas_display = ['id', 'etapa', 'escola', 'ano_ensino', 'turma', 'turno', 'frequencia', 'nome_aluno', 'respostas_brutas', 'digitador', 'status']
                for c in colunas_display:
                    if c not in df_master.columns: df_master[c] = "Aberto" if c == 'status' else ("Padrão" if c == 'etapa' else "")
                    
                df_master = df_master[colunas_display]
                df_master.columns = ['ID', 'Etapa', 'Escola', 'Ano_Ensino', 'Turma', 'Turno', 'Frequencia', 'Nome_Aluno', 'Respostas_Brutas', 'Digitador', 'Status']

                with st.container(border=True):
                    st.markdown("#### 🔍 Filtro Hierárquico de Turmas")
                    f_col0, f_col1, f_col2, f_col3 = st.columns(4)
                    
                    etapas_disp = ["Todas as Etapas"] + sorted(list(df_master['Etapa'].dropna().unique()))
                    with f_col0: sel_etapa_admin = st.selectbox("1. Etapa Avaliativa:", etapas_disp)
                    df_f0 = df_master if sel_etapa_admin == "Todas as Etapas" else df_master[df_master['Etapa'] == sel_etapa_admin]
                    
                    anos_disp = ["Todos os Anos"] + sorted(list(df_f0['Ano_Ensino'].dropna().unique()))
                    with f_col1: sel_ano_admin = st.selectbox("2. Ano de Ensino:", anos_disp)
                    df_f1 = df_f0 if sel_ano_admin == "Todos os Anos" else df_f0[df_f0['Ano_Ensino'] == sel_ano_admin]
                    
                    escolas_disp = ["Todas as Escolas"] + sorted(list(df_f1['Escola'].dropna().unique()))
                    with f_col2: sel_esc_admin = st.selectbox("3. Escola:", escolas_disp)
                    df_f2 = df_f1 if sel_esc_admin == "Todas as Escolas" else df_f1[df_f1['Escola'] == sel_esc_admin]
                    
                    if sel_esc_admin != "Todas as Escolas":
                        turmas_disp = ["Todas as Turmas"] + sorted(list(df_f2['Turma'].dropna().unique()))
                        with f_col3: sel_tur_admin = st.selectbox("4. Turma:", turmas_disp)
                        df_f3 = df_f2 if sel_tur_admin == "Todas as Turmas" else df_f2[df_f2['Turma'] == sel_tur_admin]
                    else:
                        df_f3 = df_f2

                # EXIBIÇÃO E EDIÇÃO EM SANFONA
                if sel_esc_admin != "Todas as Escolas":
                    turmas_turnos = df_f3[['Turma', 'Turno', 'Etapa']].drop_duplicates().values.tolist()
                    for (tur, tur_no, eta_b) in turmas_turnos:
                        with st.expander(f"📚 {eta_b} | Turma {tur} ({tur_no})", expanded=False):
                            df_tur = df_f3[(df_f3['Turma'] == tur) & (df_f3['Turno'] == tur_no) & (df_f3['Etapa'] == eta_b)].copy()
                            status_turma = "Bloqueado" if 'Bloqueado' in df_tur['Status'].values else "Aberto"
                            icone_status = "🔒 BLOQUEADA" if status_turma == "Bloqueado" else "🔓 ABERTA"
                            
                            st.markdown(f"**Total de Alunos:** {len(df_tur)} | **Status:** {icone_status}")
                            
                            c_lock1, c_lock2 = st.columns([2, 2])
                            with c_lock1:
                                if status_turma == "Aberto":
                                    if st.button(f"🔒 Bloquear Turma (Impedir Digitadores)", key=f"lk_{eta_b}_{sel_esc_admin}_{tur}_{tur_no}"):
                                        supabase.table("respostas_geral").update({"status": "Bloqueado"}).eq("etapa", eta_b).eq("escola", sel_esc_admin).eq("ano_ensino", sel_ano_admin).eq("turma", tur).eq("turno", tur_no).execute()
                                        st.rerun()
                                else:
                                    if st.button(f"🔓 Desbloquear Turma", key=f"un_{eta_b}_{sel_esc_admin}_{tur}_{tur_no}"):
                                        supabase.table("respostas_geral").update({"status": "Aberto"}).eq("etapa", eta_b).eq("escola", sel_esc_admin).eq("ano_ensino", sel_ano_admin).eq("turma", tur).eq("turno", tur_no).execute()
                                        st.rerun()
                            
                            for q in range(1, total_q_global + 1):
                                df_tur[f"Q{q:02d}"] = df_tur["Respostas_Brutas"].apply(lambda x: x[q-1] if isinstance(x, str) and len(x) >= q else "-")

                            cols_editar = ["ID", "Frequencia", "Nome_Aluno"] + [f"Q{q:02d}" for q in range(1, total_q_global+1)] + ["Digitador", "Status"]
                            config_cols_admin = {"ID": None, "Frequencia": st.column_config.TextColumn(width="small"), "Digitador": st.column_config.TextColumn(disabled=True), "Status": st.column_config.TextColumn(disabled=True)}
                            for q in range(1, total_q_global+1): config_cols_admin[f"Q{q:02d}"] = st.column_config.SelectboxColumn(options=["A", "B", "C", "D", "-", "*"], width="small")

                            key_ed = f"ed_adm_{eta_b}_{sel_esc_admin}_{tur}_{tur_no}"
                            df_ed = st.data_editor(df_tur[cols_editar], column_config=config_cols_admin, use_container_width=True, num_rows="dynamic", key=key_ed)

                            if st.button(f"Salvar Edições da Coordenação", key=f"btn_adm_{eta_b}_{sel_esc_admin}_{tur}_{tur_no}", type="primary"):
                                with st.spinner("Sincronizando..."):
                                    df_salvar = df_ed.copy()
                                    df_salvar["Respostas_Brutas"] = df_salvar[[f"Q{q:02d}" for q in range(1, total_q_global + 1)]].agg(lambda x: ''.join(x.astype(str)), axis=1)
                                    records_upsert = []
                                    for _, row in df_salvar.iterrows():
                                        records_upsert.append({
                                            "id": row["ID"] if pd.notna(row.get("ID")) else str(uuid.uuid4()),
                                            "etapa": eta_b, "escola": sel_esc_admin, "ano_ensino": sel_ano_admin, 
                                            "turma": tur, "turno": tur_no, "frequencia": str(row["Frequencia"]), 
                                            "nome_aluno": str(row["Nome_Aluno"]), "respostas_brutas": str(row["Respostas_Brutas"]), 
                                            "digitador": str(row["Digitador"]) if pd.notna(row.get("Digitador")) else st.session_state['nome_logado'],
                                            "status": str(row["Status"])
                                        })
                                    supabase.table("respostas_geral").upsert(records_upsert).execute()
                                    st.success(f"✅ Atualizado!")
                                    st.rerun()
                else:
                    st.write("⬆️ Para ver e editar os dados, utilize os filtros acima e selecione uma Escola.")

                st.markdown("---")
                st.markdown("#### ⚙️ Motor Gerador de Notas (Exportação Final em ZIP)")
                st.caption(f"Este motor processará **{len(df_f3)} alunos** que você filtrou no quadro acima.")
                gabarito_admin = st.text_input(f"Gabarito Oficial ({total_q_global} questões):", value="A"*total_q_global).upper().strip()
                gab_dict_admin = {}
                if len(gabarito_admin) >= total_q_global:
                    for i, char in enumerate(gabarito_admin[:total_q_global]): gab_dict_admin[i+1] = "NULA" if char in ["X", "N"] else char

                if st.button("🚀 Calcular Notas e Empacotar Planilhas (ZIP)", type="primary", use_container_width=True):
                    with st.spinner("Corrigindo alunos..."):
                        todos_resultados = []
                        if not df_f3.empty:
                            for index, row in df_f3.iterrows():
                                aluno_processado = {
                                    "Etapa": row["Etapa"], "Escola": row["Escola"], "Ano_Ensino": row["Ano_Ensino"], 
                                    "Turma": row["Turma"], "Turno": row["Turno"], 
                                    "Frequencia": row["Frequencia"], "Nome": row["Nome_Aluno"],
                                    "Digitador_Responsavel": row["Digitador"]
                                }
                                acertos_geral = 0
                                acertos_disc = {disc: 0 for disc in tot_disc_global}
                                respostas_brutas = str(row["Respostas_Brutas"])
                                
                                for q in range(1, total_q_global + 1):
                                    letra_marcada = respostas_brutas[q-1] if (q-1 < len(respostas_brutas)) else "-"
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
                            df_final_admin = df_final_admin.sort_values(by=['Etapa', 'Escola', 'Ano_Ensino', 'Turma', 'Turno', 'Ordem_Num'], ascending=[True, True, True, True, True, True], na_position='last').drop(columns=['Ordem_Num']) 
                            
                            zip_csv_buffer = io.BytesIO()
                            with zipfile.ZipFile(zip_csv_buffer, "w") as zf:
                                grouped = df_final_admin.groupby(['Etapa', 'Escola', 'Ano_Ensino', 'Turma', 'Turno'])
                                for name, group_df in grouped:
                                    eta_g, esc_g, ano_g, tur_g, turno_g = name
                                    esc_clean = str(esc_g).replace(' ', '_').replace('/', '-')
                                    eta_clean = str(eta_g).replace(' ', '_')
                                    nome_arquivo_csv = f"Notas_{eta_clean}_{esc_clean}_{ano_g}_{tur_g}_{turno_g}.csv"
                                    zf.writestr(nome_arquivo_csv, group_df.to_csv(index=False, sep=";"))
                                    
                            st.success(f"✅ {len(df_final_admin)} alunos separados e empacotados no ZIP.")
                            st.download_button("📥 Baixar Planilhas Organizadas (ZIP)", data=zip_csv_buffer.getvalue(), file_name=f"SAMAR_Notas_Por_Turma_{datetime.now().strftime('%Y%m%d')}.zip", mime="application/zip", type="primary", use_container_width=True)
            else:
                st.info("A Nuvem está vazia.")

# ====================================================================
# ABA 3 COMPARTILHADA: A MÁGICA DO DIGITADOR (NOVO FLUXO)
# ====================================================================
with tab3:
    nome_operador = st.session_state['nome_logado']
    mapa_valores_global = {"A":"A", "B":"B", "C":"C", "D":"D", "Branco":"-", "Rasura":"*", None: "-"}
    
    # CALLBACK DE INSERÇÃO
    def salvar_aluno_callback():
        nova_freq = st.session_state.freq_d + st.session_state.freq_u
        resp_str = "".join([mapa_valores_global.get(st.session_state.get(f"q_{q}"), "-") for q in range(1, total_q_global + 1)])
        novo_dado = {
            "etapa": st.session_state.config_etapa, "escola": st.session_state.config_escola, 
            "ano_ensino": st.session_state.config_ano, "turma": st.session_state.config_turma, 
            "turno": st.session_state.config_turno, "frequencia": nova_freq, 
            "nome_aluno": st.session_state.nome_aluno_input, "respostas_brutas": resp_str, 
            "digitador": nome_operador, "status": "Aberto"
        }
        if usa_nuvem:
            try: supabase.table("respostas_geral").insert([novo_dado]).execute()
            except Exception as e: print("Erro:", e)
        
        st.session_state.msg_sucesso = f"✅ Aluno {nova_freq} cadastrado com sucesso!"
        st.session_state.nome_aluno_input = ""
        st.session_state.freq_d = "0"
        st.session_state.freq_u = "0"
        for q in range(1, total_q_global + 1): st.session_state[f"q_{q}"] = None

    # INICIALIZADORES VAZIOS
    if "freq_d" not in st.session_state: st.session_state.freq_d = "0"
    if "freq_u" not in st.session_state: st.session_state.freq_u = "0"
    if "nome_aluno_input" not in st.session_state: st.session_state.nome_aluno_input = ""
    for q in range(1, 100): 
        if f"q_{q}" not in st.session_state: st.session_state[f"q_{q}"] = None 

    st.markdown("### 🖱️ Painel de Transcrição OMR")
    
    if "msg_erro" in st.session_state:
        st.error(st.session_state.msg_erro)
        del st.session_state.msg_erro
    if "msg_sucesso" in st.session_state:
        st.success(st.session_state.msg_sucesso)
        del st.session_state.msg_sucesso

    # ====================================================================
    # FASE 1: O DIGITADOR ESCOLHE SE VAI CRIAR OU EDITAR TURMA
    # ====================================================================
    if not st.session_state['turma_confirmada']:
        with st.container(border=True):
            st.markdown("#### Passo 1: Como você deseja iniciar o trabalho?")
            fluxo = st.radio("Selecione a ação:", ["📝 CRIAR Nova Turma (Iniciar Digitação)", "📂 CONTINUAR Turma Existente (Acessar Meu Histórico)"])
            
            st.divider()
            
            if "CRIAR" in fluxo:
                st.markdown("**Defina a nova turma que será criada:**")
                c_etapa, c_escola = st.columns([1, 2])
                with c_etapa: s_etapa = st.selectbox("Etapa Avaliativa:", LISTA_ETAPAS)
                with c_escola: s_escola = st.selectbox("Escola:", ESCOLAS_SAMAR)
                
                c_ano, c_turma, c_turno = st.columns(3)
                with c_ano: s_ano = st.selectbox("Ano de Ensino:", ANOS_ENSINO)
                with c_turma: s_turma = st.selectbox("Turma:", TURMAS_DISP)
                with c_turno: s_turno = st.selectbox("Turno:", TURNOS_DISP)
                
                if st.button("✅ Confirmar Dados e Abrir Cartão", type="primary", use_container_width=True):
                    if not s_escola or not s_ano or not s_turma or not s_turno:
                        st.error("⚠️ Preencha todos os campos obrigatórios da turma!")
                    else:
                        st.session_state.config_etapa = s_etapa
                        st.session_state.config_escola = s_escola
                        st.session_state.config_ano = s_ano
                        st.session_state.config_turma = s_turma
                        st.session_state.config_turno = s_turno
                        st.session_state['turma_confirmada'] = True
                        st.rerun()
            
            else:
                st.markdown("**Buscar no Meu Banco de Dados na Nuvem:**")
                if usa_nuvem:
                    res_historico = supabase.table("respostas_geral").select("etapa, escola, ano_ensino, turma, turno").eq("digitador", nome_operador).execute()
                    if res_historico.data:
                        df_hist = pd.DataFrame(res_historico.data).drop_duplicates()
                        if not df_hist.empty:
                            lista_dropdown = []
                            for _, r in df_hist.iterrows():
                                lista_dropdown.append(f"{r['etapa']} | {r['escola']} | {r['ano_ensino']} - Turma {r['turma']} ({r['turno']})")
                            
                            selecao_historico = st.selectbox("Selecione a turma que deseja continuar editando:", lista_dropdown)
                            
                            if st.button("📂 Puxar Turma da Nuvem", type="primary", use_container_width=True):
                                # Lógica para desmontar a string e jogar na session state
                                partes = selecao_historico.split(" | ")
                                st.session_state.config_etapa = partes[0]
                                st.session_state.config_escola = partes[1]
                                extra = partes[2].split(" - Turma ")
                                st.session_state.config_ano = extra[0]
                                turma_turno = extra[1].split(" (")
                                st.session_state.config_turma = turma_turno[0]
                                st.session_state.config_turno = turma_turno[1].replace(")", "")
                                st.session_state['turma_confirmada'] = True
                                st.rerun()
                        else:
                            st.info("Você não tem nenhuma turma salva na nuvem ainda.")
                    else:
                        st.info("Você não tem nenhuma turma salva na nuvem ainda.")

    # ====================================================================
    # FASE 2: TELA DE DIGITAÇÃO COM O CABEÇALHO TRAVADO
    # ====================================================================
    else:
        st.success(f"📌 **Trabalhando agora em:** {st.session_state.config_etapa} | {st.session_state.config_escola} | {st.session_state.config_ano} - Turma {st.session_state.config_turma} ({st.session_state.config_turno})")
        if st.button("🔄 Fechar esta Turma e Voltar ao Menu Principal"):
            st.session_state['turma_confirmada'] = False
            st.rerun()

        turma_esta_bloqueada = False
        if usa_nuvem:
            res_check_lock = supabase.table("respostas_geral").select("status").eq("etapa", st.session_state.config_etapa).eq("escola", st.session_state.config_escola).eq("ano_ensino", st.session_state.config_ano).eq("turma", st.session_state.config_turma).eq("turno", st.session_state.config_turno).execute()
            if res_check_lock.data and any(r.get('status') == 'Bloqueado' for r in res_check_lock.data):
                turma_esta_bloqueada = True

        if turma_esta_bloqueada:
            st.error("🔒 **TURMA BLOQUEADA PELA COORDENAÇÃO.** As notas desta turma já foram geradas. Você não pode adicionar alunos ou modificar os existentes.")

        with st.container(border=True):
            st.markdown("#### 👤 Inserir Novo Cartão-Resposta")
            st.text_input("Nome do Aluno:", max_chars=100, key="nome_aluno_input", disabled=turma_esta_bloqueada)
            st.divider()
            col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
            with col_f1: st.radio("Dezena (D):", ["0","1","2","3","4","5","6","7","8","9"], horizontal=True, key="freq_d", disabled=turma_esta_bloqueada)
            with col_f2: st.radio("Unidade (U):", ["0","1","2","3","4","5","6","7","8","9"], horizontal=True, key="freq_u", disabled=turma_esta_bloqueada)
            with col_f3:
                cor_num = "#999" if turma_esta_bloqueada else "#0d6efd"
                st.markdown(
                    f"<div style='text-align: center; border: 2px dashed {cor_num}; border-radius: 10px; padding: 10px;'>"
                    f"<p style='margin:0; font-size: 14px; font-weight: bold;'>Número:</p>"
                    f"<h1 style='margin:0; font-size: 3.5rem; color: {cor_num};'>{st.session_state.freq_d}{st.session_state.freq_u}</h1>"
                    f"</div>", unsafe_allow_html=True
                )
            st.divider()
            blocos_prova = [g for g in conf.grids if g.questao_inicial > 0]
            cols_blocos = st.columns(len(blocos_prova)) 
            opcoes_visuais = ["A", "B", "C", "D", "Branco", "Rasura"]
            for i, bloco in enumerate(blocos_prova):
                with cols_blocos[i]:
                    with st.container(border=True):
                        st.markdown(f"**{bloco.titulo}**")
                        for r in range(bloco.rows):
                            q = bloco.questao_inicial + r
                            st.radio(f"Questão {q:02d}", options=opcoes_visuais, index=None, horizontal=True, key=f"q_{q}", disabled=turma_esta_bloqueada)
            st.write("")
            if not turma_esta_bloqueada:
                st.button("Salvar Cartão deste Aluno", type="primary", use_container_width=True, on_click=salvar_aluno_callback)

        st.markdown("---")
        
        # TABELA DE VISUALIZAÇÃO E EDIÇÃO DA TURMA ATUAL
        st.markdown(f"#### 📁 Alunos Registrados nesta Turma")
        if usa_nuvem:
            res_turma = supabase.table("respostas_geral").select("*").eq("etapa", st.session_state.config_etapa).eq("escola", st.session_state.config_escola).eq("ano_ensino", st.session_state.config_ano).eq("turma", st.session_state.config_turma).eq("turno", st.session_state.config_turno).eq("digitador", nome_operador).execute()
            
            if res_turma.data:
                df_turma = pd.DataFrame(res_turma.data)
                df_turma.rename(columns={"id": "ID", "escola": "Escola", "ano_ensino": "Ano_Ensino", "turma": "Turma", "turno": "Turno", "frequencia": "Frequencia", "nome_aluno": "Nome_Aluno", "respostas_brutas": "Respostas_Brutas", "status": "Status"}, inplace=True)
                
                for q in range(1, total_q_global + 1):
                    df_turma[f"Q{q:02d}"] = df_turma["Respostas_Brutas"].apply(lambda x: x[q-1] if isinstance(x, str) and len(x) >= q else "-")
                
                colunas_exibir = ["ID", "Frequencia", "Nome_Aluno"] + [f"Q{q:02d}" for q in range(1, total_q_global + 1)]
                config_colunas = {"ID": None, "Frequencia": st.column_config.TextColumn("Freq.", max_chars=2, width="small")}
                for q in range(1, total_q_global + 1): config_colunas[f"Q{q:02d}"] = st.column_config.SelectboxColumn(f"Q{q:02d}", options=["A", "B", "C", "D", "-", "*"], width="small", required=True)

                if turma_esta_bloqueada:
                    st.caption("🔒 MODO LEITURA: A tabela abaixo está bloqueada para alterações.")
                    st.dataframe(df_turma[colunas_exibir], use_container_width=True, column_config=config_colunas, height=300)
                else:
                    st.caption("Dê dois cliques na célula para corrigir uma letra ou aperte 'Delete' para apagar um aluno duplicado.")
                    df_editado_ui = st.data_editor(df_turma[colunas_exibir], use_container_width=True, num_rows="dynamic", column_config=config_colunas, height=300, key=f"editor_atual_{st.session_state.reset_key}")
                    
                    if st.button("Salvar Edições na Nuvem", type="primary", use_container_width=True):
                        df_salvar = df_editado_ui.copy()
                        df_salvar["Respostas_Brutas"] = df_salvar[[f"Q{q:02d}" for q in range(1, total_q_global + 1)]].agg(lambda x: ''.join(x.astype(str)), axis=1)
                        
                        records_upsert = []
                        for _, row in df_salvar.iterrows():
                            records_upsert.append({
                                "id": str(row["ID"]) if pd.notna(row.get("ID")) else str(uuid.uuid4()),
                                "etapa": st.session_state.config_etapa, "escola": st.session_state.config_escola, 
                                "ano_ensino": st.session_state.config_ano, "turma": st.session_state.config_turma, 
                                "turno": st.session_state.config_turno, "frequencia": str(row["Frequencia"]), 
                                "nome_aluno": str(row["Nome_Aluno"]), "respostas_brutas": str(row["Respostas_Brutas"]), 
                                "digitador": nome_operador, "status": "Aberto"
                            })
                        supabase.table("respostas_geral").delete().eq("etapa", st.session_state.config_etapa).eq("escola", st.session_state.config_escola).eq("ano_ensino", st.session_state.config_ano).eq("turma", st.session_state.config_turma).eq("turno", st.session_state.config_turno).eq("digitador", nome_operador).execute()
                        supabase.table("respostas_geral").upsert(records_upsert).execute()
                        st.success("Tabela sincronizada com sucesso na nuvem!")
                        st.rerun()
            else:
                st.info("Nenhum aluno registrado para esta turma no momento.")

        # ATAS PARA A TURMA ATUAL
        st.markdown("---")
        st.markdown("#### 📋 Registrar Ata de Ocorrência")
        with st.expander("➕ Nova Ocorrência para esta Turma", expanded=False):
            with st.form("form_ata", clear_on_submit=True):
                nome_aplicador = st.text_input("NOME DO APLICADOR:")
                texto_ata = st.text_area("DESCRIÇÃO DA OCORRÊNCIA:", height=100)
                data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")
                if st.form_submit_button("Enviar Ata para a Coordenação", type="primary"):
                    if not nome_aplicador or not texto_ata:
                        st.error("⚠️ Preencha o nome do Aplicador e a Ocorrência.")
                    else:
                        nova_ata = {
                            "etapa": st.session_state.config_etapa, "data_registro": data_atual, 
                            "escola": st.session_state.config_escola, "ano_ensino": st.session_state.config_ano, 
                            "turma": st.session_state.config_turma, "turno": st.session_state.config_turno, 
                            "aplicador": nome_aplicador, "revisor_digitador": nome_operador, "ocorrencia": texto_ata
                        }
                        if usa_nuvem:
                            try: supabase.table("atas_ocorrencias").insert(nova_ata).execute()
                            except: pass
                        html_doc = gerar_html_ata(st.session_state.config_etapa, st.session_state.config_escola, st.session_state.config_ano, st.session_state.config_turma, st.session_state.config_turno, nome_aplicador, texto_ata, nome_operador, data_atual)
                        st.session_state['ultima_ata_html'] = html_doc
                        st.success("✅ Ata enviada com sucesso!")
            if st.session_state.get('ultima_ata_html'):
                st.download_button("🖨️ Baixar Via da Ata (HTML)", data=st.session_state['ultima_ata_html'], file_name="Ata.html", mime="text/html")
