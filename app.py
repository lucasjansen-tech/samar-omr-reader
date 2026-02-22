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
import unicodedata
import re
from datetime import datetime

# ====================================================================
# CLASSES E FUNÇÕES DE APOIO
# ====================================================================
class MockUpload:
    def __init__(self, filepath):
        self.name = os.path.basename(filepath)
        with open(filepath, "rb") as f: self.bytes = f.read()
    def read(self): return self.bytes
    def getvalue(self): return self.bytes

def limpar_texto_imagem(txt):
    if not isinstance(txt, str): return ""
    txt = txt.replace('º', 'o').replace('ª', 'a').replace('°', 'o')
    return ''.join(c for c in unicodedata.normalize('NFD', txt) if unicodedata.category(c) != 'Mn')

def get_padrao_por_ano(ano_str):
    a = str(ano_str).lower()
    if any(x in a for x in ['1', '2', '3']): return 18, [("LÍNGUA PORTUGUESA", 9), ("MATEMÁTICA", 9)]
    elif any(x in a for x in ['4', '5', '6']): return 44, [("LÍNGUA PORTUGUESA", 22), ("MATEMÁTICA", 22)]
    elif any(x in a for x in ['7', '8', '9']): return 52, [("LÍNGUA PORTUGUESA", 26), ("MATEMÁTICA", 26)]
    return 18, [("LÍNGUA PORTUGUESA", 9), ("MATEMÁTICA", 9)] 

# ====================================================================
# INJEÇÃO DE DESIGN E CONEXÃO SUPABASE
# ====================================================================
st.set_page_config(layout="wide", page_title="SAMAR GRID PRO")

st.markdown("""
    <style>
    div.stButton > button[kind="primary"] {
        background-color: #0d6efd !important; color: white !important;
        border: 1px solid #0d6efd !important; font-weight: bold !important; border-radius: 6px !important;
    }
    div.stButton > button[kind="primary"]:hover { background-color: #0b5ed7 !important; }
    .stDataFrame { font-size: 14px !important; }
    </style>
""", unsafe_allow_html=True)

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

if not HAS_SUPABASE: st.error("⚠️ A biblioteca supabase não está instalada ou o servidor está offline.")

# ====================================================================
# INICIALIZAÇÃO DE BANCOS DE DADOS LOCAIS 
# ====================================================================
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

DB_ESCOLAS = "escolas_samar.csv"
if not os.path.exists(DB_ESCOLAS):
    escolas_iniciais = [
        "COLÉGIO MILITAR TIRADENTES XII", "UNIDADE ESCOLAR JOSÉ LISBOA", "UNIDADE ESCOLAR MANOEL BATISTA",
        "UNIDADE ESCOLAR NOVA ARAÇAGI", "UNIDADE ESCOLAR SOCORRO MAGALHÃES", "UNIDADE ESCOLAR SÃO JOAQUIM",
        "UNIDADE ESCOLAR VILA NOVA", "UNIDADE ESCOLAR VILA SÃO JOÃO", "UNIDADE INTEGRADA CRIANÇA ESPERANÇA",
        "UNIDADE INTEGRADA HENRIQUE DE LA ROQUE", "UNIDADE INTEGRADA JARBAS PASSARINHO", "UNIDADE INTEGRADA MARCONE CALDAS",
        "UNIDADE INTEGRADA PROFESSORA MARIA ROSA REIS TRINDADE", "UNIDADE INTEGRADA RURAL BOA ESPERANÇA",
        "UNIDADE INTEGRADA SANTO ANTÔNIO", "UNIDADE INTEGRADA SARNEY FILHO"
    ]
    pd.DataFrame([{"Nome_Escola": e} for e in escolas_iniciais]).to_csv(DB_ESCOLAS, index=False, sep=";")

DB_ANOS = "anos_ensino_samar.csv"
if not os.path.exists(DB_ANOS):
    anos_iniciais = ["1º Ano", "2º Ano", "3º Ano", "4º Ano", "5º Ano", "6º Ano", "7º Ano", "8º Ano", "9º Ano"]
    pd.DataFrame([{"Ano_Ensino": a} for a in anos_iniciais]).to_csv(DB_ANOS, index=False, sep=";")

DB_ETAPAS = "etapas_samar.csv"
if not os.path.exists(DB_ETAPAS): 
    pd.DataFrame([{"Nome_Etapa": "Avaliação Diagnóstica", "Data_Abertura": "2020-01-01", "Data_Limite": "2030-12-31"}]).to_csv(DB_ETAPAS, index=False, sep=";")
else:
    df_e = pd.read_csv(DB_ETAPAS, sep=";", dtype=str)
    mudou = False
    if "Data_Limite" not in df_e.columns:
        df_e["Data_Limite"] = "2030-12-31"
        mudou = True
    if "Data_Abertura" not in df_e.columns:
        df_e["Data_Abertura"] = "2020-01-01"
        mudou = True
    if mudou: df_e.to_csv(DB_ETAPAS, index=False, sep=";")

df_esc_lida = pd.read_csv(DB_ESCOLAS, sep=";", dtype=str)
ESCOLAS_SAMAR = [""] + df_esc_lida['Nome_Escola'].dropna().tolist()

df_ano_lida = pd.read_csv(DB_ANOS, sep=";", dtype=str)
ANOS_ENSINO = [""] + df_ano_lida['Ano_Ensino'].dropna().tolist()

TURMAS_DISP = ["", "A", "B", "C", "D", "E", "F", "G", "H", "Única"]
TURNOS_DISP = ["", "Manhã", "Tarde", "Integral", "Noite"]

df_etapas_lidas = pd.read_csv(DB_ETAPAS, sep=";", dtype=str)
hoje = datetime.now().date()
ETAPAS_ATIVAS = []
TODAS_ETAPAS = []
for _, row in df_etapas_lidas.iterrows():
    nome_etapa = str(row.get('Nome_Etapa', '')).strip()
    if not nome_etapa or nome_etapa == 'nan': continue
    TODAS_ETAPAS.append(nome_etapa)
    try:
        dt_abert = datetime.strptime(str(row.get('Data_Abertura', '2020-01-01')).split()[0].replace('/','-'), "%Y-%m-%d").date()
        dt_lim = datetime.strptime(str(row.get('Data_Limite', '2030-12-31')).split()[0].replace('/','-'), "%Y-%m-%d").date()
        if dt_abert <= hoje <= dt_lim: ETAPAS_ATIVAS.append(nome_etapa)
    except: ETAPAS_ATIVAS.append(nome_etapa) 

if not TODAS_ETAPAS: TODAS_ETAPAS = ["Padrão"]
if not ETAPAS_ATIVAS: ETAPAS_ATIVAS = TODAS_ETAPAS 

dict_gabaritos_mestres = {}
if usa_nuvem:
    try:
        res_gabs = supabase.table("gabaritos_oficiais").select("*").execute()
        if res_gabs.data:
            for item in res_gabs.data: dict_gabaritos_mestres[(item['etapa'], item['ano_ensino'])] = str(item['gabarito']).upper().strip()
    except: pass

# --- ESTADOS DA SESSÃO ---
estados_padrao = {
    'usuario_logado': None, 'nome_logado': None, 'perfil_logado': None,
    'turma_confirmada': False, 'config_etapa': "", 'config_escola': "",
    'config_ano': "", 'config_turma': "", 'config_turno': "",
    'msg_sucesso_form': None, 'gerar_zip_digitador': False
}
for key, valor in estados_padrao.items():
    if key not in st.session_state: st.session_state[key] = valor

# ====================================================================
# GERADORES DE ARQUIVOS (PDF COM CABEÇALHO OFICIAL E ALINHAMENTO)
# ====================================================================
def gerar_zip_gabaritos(df, conf_prova, modelo_prova, etapa_nome, ano_nome):
    id_unico = uuid.uuid4().hex
    fn_pdf = f"base_temp_{modelo_prova}_{id_unico}.pdf"
    
    logo_file = MockUpload("Frame 18.png") if os.path.exists("Frame 18.png") else None
    logos_dict = {'esq': None, 'cen': logo_file, 'dir': None}
    titulo_doc = str(etapa_nome).upper() if etapa_nome else conf_prova.titulo_prova
    sub_doc = f"Série/Ano: {ano_nome}" if ano_nome else conf_prova.subtitulo
    
    gerar_pdf(conf_prova, fn_pdf, titulo_doc, sub_doc, logos_dict)
    
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
            
            escola = limpar_texto_imagem(str(row.get("Escola", "")))
            ano = limpar_texto_imagem(str(row.get("Ano_Ensino", "")))
            turma = limpar_texto_imagem(str(row.get("Turma", "")))
            turno = limpar_texto_imagem(str(row.get("Turno", "")))
            nome = limpar_texto_imagem(str(row.get("Nome_Aluno", "")))
            
            freq = str(row.get("Frequencia", "00")).zfill(2)
            respostas = str(row.get("Respostas_Brutas", ""))
            
            cor_caneta = (0, 0, 0)
            fonte = cv2.FONT_HERSHEY_SIMPLEX
            escala = 0.55
            espessura = 2
            h, w = conf_prova.REF_H, conf_prova.REF_W
            
            cv2.putText(img_aluno, escola, (int(w * 0.28), int(h * 0.146)), fonte, escala, cor_caneta, espessura)
            cv2.putText(img_aluno, ano, (int(w * 0.12), int(h * 0.178)), fonte, escala, cor_caneta, espessura)
            cv2.putText(img_aluno, turma, (int(w * 0.42), int(h * 0.178)), fonte, escala, cor_caneta, espessura)
            cv2.putText(img_aluno, turno, (int(w * 0.67), int(h * 0.178)), fonte, escala, cor_caneta, espessura)
            cv2.putText(img_aluno, nome, (int(w * 0.12), int(h * 0.213)), fonte, escala, cor_caneta, espessura)
            cv2.putText(img_aluno, freq, (int(w * 0.89), int(h * 0.213)), fonte, escala, cor_caneta, espessura)
            
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
                        cv2.circle(img_aluno, (cx, cy), raio + 4, cor_caneta, -1) 
            is_success, buffer = cv2.imencode(".jpg", img_aluno)
            if is_success:
                nome_arq = nome.replace(" ", "_") if nome else "Sem_Nome"
                zf.writestr(f"Gabarito_F{freq}_{nome_arq}.jpg", buffer.tobytes())
    return zip_buffer.getvalue()

def gerar_html_ata(etapa, escola, ano, turma, turno, aplicador, ocorrencia, revisor, data):
    logo_html = ""
    if os.path.exists("Frame 18.png"):
        try:
            with open("Frame 18.png", "rb") as img_file:
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
# TELA DE LOGIN E AUTENTICAÇÃO
# ====================================================================
if not st.session_state['usuario_logado']:
    st.title("🖨️ Sistema SAMAR - Acesso Restrito")
    st.info("Insira suas credenciais corporativas para acessar o painel em nuvem.")
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
# BARRA LATERAL E TOPO
# ====================================================================
st.sidebar.markdown("### 👤 Sessão Ativa")
st.sidebar.success(f"**{st.session_state['nome_logado']}**\n\nNível: {st.session_state['perfil_logado']}")
if usa_nuvem: st.sidebar.caption("🟢 Conectado ao Supabase")
else: st.sidebar.caption("🔴 Banco Offline")

if st.sidebar.button("🚪 Sair do Sistema"):
    st.session_state.clear()
    st.rerun()

is_admin = (st.session_state['perfil_logado'] == "Administrador")

st.title("🖨️ Sistema SAMAR - Operação em Nuvem")

modelos_disponiveis = list(TIPOS_PROVA.keys())
idx_padrao = next((i for i, m in enumerate(modelos_disponiveis) if "18" in m), 0)
modelo = st.selectbox("Modelo da Prova / Gabarito:", modelos_disponiveis, index=idx_padrao)
conf = TIPOS_PROVA[modelo]
total_q_global = int(modelo.split('_')[1])

if is_admin:
    tabs = st.tabs(["1. Gerador", "2. Leitor Robô", "3. Cartão Digital", "4. Controle Nuvem", "5. 👥 Usuários", "6. 📋 Atas", "7. ⚙️ Configurações & Ciclos"])
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = tabs
else:
    tabs = st.tabs(["📝 Área de Transcrição Digital"])
    tab3 = tabs[0]

# ====================================================================
# ABA 7 (ADMIN): CONFIGURAÇÕES
# ====================================================================
if is_admin:
    with tab7:
        st.markdown("### ⚙️ Gestão de Ciclos e Gabaritos")
        
        with st.container(border=True):
            st.markdown("#### 📅 1. Definir Ciclos e Prazos de Acesso")
            df_etapas_edit = pd.read_csv(DB_ETAPAS, sep=";", dtype=str)
            df_etapas_edit['Data_Abertura'] = pd.to_datetime(df_etapas_edit['Data_Abertura'], dayfirst=True, errors='coerce').dt.date
            df_etapas_edit['Data_Abertura'] = df_etapas_edit['Data_Abertura'].fillna(datetime(2020, 1, 1).date())
            df_etapas_edit['Data_Limite'] = pd.to_datetime(df_etapas_edit['Data_Limite'], dayfirst=True, errors='coerce').dt.date
            df_etapas_edit['Data_Limite'] = df_etapas_edit['Data_Limite'].fillna(datetime(2030, 12, 31).date())
            
            edited_etapas = st.data_editor(
                df_etapas_edit,
                column_config={"Nome_Etapa": st.column_config.TextColumn("Nome do Ciclo", required=True), "Data_Abertura": st.column_config.DateColumn("Abertura", format="DD/MM/YYYY"), "Data_Limite": st.column_config.DateColumn("Prazo Final", format="DD/MM/YYYY")},
                num_rows="dynamic", use_container_width=True, key="ed_etp"
            )
            if st.button("💾 Salvar Ciclos e Prazos", type="primary"):
                edited_etapas['Data_Abertura'] = edited_etapas['Data_Abertura'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else '2020-01-01')
                edited_etapas['Data_Limite'] = edited_etapas['Data_Limite'].apply(lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else '2030-12-31')
                edited_etapas.to_csv(DB_ETAPAS, index=False, sep=";")
                st.success("Ciclos atualizados!")
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        
        with st.container(border=True):
            st.markdown("#### 🔑 2. Atribuir Gabaritos Mestres por Ciclo")
            
            c_gab1, c_gab2 = st.columns(2)
            with c_gab1: sel_eta_gab = st.selectbox("Selecione o Ciclo:", TODAS_ETAPAS, key="sel_eta_gab")
            with c_gab2: sel_ano_gab = st.selectbox("Selecione o Ano de Ensino Avaliado:", ANOS_ENSINO, key="sel_ano_gab")
            
            if sel_eta_gab and sel_ano_gab:
                gab_existente = dict_gabaritos_mestres.get((sel_eta_gab, sel_ano_gab), "")
                if gab_existente: st.success(f"✅ Já existe um gabarito cadastrado para o **{sel_ano_gab}** na etapa **{sel_eta_gab}**.")
                
                expected_total, blocos_esperados = get_padrao_por_ano(sel_ano_gab)
                st.markdown(f"**Padrão detectado para o {sel_ano_gab}:** {expected_total} questões no total.")
                
                cols_gab_input = st.columns(len(blocos_esperados))
                inputs_gab = []

                for i, (nome_disc, qtd_q) in enumerate(blocos_esperados):
                    with cols_gab_input[i]:
                        val = st.text_area(f"{nome_disc} ({qtd_q} q.):", height=200, key=f"gab_bloco_{i}")
                        inputs_gab.append((nome_disc, qtd_q, val))

                if st.button(f"💾 Salvar Gabarito do {sel_ano_gab}", type="primary", use_container_width=True):
                    gab_str_final = ""
                    erros = []
                    for nome_disc, expected_rows, val in inputs_gab:
                        gab_limpo = re.sub(r'[^A-Z]', '', val.upper())
                        if len(gab_limpo) != expected_rows:
                            erros.append(f"**{nome_disc}:** Esperado {expected_rows} letras, mas você inseriu {len(gab_limpo)}.")
                        gab_str_final += gab_limpo
                    
                    if erros:
                        st.error("⚠️ **Erro de Preenchimento detectado:**\n\n" + "\n".join([f"- {e}" for e in erros]))
                    else:
                        if usa_nuvem:
                            records_gab = [{"id": str(uuid.uuid4()), "etapa": sel_eta_gab, "ano_ensino": sel_ano_gab, "gabarito": gab_str_final}]
                            supabase.table("gabaritos_oficiais").delete().eq("etapa", sel_eta_gab).eq("ano_ensino", sel_ano_gab).execute() 
                            supabase.table("gabaritos_oficiais").insert(records_gab).execute()
                            st.success(f"✅ Gabarito Mestre do {sel_ano_gab} salvo com sucesso!")
                            st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        c_cfg2, c_cfg3 = st.columns(2)
        with c_cfg2:
            st.markdown("#### 🏫 3. Escolas da Rede")
            df_esc_edit = pd.read_csv(DB_ESCOLAS, sep=";", dtype=str)
            edited_escolas = st.data_editor(df_esc_edit, num_rows="dynamic", use_container_width=True, key="ed_esc")
            if st.button("💾 Salvar Escolas", type="primary"):
                edited_escolas.to_csv(DB_ESCOLAS, index=False, sep=";")
                st.rerun()
        with c_cfg3:
            st.markdown("#### 🎓 4. Anos de Ensino")
            df_ano_edit = pd.read_csv(DB_ANOS, sep=";", dtype=str)
            edited_anos = st.data_editor(df_ano_edit, num_rows="dynamic", use_container_width=True, key="ed_ano")
            if st.button("💾 Salvar Anos", type="primary"):
                edited_anos.to_csv(DB_ANOS, index=False, sep=";")
                st.rerun()

# ====================================================================
# ABA 1: GERADOR DE PDF
# ====================================================================
if is_admin:
    with tab1:
        st.markdown("### 🎨 Personalização do Cabeçalho e Arquivo")
        col_t1, col_t2 = st.columns(2)
        with col_t1: custom_titulo = st.text_input("Título da Avaliação:", conf.titulo_prova)
        with col_t2: custom_sub = st.text_input("Etapa/Ano (Subtítulo):", conf.subtitulo)
        col_ref1, col_ref2 = st.columns(2)
        with col_ref1: sel_etapa_gerador = st.selectbox("Referência para salvar o arquivo (Etapa):", TODAS_ETAPAS, key="ger_etapa")
        with col_ref2: sel_escola_gerador = st.selectbox("Referência para salvar o arquivo (Escola):", ESCOLAS_SAMAR, key="ger_escola")
        col_l1, col_l2, col_l3 = st.columns(3)
        with col_l1: logo_esq = st.file_uploader("Logo Esquerda", type=["png", "jpg"])
        with col_l2: logo_cen = st.file_uploader("Logo Centro", type=["png", "jpg"])
        with col_l3: logo_dir = st.file_uploader("Logo Direita", type=["png", "jpg"])
        col_fmt1, col_fmt2 = st.columns(2)
        with col_fmt1: fmt = st.radio("Formato de Saída:", ["PDF", "PNG", "JPEG"], horizontal=True)
        with col_fmt2:
            st.write("")
            if st.button("Gerar Arquivo Pronto para Impressão", type="primary", use_container_width=True):
                if logo_cen is None and os.path.exists("Frame 18.png"): logo_cen = MockUpload("Frame 18.png")
                    
                logos_dict = {'esq': logo_esq, 'cen': logo_cen, 'dir': logo_dir}
                titulo_final = custom_titulo if custom_titulo else sel_etapa_gerador.upper()
                
                ext = fmt.split()[0].lower()
                eta_cln = str(sel_etapa_gerador).replace(" ", "_") if sel_etapa_gerador else "Geral"
                esc_cln = str(sel_escola_gerador).replace(" ", "_") if sel_escola_gerador else "S-Escola"
                fn = f"Gabaritos_{eta_cln}_{esc_cln}_{modelo}.{ext}"
                
                if ext == "pdf": gerar_pdf(conf, fn, titulo_final, custom_sub, logos_dict)
                else: gerar_imagem_a4(conf, fn, ext, titulo_final, custom_sub, logos_dict)
                
                if os.path.exists(fn):
                    with open(fn, "rb") as f: st.download_button(f"📥 Baixar {fn}", f, fn, mime="application/octet-stream", use_container_width=True)

# ====================================================================
# ABA 2: LEITOR ROBÔ (COM BLOQUEIO DE DUPLICIDADE)
# ====================================================================
if is_admin:
    with tab2:
        st.markdown("### 📝 Passo 1: Informar o Contexto do Lote")
        with st.container(border=True):
            c_l1, c_l2 = st.columns([1, 2])
            with c_l1: etapa_leitor = st.selectbox("Etapa Avaliativa (Leitor):", TODAS_ETAPAS, key="leitor_etapa")
            with c_l2: escola_leitor = st.selectbox("Escola (Leitor):", ESCOLAS_SAMAR, key="leitor_escola")
            c_l3, c_l4, c_l5 = st.columns(3)
            with c_l3: ano_leitor = st.selectbox("Ano de Ensino:", ANOS_ENSINO, key="leitor_ano")
            with c_l4: turma_leitor = st.selectbox("Turma:", TURMAS_DISP, key="leitor_turma")
            with c_l5: turno_leitor = st.selectbox("Turno:", TURNOS_DISP, key="leitor_turno")

        st.markdown("---")
        
        if not ano_leitor:
            st.info("⚠️ Selecione o 'Ano de Ensino' acima para carregar o padrão de correção correto.")
        else:
            expected_total_leitor, blocos_esperados_leitor = get_padrao_por_ano(ano_leitor)
            
            if total_q_global != expected_total_leitor:
                st.error(f"❌ CONFLITO DE PADRÃO: O **{ano_leitor}** exige um gabarito de {expected_total_leitor} questões, mas o 'Modelo da Prova' selecionado lá no topo da página tem {total_q_global}. Mude o Modelo de Prova no topo e tente novamente.")
            else:
                gab_mestre_detectado = dict_gabaritos_mestres.get((etapa_leitor, ano_leitor), "")
                gab_oficial = {}
                
                if gab_mestre_detectado:
                    st.success(f"✅ **Gabarito Mestre Detectado Automaticamente:** O sistema usará as respostas do {ano_leitor}.")
                    for i, char in enumerate(gab_mestre_detectado[:expected_total_leitor]): 
                        gab_oficial[i+1] = "NULA" if char in ["X", "N"] else char
                else:
                    st.warning(f"⚠️ O {ano_leitor} requer {expected_total_leitor} questões. Insira temporariamente para ler as provas.")
                    modo_gab = st.radio("Como deseja inserir o gabarito temporário?", ["Colar por Disciplina (Modo Matriz)", "Preenchimento Manual Unitário"], horizontal=True)
                    
                    if "Modo Matriz" in modo_gab:
                        cols_gb = st.columns(len(blocos_esperados_leitor))
                        gab_parts = []
                        for i, (nome_disc, qtd_q) in enumerate(blocos_esperados_leitor):
                            with cols_gb[i]:
                                val = st.text_area(f"{nome_disc} ({qtd_q} q.):", height=150, key=f"gab_r_{i}")
                                gab_parts.append((nome_disc, qtd_q, val))
                        
                        gab_temp_str = ""
                        erros_leitor = []
                        for nome_disc, expected_rows, val in gab_parts:
                            gab_limpo = re.sub(r'[^A-Z]', '', val.upper())
                            if val.strip() and len(gab_limpo) != expected_rows:
                                erros_leitor.append(f"**{nome_disc}** (Lidas {len(gab_limpo)}, precisa de {expected_rows})")
                            gab_temp_str += gab_limpo
                        
                        if erros_leitor:
                            st.error("⚠️ Verifique as quantidades:\n" + "\n".join([f"- {e}" for e in erros_leitor]))
                        elif len(gab_temp_str) == expected_total_leitor:
                            for i, char in enumerate(gab_temp_str): gab_oficial[i+1] = "NULA" if char in ["X", "N"] else char
                    else:
                        cols = st.columns(len(blocos_esperados_leitor))
                        q_num_manual = 1
                        for bloco_idx, (nome_disc, qtd_q) in enumerate(blocos_esperados_leitor):
                            with cols[bloco_idx]:
                                st.markdown(f"**{nome_disc}**")
                                for _ in range(qtd_q):
                                    gab_oficial[q_num_manual] = st.selectbox(f"Q.{q_num_manual:02d}", ["A", "B", "C", "D", "NULA"], key=f"q_t2_{q_num_manual}")
                                    q_num_manual += 1
                
                if gab_oficial:
                    st.markdown("---")
                    st.markdown("### 📸 Passo 2: Subir as Imagens/Provas Scaneadas")
                    up = st.file_uploader("Upload das Imagens/PDF do lote selecionado acima:", type=["pdf", "png", "jpg"], accept_multiple_files=True)
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
                                    
                                    aluno_dados = {"Etapa": etapa_leitor, "Escola": escola_leitor, "Ano_Ensino": ano_leitor, "Turma": turma_leitor, "Turno": turno_leitor, "Frequencia": freq}
                                    
                                    acertos_disciplina = {n_d: 0 for n_d, _ in blocos_esperados_leitor}
                                    mapa_disc_aluno = {}
                                    q_curr = 1
                                    for n_d, q_d in blocos_esperados_leitor:
                                        for _ in range(q_d):
                                            mapa_disc_aluno[q_curr] = n_d
                                            q_curr += 1
                                            
                                    for q_num in range(1, expected_total_leitor + 1):
                                        resp_str = res["respostas"].get(q_num, ".")
                                        aluno_dados[f"Letra_Q{q_num:02d}"] = "Múltiplas" if resp_str == "*" else resp_str
                                        is_correct = 1 if "Correto" in res.get("correcao_detalhada", {}).get(q_num, {}).get("Status", "") else 0
                                        aluno_dados[f"Q{q_num:02d}"] = is_correct
                                        if mapa_disc_aluno.get(q_num) and is_correct: acertos_disciplina[mapa_disc_aluno[q_num]] += 1
                                    aluno_dados["Total_Acertos_Geral"] = acertos
                                    for n_d, _ in blocos_esperados_leitor: aluno_dados[f"Acertos_{n_d.replace(' ', '_')}"] = acertos_disciplina[n_d]
                                    resultados_lote.append(aluno_dados)
                            except Exception as e: st.error(f"Erro no arquivo {arquivo.name}")
                        
                        if resultados_lote:
                            # BLOQUEIO DE FREQUÊNCIA DUPLICADA NO LEITOR
                            freqs_lidas = [r["Frequencia"] for r in resultados_lote]
                            freqs_dup = set([x for x in freqs_lidas if freqs_lidas.count(x) > 1])
                            
                            if freqs_dup:
                                st.error(f"🚨 ATENÇÃO: Foram encontradas imagens de provas com a mesma Frequência ({', '.join(freqs_dup)}). Verifique o lote lido antes de subir os dados para o sistema, para evitar conflitos na Turma.")
                            
                            df_export = pd.DataFrame(resultados_lote)
                            st.download_button("📥 Baixar CSV Corrigido", df_export.to_csv(index=False, sep=";"), f"Resultados_Robo_{ano_leitor}_{turma_leitor}.csv", "text/csv", type="primary")

# ====================================================================
# ABA 4 (ADMIN): TORRE DE CONTROLE E FILTROS LIVRES
# ====================================================================
if is_admin:
    with tab4:
        st.markdown("### ☁️ Torre de Controle do Supabase")
        st.info("Abaixo você tem a visão Raio-X de toda a Secretaria de Educação. Use os filtros para cruzar dados livremente e gerar relatórios.")

        if usa_nuvem:
            res_nuvem = supabase.table("respostas_geral").select("*").execute()
            if res_nuvem.data:
                df_master = pd.DataFrame(res_nuvem.data)
                colunas_display = ['id', 'etapa', 'escola', 'ano_ensino', 'turma', 'turno', 'frequencia', 'nome_aluno', 'respostas_brutas', 'digitador', 'status']
                for c in colunas_display:
                    if c not in df_master.columns: df_master[c] = "Aberto" if c == 'status' else ("Padrão" if c == 'etapa' else "")
                    
                df_master = df_master[colunas_display]
                df_master.columns = ['ID', 'Etapa', 'Escola', 'Ano_Ensino', 'Turma', 'Turno', 'Frequencia', 'Nome_Aluno', 'Respostas_Brutas', 'Digitador', 'Status']

                df_final_filtro = df_master.copy()
                
                with st.container(border=True):
                    st.markdown("#### 🔍 Filtro Hierárquico Livre")
                    f_col0, f_col1, f_col2, f_col3 = st.columns(4)
                    
                    with f_col0:
                        etapas_disp = ["Todas as Etapas"] + sorted(list(df_final_filtro['Etapa'].dropna().unique()))
                        sel_etapa_admin = st.selectbox("1. Selecione a Etapa:", etapas_disp)
                        if sel_etapa_admin != "Todas as Etapas":
                            df_final_filtro = df_final_filtro[df_final_filtro['Etapa'] == sel_etapa_admin]
                    
                    with f_col1:
                        anos_disp = ["Todos os Anos"] + sorted(list(df_final_filtro['Ano_Ensino'].dropna().unique()))
                        sel_ano_admin = st.selectbox("2. Selecione o Ano:", anos_disp)
                        if sel_ano_admin != "Todos os Anos":
                            df_final_filtro = df_final_filtro[df_final_filtro['Ano_Ensino'] == sel_ano_admin]

                    with f_col2:
                        escolas_disp = ["Todas as Escolas"] + sorted(list(df_final_filtro['Escola'].dropna().unique()))
                        sel_esc_admin = st.selectbox("3. Selecione a Escola:", escolas_disp)
                        if sel_esc_admin != "Todas as Escolas":
                            df_final_filtro = df_final_filtro[df_final_filtro['Escola'] == sel_esc_admin]

                    with f_col3:
                        turmas_disp = ["Todas as Turmas"] + sorted(list(df_final_filtro['Turma'].dropna().unique()))
                        sel_tur_admin = st.selectbox("4. Selecione a Turma:", turmas_disp)
                        if sel_tur_admin != "Todas as Turmas":
                            df_final_filtro = df_final_filtro[df_final_filtro['Turma'] == sel_tur_admin]

                # MOSTRA AS TABELAS ENCONTRADAS NO FILTRO
                if not df_final_filtro.empty:
                    turmas_turnos = df_final_filtro[['Escola', 'Etapa', 'Ano_Ensino', 'Turma', 'Turno']].drop_duplicates().values.tolist()
                    turmas_turnos.sort(key=lambda x: (x[2], x[0], x[3])) # Organiza Ano > Escola > Turma
                    
                    for (esc, eta_b, ano_b, tur, tur_no) in turmas_turnos:
                        with st.expander(f"🏫 {esc} | 📚 {eta_b} | {ano_b} | Turma {tur} ({tur_no})", expanded=False):
                            df_tur = df_final_filtro[(df_final_filtro['Escola'] == esc) & (df_final_filtro['Turma'] == tur) & (df_final_filtro['Turno'] == tur_no) & (df_final_filtro['Etapa'] == eta_b) & (df_final_filtro['Ano_Ensino'] == ano_b)].copy()
                            
                            status_turma = "Bloqueado" if 'Bloqueado' in df_tur['Status'].values else "Aberto"
                            icone_status = "🔒 BLOQUEADA" if status_turma == "Bloqueado" else "🔓 ABERTA"
                            st.markdown(f"**Total de Alunos:** {len(df_tur)} | **Status:** {icone_status}")
                            
                            c_lock1, c_lock2, c_lock3 = st.columns([1.5, 1.5, 2])
                            with c_lock1:
                                if status_turma == "Aberto":
                                    if st.button(f"🔒 Bloquear Turma", key=f"lk_{eta_b}_{esc}_{ano_b}_{tur}_{tur_no}"):
                                        supabase.table("respostas_geral").update({"status": "Bloqueado"}).eq("etapa", eta_b).eq("escola", esc).eq("ano_ensino", ano_b).eq("turma", tur).eq("turno", tur_no).execute()
                                        st.rerun()
                                else:
                                    if st.button(f"🔓 Desbloquear Turma", key=f"un_{eta_b}_{esc}_{ano_b}_{tur}_{tur_no}"):
                                        supabase.table("respostas_geral").update({"status": "Aberto"}).eq("etapa", eta_b).eq("escola", esc).eq("ano_ensino", ano_b).eq("turma", tur).eq("turno", tur_no).execute()
                                        st.rerun()
                            
                            with c_lock3:
                                if st.button(f"🖼️ Baixar Gabaritos em PDF/JPG", key=f"zip_{eta_b}_{esc}_{ano_b}_{tur}_{tur_no}"):
                                    with st.spinner("Desenhando gabaritos..."):
                                        zip_adm = gerar_zip_gabaritos(df_tur, conf, modelo, eta_b, ano_b)
                                        st.download_button("📥 Clique aqui para salvar", zip_adm, f"Gabaritos_{esc}_{ano_b}_{tur}.zip", "application/zip", type="primary", key=f"d_zip_{eta_b}_{esc}_{ano_b}_{tur}")

                            q_esperadas, _ = get_padrao_por_ano(ano_b)
                            
                            # CORTA A TABELA PARA MOSTRAR SÓ AS QUESTÕES DO ANO ESPECÍFICO
                            for q in range(1, q_esperadas + 1):
                                df_tur[f"Q{q:02d}"] = df_tur["Respostas_Brutas"].apply(lambda x: x[q-1] if isinstance(x, str) and len(x) >= q else "-")

                            cols_editar = ["ID", "Frequencia", "Nome_Aluno"] + [f"Q{q:02d}" for q in range(1, q_esperadas+1)] + ["Digitador", "Status"]
                            config_cols_admin = {"ID": None, "Frequencia": st.column_config.TextColumn(width="small"), "Digitador": st.column_config.TextColumn(disabled=True), "Status": st.column_config.TextColumn(disabled=True)}
                            # NOVAS OPÇÕES INCLUÍDAS NA TABELA DO ADMIN
                            for q in range(1, q_esperadas+1): config_cols_admin[f"Q{q:02d}"] = st.column_config.SelectboxColumn(options=["A", "B", "C", "D", "-", "*", "R"], width="small")

                            key_ed = f"ed_adm_{eta_b}_{esc}_{ano_b}_{tur}_{tur_no}"
                            df_ed = st.data_editor(df_tur[cols_editar], column_config=config_cols_admin, use_container_width=True, num_rows="dynamic", key=key_ed)

                            if st.button(f"💾 Salvar Edições da Coordenação", key=f"btn_adm_{eta_b}_{esc}_{ano_b}_{tur}_{tur_no}", type="primary"):
                                with st.spinner("Sincronizando..."):
                                    df_salvar = df_ed.copy()
                                    df_salvar["Respostas_Brutas"] = df_salvar[[f"Q{q:02d}" for q in range(1, q_esperadas + 1)]].agg(lambda x: ''.join(x.astype(str)), axis=1)
                                    records_upsert = []
                                    for _, row in df_salvar.iterrows():
                                        records_upsert.append({
                                            "id": row["ID"] if pd.notna(row.get("ID")) else str(uuid.uuid4()),
                                            "etapa": eta_b, "escola": esc, "ano_ensino": ano_b, 
                                            "turma": tur, "turno": tur_no, "frequencia": str(row["Frequencia"]), 
                                            "nome_aluno": str(row["Nome_Aluno"]), "respostas_brutas": str(row["Respostas_Brutas"]), 
                                            "digitador": str(row["Digitador"]) if pd.notna(row.get("Digitador")) else st.session_state['nome_logado'],
                                            "status": str(row["Status"])
                                        })
                                    supabase.table("respostas_geral").upsert(records_upsert).execute()
                                    st.success(f"✅ Atualizado!")
                                    st.rerun()
                                    
                            st.write("")
                            with st.expander("🚨 ZONA DE PERIGO: Excluir Turma", expanded=False):
                                if st.button(f"🗑️ Excluir Turma {tur} Permanentemente", key=f"del_{eta_b}_{esc}_{ano_b}_{tur}_{tur_no}"):
                                    supabase.table("respostas_geral").delete().eq("etapa", eta_b).eq("escola", esc).eq("ano_ensino", ano_b).eq("turma", tur).eq("turno", tur_no).execute()
                                    st.success("A turma foi apagada da nuvem instantaneamente.")
                                    st.rerun()
                else:
                    st.info("⬆️ A base de dados não encontrou nenhum aluno para o filtro selecionado.")

                st.markdown("---")
                st.markdown("#### ⚙️ Motor Inteligente de Notas & Exportação Global")
                
                c_mot1, c_mot2 = st.columns(2)
                with c_mot1:
                    st.download_button("📊 Exportar Tabela Bruta (Apenas os Dados CSV do Filtro)", df_final_filtro.to_csv(index=False, sep=";"), f"Dados_Brutos_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", use_container_width=True)
                
                with c_mot2:
                    if st.button("🚀 Calcular Notas e Empacotar Pastas (ZIP)", type="primary", use_container_width=True):
                        with st.spinner("Buscando gabaritos mestres e corrigindo alunos..."):
                            todos_resultados = []
                            if not df_final_filtro.empty:
                                for index, row in df_final_filtro.iterrows():
                                    eta_aluno = row["Etapa"]
                                    ano_aluno = row["Ano_Ensino"]
                                    gabarito_str = dict_gabaritos_mestres.get((eta_aluno, ano_aluno), "")
                                    if not gabarito_str: continue 
                                    
                                    total_q_aluno, blocos_aluno = get_padrao_por_ano(ano_aluno)
                                    mapa_disc_aluno = {}
                                    tot_disc_aluno = {}
                                    q_curr = 1
                                    for n_disc, q_disc in blocos_aluno:
                                        tot_disc_aluno[n_disc] = q_disc
                                        for _ in range(q_disc):
                                            mapa_disc_aluno[q_curr] = n_disc
                                            q_curr += 1
                                    
                                    gab_dict_admin = {i+1: ("NULA" if char in ["X", "N"] else char) for i, char in enumerate(gabarito_str[:total_q_aluno])}

                                    aluno_processado = {
                                        "Etapa": eta_aluno, "Escola": row["Escola"], "Ano_Ensino": ano_aluno, 
                                        "Turma": row["Turma"], "Turno": row["Turno"], 
                                        "Frequencia": row["Frequencia"], "Nome": row["Nome_Aluno"],
                                        "Digitador_Responsavel": row["Digitador"]
                                    }
                                    acertos_geral = 0
                                    acertos_disc = {disc: 0 for disc in tot_disc_aluno}
                                    respostas_brutas = str(row["Respostas_Brutas"])
                                    
                                    for q in range(1, total_q_aluno + 1):
                                        letra_marcada = respostas_brutas[q-1] if (q-1 < len(respostas_brutas)) else "-"
                                        gabarito_certo = gab_dict_admin.get(q, "NULA")
                                        aluno_processado[f"Letra_Q{q:02d}"] = letra_marcada
                                        is_correct = 1 if gabarito_certo == "NULA" or letra_marcada == gabarito_certo else 0
                                        if is_correct:
                                            acertos_geral += 1
                                            if mapa_disc_aluno.get(q): acertos_disc[mapa_disc_aluno[q]] += 1
                                        aluno_processado[f"Q{q:02d}"] = is_correct
                                    
                                    aluno_processado["Total_Acertos_Geral"] = acertos_geral
                                    aluno_processado["%_Acerto_Geral"] = round((acertos_geral / total_q_aluno) * 100, 2) if total_q_aluno > 0 else 0
                                    for disc, total in tot_disc_aluno.items():
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
                                        eta_clean = str(eta_g).replace(' ', '_').replace('/', '-')
                                        ano_clean = str(ano_g).replace(' ', '_').replace('/', '-')
                                        tur_clean = str(tur_g).replace(' ', '_')
                                        turno_clean = str(turno_g).replace(' ', '_')
                                        
                                        nome_arquivo_csv = f"{eta_clean}/{esc_clean}/{ano_clean}/Turma_{tur_clean}_{turno_clean}.csv"
                                        zf.writestr(nome_arquivo_csv, group_df.to_csv(index=False, sep=";"))
                                        
                                st.success(f"✅ {len(df_final_admin)} alunos avaliados foram separados em pastas e empacotados!")
                                st.download_button("📥 Baixar Arquivo ZIP Estruturado", data=zip_csv_buffer.getvalue(), file_name=f"Resultados_SAMAR_{datetime.now().strftime('%Y%m%d')}.zip", mime="application/zip", type="primary", use_container_width=True)
                            else:
                                st.warning("⚠️ O motor não corrigiu nenhum aluno. Verifique se as turmas selecionadas possuem Gabarito Mestre cadastrado na Aba 7.")
            else:
                st.info("A Nuvem está vazia.")

# ====================================================================
# ABA 5 E 6: GESTÃO DE USUÁRIOS E ATAS
# ====================================================================
if is_admin:
    with tab5:
        st.markdown("### 👥 Controle de Usuários")
        df_usuarios = pd.read_csv(DB_USUARIOS, sep=";", dtype=str)
        st.dataframe(df_usuarios[["Nome", "Email", "Perfil"]], use_container_width=True)
        col_add, col_edit = st.columns(2)
        with col_add:
            with st.container(border=True):
                st.markdown("#### ➕ Criar Novo Usuário")
                with st.form("form_add_user", clear_on_submit=True):
                    novo_nome = st.text_input("Nome:")
                    novo_email = st.text_input("Login:")
                    nova_senha = st.text_input("Senha:", type="password")
                    novo_perfil = st.selectbox("Perfil:", ["Digitador", "Administrador"])
                    if st.form_submit_button("Cadastrar Usuário", type="primary", use_container_width=True):
                        if novo_nome and novo_email and nova_senha:
                            if novo_email in df_usuarios['Email'].values: st.error("Email já cadastrado!")
                            else:
                                pd.DataFrame([{"Nome": novo_nome, "Email": novo_email, "Senha": hash_senha(nova_senha), "Perfil": novo_perfil}]).to_csv(DB_USUARIOS, mode='a', header=False, index=False, sep=";")
                                st.rerun()
        with col_edit:
            with st.container(border=True):
                st.markdown("#### ✏️ Editar")
                if not df_usuarios.empty:
                    user_to_edit = st.selectbox("Usuário:", df_usuarios['Email'].tolist())
                    nova_senha_edit = st.text_input("Nova Senha:", type="password")
                    if st.button("Salvar Nova Senha", type="primary", use_container_width=True):
                        df_usuarios.loc[df_usuarios['Email'] == user_to_edit, 'Senha'] = hash_senha(nova_senha_edit)
                        df_usuarios.to_csv(DB_USUARIOS, index=False, sep=";")
                        st.rerun()
            
            with st.container(border=True):
                st.markdown("#### 🚨 Excluir Usuário")
                if not df_usuarios.empty:
                    user_to_del = st.selectbox("Selecione o Usuário para remover:", df_usuarios['Email'].tolist(), key="sel_del_user")
                    st.warning("⚠️ Esta ação apagará permanentemente o acesso deste usuário.")
                    if st.button(f"🗑️ Confirmar Exclusão", use_container_width=True):
                        if user_to_del == "admin":
                            st.error("Não é possível excluir o Administrador Master do sistema.")
                        else:
                            df_usuarios = df_usuarios[df_usuarios['Email'] != user_to_del]
                            df_usuarios.to_csv(DB_USUARIOS, index=False, sep=";")
                            st.success(f"Acesso de {user_to_del} revogado!")
                            st.rerun()

    with tab6:
        st.markdown("### 📋 Livro Oficial de Atas")
        if usa_nuvem:
            res_atas = supabase.table("atas_ocorrencias").select("*").execute()
            if res_atas.data:
                df_atas = pd.DataFrame(res_atas.data)
                df_atas.rename(columns={"etapa": "Etapa", "data_registro":"Data_Registro", "escola":"Escola", "ano_ensino":"Ano_Ensino", "turma":"Turma", "turno":"Turno", "aplicador":"Aplicador", "revisor_digitador":"Revisor_Digitador", "ocorrencia":"Ocorrencia"}, inplace=True)
                df_atas_editado = st.data_editor(df_atas, use_container_width=True, num_rows="dynamic", key="editor_admin_atas", height=300)
                
                col_save_atas, c1, c2 = st.columns([1.5, 1, 1])
                with col_save_atas:
                    if st.button("Salvar Edições de Atas na Nuvem", use_container_width=True, type="primary"):
                        records_ata = []
                        for _, row in df_atas_editado.iterrows():
                            records_ata.append({
                                "id": row.get("id", str(uuid.uuid4())), "etapa": str(row.get("Etapa", "Padrão")),
                                "data_registro": str(row["Data_Registro"]), "escola": str(row["Escola"]),
                                "ano_ensino": str(row["Ano_Ensino"]), "turma": str(row["Turma"]),
                                "turno": str(row["Turno"]), "aplicador": str(row["Aplicador"]),
                                "revisor_digitador": str(row["Revisor_Digitador"]), "ocorrencia": str(row["Ocorrencia"])
                            })
                        supabase.table("atas_ocorrencias").upsert(records_ata).execute()
                        st.success("Banco de Atas atualizado na Nuvem!")
                        st.rerun()
                with c1: st.download_button("📊 Exportar Planilha (CSV)", df_atas_editado.to_csv(index=False, sep=";"), f"atas_samar_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", use_container_width=True)
                with c2: st.download_button("🖨️ Baixar Documentos HTML (ZIP)", gerar_zip_atas(df_atas_editado), f"Documentos_Atas_{datetime.now().strftime('%Y%m%d')}.zip", "application/zip", use_container_width=True)
            else: st.success("Nenhuma ocorrência na nuvem.")

# ====================================================================
# ABA 3 COMPARTILHADA: A MÁGICA DO DIGITADOR (COM FORMULÁRIO ESTÁTICO)
# ====================================================================
with tab3:
    nome_operador = st.session_state['nome_logado']
    
    # NOVAS OPÇÕES: MÚLTIPLAS E RASURA
    mapa_valores_global = {"A":"A", "B":"B", "C":"C", "D":"D", "Branco":"-", "Múltiplas":"*", "Rasura":"R", None: "-"}

    st.markdown("### 🖱️ Painel de Transcrição OMR")
    if st.session_state.msg_erro:
        st.error(st.session_state.msg_erro)
        st.session_state.msg_erro = None
    if st.session_state.msg_sucesso_form:
        st.success(st.session_state.msg_sucesso_form)
        st.session_state.msg_sucesso_form = None

    if not st.session_state['turma_confirmada']:
        tab_criar, tab_hist = st.tabs(["📝 Iniciar Nova Turma", "📂 Buscar do Meu Histórico (Nuvem)"])
        
        with tab_criar:
            with st.container(border=True):
                if not ETAPAS_ATIVAS:
                    st.error("🚨 **SISTEMA FECHADO:** Não há nenhum ciclo avaliativo com prazo em aberto. Aguarde a Coordenação liberar um novo prazo.")
                else:
                    st.markdown("**Defina os dados da turma que será iniciada:**")
                    c_etapa, c_escola = st.columns([1, 2])
                    with c_etapa: s_etapa = st.selectbox("Ciclo Avaliativo:", ETAPAS_ATIVAS, key="s_eta")
                    with c_escola: s_escola = st.selectbox("Escola:", ESCOLAS_SAMAR, key="s_esc")
                    
                    c_ano, c_turma, c_turno = st.columns(3)
                    with c_ano: s_ano = st.selectbox("Ano de Ensino:", ANOS_ENSINO, key="s_ano")
                    with c_turma: s_turma = st.selectbox("Turma:", TURMAS_DISP, key="s_tur")
                    with c_turno: s_turno = st.selectbox("Turno:", TURNOS_DISP, key="s_tno")
                    
                    if st.button("✅ Confirmar e Abrir Cartão-Resposta", type="primary", use_container_width=True):
                        if not s_escola or not s_ano or not s_turma or not s_turno:
                            st.session_state.msg_erro = "⚠️ Preencha todos os campos obrigatórios da turma!"
                            st.rerun()
                        else:
                            q_esperadas_check, _ = get_padrao_por_ano(s_ano)
                            if total_q_global != q_esperadas_check:
                                st.session_state.msg_erro = f"❌ O **{s_ano}** exige {q_esperadas_check} questões. Por favor, mude o 'Modelo da Prova' no menu superior da página para continuar."
                                st.rerun()
                                
                            if usa_nuvem:
                                check_exist = supabase.table("respostas_geral").select("digitador").eq("etapa", s_etapa).eq("escola", s_escola).eq("ano_ensino", s_ano).eq("turma", s_turma).eq("turno", s_turno).limit(1).execute()
                                if check_exist.data:
                                    dono = check_exist.data[0]['digitador']
                                    if dono != nome_operador:
                                        st.session_state.msg_erro = f"⚠️ COLISÃO DE DADOS: A turma {s_turma} ({s_turno}) já foi iniciada pelo usuário '{dono}'."
                                        st.rerun()
                                    else:
                                        st.session_state.msg_erro = f"⚠️ AVISO: Você já iniciou essa turma anteriormente! Vá para a aba 'Buscar do Meu Histórico'."
                                        st.rerun()

                            st.session_state.config_etapa = s_etapa
                            st.session_state.config_escola = s_escola
                            st.session_state.config_ano = s_ano
                            st.session_state.config_turma = s_turma
                            st.session_state.config_turno = s_turno
                            st.session_state['turma_confirmada'] = True
                            st.rerun()
        
        with tab_hist:
            with st.container(border=True):
                st.markdown("**Selecione uma turma que você já digitou anteriormente:**")
                c_hist_btn, c_hist_sync = st.columns([4, 1])
                
                if usa_nuvem:
                    res_historico = supabase.table("respostas_geral").select("etapa, escola, ano_ensino, turma, turno").eq("digitador", nome_operador).execute()
                    if res_historico.data:
                        df_hist = pd.DataFrame(res_historico.data).drop_duplicates()
                        if not df_hist.empty:
                            lista_dropdown = []
                            for _, r in df_hist.iterrows():
                                lista_dropdown.append(f"{r['etapa']} | {r['escola']} | {r['ano_ensino']} - Turma {r['turma']} ({r['turno']})")
                            
                            selecao_historico = st.selectbox("Suas turmas encontradas na base:", lista_dropdown, key="s_hist")
                            
                            with c_hist_btn:
                                if st.button("📂 Puxar Esta Turma da Nuvem", type="primary", use_container_width=True):
                                    partes = selecao_historico.split(" | ")
                                    st.session_state.config_etapa = partes[0]
                                    st.session_state.config_escola = partes[1]
                                    extra = partes[2].split(" - Turma ")
                                    st.session_state.config_ano = extra[0]
                                    turma_turno = extra[1].split(" (")
                                    st.session_state.config_turma = turma_turno[0]
                                    st.session_state.config_turno = turma_turno[1].replace(")", "")
                                    
                                    q_esperadas_check, _ = get_padrao_por_ano(st.session_state.config_ano)
                                    if total_q_global != q_esperadas_check:
                                        st.session_state.msg_erro = f"❌ O **{st.session_state.config_ano}** exige {q_esperadas_check} questões. Altere o 'Modelo da Prova' no topo e tente novamente."
                                    else:
                                        st.session_state['turma_confirmada'] = True
                                        st.rerun()
                            with c_hist_sync:
                                if st.button("🔄 Sincronizar", use_container_width=True): st.rerun()
                        else: st.info("Nenhuma turma salva. Se o Admin excluiu a turma, ela some daqui.")
                    else: st.info("Nenhuma turma salva. Se o Admin excluiu a turma, ela some daqui.")

    else:
        st.success(f"📌 **Local de Trabalho Fixo:** {st.session_state.config_etapa} | {st.session_state.config_escola} | {st.session_state.config_ano} - Turma {st.session_state.config_turma} ({st.session_state.config_turno})")
        if st.button("⬅️ Sair Desta Turma (Voltar ao Menu)"):
            st.session_state['turma_confirmada'] = False
            st.session_state.config_etapa = ""
            st.session_state.config_escola = ""
            st.session_state.config_ano = ""
            st.session_state.config_turma = ""
            st.session_state.config_turno = ""
            st.session_state.gerar_zip_digitador = False
            st.rerun()

        turma_esta_bloqueada = False
        etapa_vencida = st.session_state.config_etapa not in ETAPAS_ATIVAS
        
        if usa_nuvem:
            res_check_lock = supabase.table("respostas_geral").select("status").eq("etapa", st.session_state.config_etapa).eq("escola", st.session_state.config_escola).eq("ano_ensino", st.session_state.config_ano).eq("turma", st.session_state.config_turma).eq("turno", st.session_state.config_turno).execute()
            if res_check_lock.data and any(r.get('status') == 'Bloqueado' for r in res_check_lock.data):
                turma_esta_bloqueada = True

        q_esperadas_dig, blocos_esperados_dig = get_padrao_por_ano(st.session_state.config_ano)

        if etapa_vencida:
            turma_esta_bloqueada = True
            st.error(f"⏳ **PRAZO ENCERRADO:** A data limite configurada para a etapa **{st.session_state.config_etapa}** expirou.")
        elif turma_esta_bloqueada:
            st.error("🔒 **TURMA BLOQUEADA PELA COORDENAÇÃO:** O boletim desta turma já foi gerado.")

        if not turma_esta_bloqueada:
            with st.container(border=True):
                st.markdown("#### 👤 Inserir Novo Cartão-Resposta")
                
                # NOVO FORMULÁRIO (EVITA A TELA PISCANDO)
                with st.form("form_cartao_aluno", clear_on_submit=True):
                    nome_aluno_input = st.text_input("Nome do Aluno:", max_chars=100)
                    st.divider()
                    
                    col_f1, col_f2 = st.columns(2)
                    with col_f1: freq_d = st.radio("Dezena (D):", ["0","1","2","3","4","5","6","7","8","9"], horizontal=True, index=0)
                    with col_f2: freq_u = st.radio("Unidade (U):", ["0","1","2","3","4","5","6","7","8","9"], horizontal=True, index=None)
                    
                    st.divider()
                    cols_blocos = st.columns(len(blocos_esperados_dig)) 
                    # NOVAS OPÇÕES: MÚLTIPLAS E RASURA
                    opcoes_visuais = ["A", "B", "C", "D", "Branco", "Múltiplas", "Rasura"]
                    
                    respostas_temp = {}
                    q_num = 1
                    for i, (nome_disc, qtd_q) in enumerate(blocos_esperados_dig):
                        with cols_blocos[i]:
                            st.markdown(f"**{nome_disc}**")
                            for r in range(qtd_q):
                                respostas_temp[q_num] = st.radio(f"Questão {q_num:02d}", options=opcoes_visuais, index=None, horizontal=True)
                                q_num += 1
                    
                    st.write("")
                    submit_aluno = st.form_submit_button("Salvar Cartão deste Aluno", type="primary", use_container_width=True)
                    
                    if submit_aluno:
                        erros = []
                        if not nome_aluno_input.strip(): erros.append("O campo 'Nome do Aluno' não pode ficar em branco.")
                        if freq_u is None: erros.append("Marque a Unidade (U) da Frequência.")
                        vazias = [str(q) for q, v in respostas_temp.items() if v is None]
                        if vazias: erros.append(f"Faltam as questões: {', '.join(vazias)}.")
                        
                        nova_freq = (freq_d if freq_d else "0") + (freq_u if freq_u else "0")
                        
                        # BLOQUEIO DE FREQUÊNCIA DUPLICADA NA TURMA
                        if not erros and usa_nuvem:
                            res_check_dup = supabase.table("respostas_geral").select("frequencia").eq("etapa", st.session_state.config_etapa).eq("escola", st.session_state.config_escola).eq("ano_ensino", st.session_state.config_ano).eq("turma", st.session_state.config_turma).eq("turno", st.session_state.config_turno).execute()
                            if res_check_dup.data and nova_freq in [x['frequencia'] for x in res_check_dup.data]:
                                erros.append(f"Já existe um aluno cadastrado com a Frequência '{nova_freq}'. Exclua o antigo na tabela abaixo ou use outra frequência.")
                        
                        if erros:
                            for e in erros: st.error(f"⚠️ {e}")
                        else:
                            resp_str = "".join([mapa_valores_global[respostas_temp[q]] for q in range(1, q_esperadas_dig + 1)])
                            novo_dado = {
                                "etapa": st.session_state.config_etapa, "escola": st.session_state.config_escola, 
                                "ano_ensino": st.session_state.config_ano, "turma": st.session_state.config_turma, 
                                "turno": st.session_state.config_turno, "frequencia": nova_freq, 
                                "nome_aluno": nome_aluno_input, "respostas_brutas": resp_str, 
                                "digitador": nome_operador, "status": "Aberto"
                            }
                            try:
                                supabase.table("respostas_geral").insert([novo_dado]).execute()
                                st.session_state.msg_sucesso_form = f"✅ Aluno {nome_aluno_input} (Freq: {nova_freq}) salvo com sucesso!"
                                st.rerun() # Refresh instantâneo da tabela
                            except Exception as e:
                                st.error("Erro ao salvar no banco de dados.")

        st.markdown("---")
        
        st.markdown(f"#### 📁 Alunos Registrados nesta Turma")
        if usa_nuvem:
            res_turma = supabase.table("respostas_geral").select("*").eq("etapa", st.session_state.config_etapa).eq("escola", st.session_state.config_escola).eq("ano_ensino", st.session_state.config_ano).eq("turma", st.session_state.config_turma).eq("turno", st.session_state.config_turno).eq("digitador", nome_operador).execute()
            
            if res_turma.data:
                df_turma = pd.DataFrame(res_turma.data)
                df_turma.rename(columns={"id": "ID", "escola": "Escola", "ano_ensino": "Ano_Ensino", "turma": "Turma", "turno": "Turno", "frequencia": "Frequencia", "nome_aluno": "Nome_Aluno", "respostas_brutas": "Respostas_Brutas", "status": "Status"}, inplace=True)
                
                for q in range(1, q_esperadas_dig + 1):
                    df_turma[f"Q{q:02d}"] = df_turma["Respostas_Brutas"].apply(lambda x: x[q-1] if isinstance(x, str) and len(x) >= q else "-")
                
                colunas_exibir = ["ID", "Frequencia", "Nome_Aluno"] + [f"Q{q:02d}" for q in range(1, q_esperadas_dig + 1)]
                config_colunas = {"ID": None, "Frequencia": st.column_config.TextColumn("Freq.", max_chars=2, width="small")}
                
                # ADICIONADO * (Múltiplas) e R (Rasura) NA TABELA
                for q in range(1, q_esperadas_dig + 1): config_colunas[f"Q{q:02d}"] = st.column_config.SelectboxColumn(f"Q{q:02d}", options=["A", "B", "C", "D", "-", "*", "R"], width="small", required=True)

                if turma_esta_bloqueada:
                    st.caption("🔒 MODO LEITURA: A tabela abaixo está bloqueada devido às travas de segurança da Coordenação.")
                    st.dataframe(df_turma[colunas_exibir], use_container_width=True, column_config=config_colunas, height=300)
                else:
                    st.caption("Dê dois cliques na célula para corrigir uma letra ou aperte 'Delete' para apagar um aluno.")
                    df_editado_ui = st.data_editor(df_turma[colunas_exibir], use_container_width=True, num_rows="dynamic", column_config=config_colunas, height=300, key=f"editor_dig_fixo")
                    
                    if st.button("Salvar Edições da Tabela na Nuvem", type="primary", use_container_width=True):
                        df_salvar = df_editado_ui.copy()
                        df_salvar["Respostas_Brutas"] = df_salvar[[f"Q{q:02d}" for q in range(1, q_esperadas_dig + 1)]].agg(lambda x: ''.join(x.astype(str)), axis=1)
                        
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

                st.write("")
                col_down1, col_down2 = st.columns(2)
                with col_down1:
                    st.download_button("📊 Exportar Tabela em CSV", df_turma.to_csv(index=False, sep=";"), f"Turma_{st.session_state.config_turma}.csv", "text/csv", use_container_width=True)
                
                with col_down2:
                    if st.button("🖼️ Empacotar Imagens (ZIP)", key="btn_zip_dig", use_container_width=True):
                        st.session_state.gerar_zip_digitador = True
                    
                    if st.session_state.get('gerar_zip_digitador', False):
                        with st.spinner("Injetando Cabeçalho e Gerando imagens, aguarde..."):
                            zip_data = gerar_zip_gabaritos(df_turma, conf, modelo, st.session_state.config_etapa, st.session_state.config_ano)
                            esc_cln = st.session_state.config_escola.replace(' ','_')
                            st.download_button(
                                label="✅ Arquivo Pronto! Clique para Baixar o ZIP", 
                                data=zip_data, 
                                file_name=f"Gabaritos_{esc_cln}_{st.session_state.config_turma}.zip", 
                                mime="application/zip", 
                                type="primary", use_container_width=True
                            )
            else:
                st.info("Nenhum aluno registrado para esta turma no momento.")

        # ====================================================================
        # ATA ÚNICA E EDITÁVEL POR TURMA
        # ====================================================================
        st.markdown("---")
        st.markdown("#### 📋 Ata Oficial de Ocorrência da Turma")
        
        ata_texto_existente = ""
        ata_aplicador_existente = ""
        if usa_nuvem:
            res_ata = supabase.table("atas_ocorrencias").select("*").eq("etapa", st.session_state.config_etapa).eq("escola", st.session_state.config_escola).eq("ano_ensino", st.session_state.config_ano).eq("turma", st.session_state.config_turma).eq("turno", st.session_state.config_turno).execute()
            if res_ata.data:
                ata_texto_existente = res_ata.data[0].get("ocorrencia", "")
                ata_aplicador_existente = res_ata.data[0].get("aplicador", "")

        if turma_esta_bloqueada:
            st.error("🔒 O envio e edição de atas para este ciclo/turma foi encerrado.")
            if ata_texto_existente:
                st.info(f"**Aplicador Responsável:** {ata_aplicador_existente}")
                st.text_area("Ocorrência Registrada:", value=ata_texto_existente, disabled=True)
        else:
            with st.expander("📝 Editar Ata desta Turma (Apenas 1 documento por Turma)", expanded=True):
                with st.form("form_ata", clear_on_submit=False):
                    nome_aplicador = st.text_input("NOME DO APLICADOR:", value=ata_aplicador_existente)
                    texto_ata = st.text_area("DESCRIÇÃO DA OCORRÊNCIA:", value=ata_texto_existente, height=100)
                    data_atual = datetime.now().strftime("%d/%m/%Y %H:%M")
                    
                    if st.form_submit_button("Salvar / Atualizar Ata da Turma", type="primary"):
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
                                try: 
                                    supabase.table("atas_ocorrencias").delete().eq("etapa", st.session_state.config_etapa).eq("escola", st.session_state.config_escola).eq("ano_ensino", st.session_state.config_ano).eq("turma", st.session_state.config_turma).eq("turno", st.session_state.config_turno).execute()
                                    supabase.table("atas_ocorrencias").insert(nova_ata).execute()
                                except: pass
                            
                            html_doc = gerar_html_ata(st.session_state.config_etapa, st.session_state.config_escola, st.session_state.config_ano, st.session_state.config_turma, st.session_state.config_turno, nome_aplicador, texto_ata, nome_operador, data_atual)
                            st.session_state['ultima_ata_html'] = html_doc
                            st.success("✅ Ata consolidada salva com sucesso!")
                            st.rerun()

                if st.session_state.get('ultima_ata_html'):
                    st.download_button("🖨️ Baixar Via da Ata (HTML)", data=st.session_state['ultima_ata_html'], file_name="Ata.html", mime="text/html")
