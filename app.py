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
# FUNÇÕES DE APOIO E LIMPEZA
# ====================================================================
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

def hash_senha(senha): return hashlib.sha256(senha.encode()).hexdigest()

# ====================================================================
# SEMEADOR DE DADOS DA NUVEM (PARA NÃO NASCER VAZIO)
# ====================================================================
if usa_nuvem:
    try:
        chk_esc = supabase.table("escolas_oficiais").select("id").limit(1).execute()
        if not chk_esc.data:
            escolas_iniciais = [
                "COLÉGIO MILITAR TIRADENTES XII", "UNIDADE ESCOLAR JOSÉ LISBOA", "UNIDADE ESCOLAR MANOEL BATISTA",
                "UNIDADE ESCOLAR NOVA ARAÇAGI", "UNIDADE ESCOLAR SOCORRO MAGALHÃES", "UNIDADE ESCOLAR SÃO JOAQUIM",
                "UNIDADE ESCOLAR VILA NOVA", "UNIDADE ESCOLAR VILA SÃO JOÃO", "UNIDADE INTEGRADA CRIANÇA ESPERANÇA",
                "UNIDADE INTEGRADA HENRIQUE DE LA ROQUE", "UNIDADE INTEGRADA JARBAS PASSARINHO", "UNIDADE INTEGRADA MARCONE CALDAS",
                "UNIDADE INTEGRADA PROFESSORA MARIA ROSA REIS TRINDADE", "UNIDADE INTEGRADA RURAL BOA ESPERANÇA",
                "UNIDADE INTEGRADA SANTO ANTÔNIO", "UNIDADE INTEGRADA SARNEY FILHO"
            ]
            supabase.table("escolas_oficiais").insert([{"nome_escola": e} for e in escolas_iniciais]).execute()

        chk_ano = supabase.table("anos_oficiais").select("id").limit(1).execute()
        if not chk_ano.data:
            anos_iniciais = ["1º Ano", "2º Ano", "3º Ano", "4º Ano", "5º Ano", "6º Ano", "7º Ano", "8º Ano", "9º Ano"]
            supabase.table("anos_oficiais").insert([{"ano_ensino": a} for a in anos_iniciais]).execute()

        chk_eta = supabase.table("etapas_oficiais").select("id").limit(1).execute()
        if not chk_eta.data:
            supabase.table("etapas_oficiais").insert([{"nome_etapa": "Avaliação Diagnóstica", "data_abertura": "2020-01-01", "data_limite": "2030-12-31"}]).execute()
    except: pass

# ====================================================================
# CARREGAMENTO GLOBAL DAS LISTAS DA NUVEM
# ====================================================================
ESCOLAS_SAMAR = [""]
ANOS_ENSINO = [""]
TODAS_ETAPAS = []
ETAPAS_ATIVAS = []
dict_gabaritos_mestres = {}

if usa_nuvem:
    try:
        r_esc = supabase.table("escolas_oficiais").select("nome_escola").execute()
        if r_esc.data: ESCOLAS_SAMAR += sorted([x['nome_escola'] for x in r_esc.data])

        r_ano = supabase.table("anos_oficiais").select("ano_ensino").execute()
        if r_ano.data: ANOS_ENSINO += sorted([x['ano_ensino'] for x in r_ano.data])

        r_eta = supabase.table("etapas_oficiais").select("*").execute()
        hoje = datetime.now().date()
        if r_eta.data:
            for row in r_eta.data:
                n_etapa = str(row.get('nome_etapa', '')).strip()
                if not n_etapa: continue
                TODAS_ETAPAS.append(n_etapa)
                try:
                    d_abert = datetime.strptime(str(row.get('data_abertura', '2020-01-01')).split()[0], "%Y-%m-%d").date()
                    d_lim = datetime.strptime(str(row.get('data_limite', '2030-12-31')).split()[0], "%Y-%m-%d").date()
                    if d_abert <= hoje <= d_lim: ETAPAS_ATIVAS.append(n_etapa)
                except: ETAPAS_ATIVAS.append(n_etapa)

        r_gab = supabase.table("gabaritos_oficiais").select("*").execute()
        if r_gab.data:
            for i in r_gab.data: dict_gabaritos_mestres[(i['etapa'], i['ano_ensino'])] = str(i['gabarito']).upper().strip()
    except Exception as e: pass

if not TODAS_ETAPAS: TODAS_ETAPAS = ["Padrão"]
if not ETAPAS_ATIVAS: ETAPAS_ATIVAS = TODAS_ETAPAS

TURMAS_DISP = ["", "A", "B", "C", "D", "E", "F", "G", "H", "Única"]
TURNOS_DISP = ["", "Manhã", "Tarde", "Integral", "Noite"]

estados_padrao = {
    'usuario_logado': None, 'nome_logado': None, 'perfil_logado': None,
    'turma_confirmada': False, 'config_etapa': "", 'config_escola': "",
    'config_ano': "", 'config_turma': "", 'config_turno': "",
    'freq_d': "0", 'freq_u': None, 'nome_aluno_input': "",
    'msg_erro': None, 'msg_sucesso_form': None, 'gerar_zip_digitador': False,
    'reset_form_questoes': 0
}
for key, valor in estados_padrao.items():
    if key not in st.session_state: st.session_state[key] = valor

# ====================================================================
# GERADORES DE ARQUIVOS (PDF COM CABEÇALHO OFICIAL)
# ====================================================================
def gerar_zip_gabaritos(df, conf_prova, modelo_prova, etapa_nome, ano_nome):
    id_unico = uuid.uuid4().hex
    fn_pdf = f"base_temp_{modelo_prova}_{id_unico}.pdf"
    
    # RESOLUÇÃO DO ERRO DO GERADOR: Puxa a string direta do arquivo se ele existir
    logo_file = "Frame 18.png" if os.path.exists("Frame 18.png") else None
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
        if not df_atas.empty:
            for idx, row in df_atas.iterrows():
                eta = str(row.get("Etapa", "Padrão"))
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
            senha_criptografada = hash_senha(senha_input)
            if email_input == "admin" and senha_input == "coted2026":
                st.session_state['usuario_logado'] = "admin"
                st.session_state['nome_logado'] = "Coordenação Master"
                st.session_state['perfil_logado'] = "Administrador"
                st.rerun()
            elif usa_nuvem:
                res = supabase.table("usuarios_oficiais").select("*").eq("email", email_input).eq("senha", senha_criptografada).execute()
                if res.data:
                    st.session_state['usuario_logado'] = email_input
                    st.session_state['nome_logado'] = res.data[0]['nome']
                    st.session_state['perfil_logado'] = res.data[0]['perfil']
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

for q in range(1, total_q_global + 1):
    if f"q_{q}" not in st.session_state: st.session_state[f"q_{q}"] = None

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
        st.markdown("### ⚙️ Gestão de Ciclos e Gabaritos (100% Nuvem)")
        
        with st.container(border=True):
            st.markdown("#### 📅 1. Definir Ciclos e Prazos de Acesso")
            if usa_nuvem:
                r_et = supabase.table("etapas_oficiais").select("*").execute()
                df_etapas_edit = pd.DataFrame(r_et.data) if r_et.data else pd.DataFrame(columns=["id", "nome_etapa", "data_abertura", "data_limite"])
                df_etapas_edit['data_abertura'] = pd.to_datetime(df_etapas_edit['data_abertura'], errors='coerce').dt.date
                df_etapas_edit['data_limite'] = pd.to_datetime(df_etapas_edit['data_limite'], errors='coerce').dt.date
                
                edited_etapas = st.data_editor(
                    df_etapas_edit,
                    column_config={
                        "id": None, 
                        "nome_etapa": st.column_config.TextColumn("Nome do Ciclo", required=True), 
                        "data_abertura": st.column_config.DateColumn("Abertura", format="DD/MM/YYYY"), 
                        "data_limite": st.column_config.DateColumn("Prazo Final", format="DD/MM/YYYY")
                    },
                    num_rows="dynamic", use_container_width=True, key="ed_etp"
                )
                if st.button("💾 Salvar Ciclos e Prazos", type="primary"):
                    c_ids = [r["id"] for _, r in edited_etapas.iterrows() if pd.notna(r.get("id")) and str(r.get("id")).strip()]
                    db_ids = [x["id"] for x in r_et.data] if r_et.data else []
                    to_del = [x for x in db_ids if x not in c_ids]
                    if to_del: supabase.table("etapas_oficiais").delete().in_("id", to_del).execute()
                    
                    recs = []
                    for _, r in edited_etapas.iterrows():
                        if pd.notna(r["nome_etapa"]):
                            d_a = r['data_abertura'].strftime('%Y-%m-%d') if pd.notna(r['data_abertura']) else '2020-01-01'
                            d_l = r['data_limite'].strftime('%Y-%m-%d') if pd.notna(r['data_limite']) else '2030-12-31'
                            recs.append({"id": r["id"] if pd.notna(r.get("id")) and str(r.get("id")).strip() else str(uuid.uuid4()), "nome_etapa": r["nome_etapa"], "data_abertura": d_a, "data_limite": d_l})
                    if recs: supabase.table("etapas_oficiais").upsert(recs).execute()
                    st.success("Ciclos atualizados no Supabase!")
                    st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        
        with st.container(border=True):
            st.markdown("#### 🔑 2. Atribuir Gabaritos Mestres por Ciclo")
            c_gab1, c_gab2 = st.columns(2)
            with c_gab1: sel_eta_gab = st.selectbox("Selecione o Ciclo:", TODAS_ETAPAS, key="sel_eta_gab")
            with c_gab2: sel_ano_gab = st.selectbox("Selecione o Ano de Ensino Avaliado:", ANOS_ENSINO, key="sel_ano_gab")
            
            if sel_eta_gab and sel_ano_gab:
                gab_existente = dict_gabaritos_mestres.get((sel_eta_gab, sel_ano_gab), "")
                if gab_existente: 
                    st.success(f"✅ Já existe um gabarito cadastrado para o **{sel_ano_gab}** na etapa **{sel_eta_gab}**.")
                    if st.button("🗑️ Excluir este Gabarito Mestre", type="secondary"):
                        supabase.table("gabaritos_oficiais").delete().eq("etapa", sel_eta_gab).eq("ano_ensino", sel_ano_gab).execute()
                        st.warning(f"Gabarito do {sel_ano_gab} excluído com sucesso!")
                        st.rerun()
                
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
            if usa_nuvem:
                r_esc = supabase.table("escolas_oficiais").select("*").execute()
                df_esc_edit = pd.DataFrame(r_esc.data) if r_esc.data else pd.DataFrame(columns=["id", "nome_escola"])
                edited_escolas = st.data_editor(df_esc_edit, column_config={"id": None, "nome_escola": st.column_config.TextColumn("Nome da Escola", required=True)}, num_rows="dynamic", use_container_width=True, key="ed_esc")
                if st.button("💾 Salvar Escolas", type="primary"):
                    c_ids = [r["id"] for _, r in edited_escolas.iterrows() if pd.notna(r.get("id")) and str(r.get("id")).strip()]
                    db_ids = [x["id"] for x in r_esc.data] if r_esc.data else []
                    to_del = [x for x in db_ids if x not in c_ids]
                    if to_del: supabase.table("escolas_oficiais").delete().in_("id", to_del).execute()
                    
                    recs = [{"id": r["id"] if pd.notna(r.get("id")) and str(r.get("id")).strip() else str(uuid.uuid4()), "nome_escola": r["nome_escola"]} for _, r in edited_escolas.iterrows() if pd.notna(r["nome_escola"])]
                    if recs: supabase.table("escolas_oficiais").upsert(recs).execute()
                    st.rerun()

        with c_cfg3:
            st.markdown("#### 🎓 4. Anos de Ensino")
            if usa_nuvem:
                r_ano = supabase.table("anos_oficiais").select("*").execute()
                df_ano_edit = pd.DataFrame(r_ano.data) if r_ano.data else pd.DataFrame(columns=["id", "ano_ensino"])
                edited_anos = st.data_editor(df_ano_edit, column_config={"id": None, "ano_ensino": st.column_config.TextColumn("Ano / Série", required=True)}, num_rows="dynamic", use_container_width=True, key="ed_ano")
                if st.button("💾 Salvar Anos", type="primary"):
                    c_ids = [r["id"] for _, r in edited_anos.iterrows() if pd.notna(r.get("id")) and str(r.get("id")).strip()]
                    db_ids = [x["id"] for x in r_ano.data] if r_ano.data else []
                    to_del = [x for x in db_ids if x not in c_ids]
                    if to_del: supabase.table("anos_oficiais").delete().in_("id", to_del).execute()
                    
                    recs = [{"id": r["id"] if pd.notna(r.get("id")) and str(r.get("id")).strip() else str(uuid.uuid4()), "ano_ensino": r["ano_ensino"]} for _, r in edited_anos.iterrows() if pd.notna(r["ano_ensino"])]
                    if recs: supabase.table("anos_oficiais").upsert(recs).execute()
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
                
                # RESOLUÇÃO DO ERRO DO GERADOR AQUI TAMBÉM
                if logo_cen is None and os.path.exists("Frame 18.png"): 
                    logo_cen = "Frame 18.png"
                    
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
# ABA 2: LEITOR ROBÔ
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
                            freqs_lidas = [r["Frequencia"] for r in resultados_lote]
                            freqs_dup = set([x for x in freqs_lidas if freqs_lidas.count(x) > 1])
                            if freqs_dup:
                                st.error(f"🚨 ATENÇÃO: Foram encontradas imagens de provas com a mesma Frequência ({', '.join(freqs_dup)}). Verifique o lote lido antes de subir os dados para o sistema.")
                            
                            df_export = pd.DataFrame(resultados_lote)
                            st.download_button("📥 Baixar CSV Corrigido", df_export.to_csv(index=False, sep=";"), f"Resultados_Robo_{ano_leitor}_{turma_leitor}.csv", "text/csv", type="primary")

# ====================================================================
# ABA 4 (ADMIN): TORRE DE CONTROLE E EXPORTAÇÃO
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

                if not df_final_filtro.empty:
                    turmas_turnos = df_final_filtro[['Escola', 'Etapa', 'Ano_Ensino', 'Turma', 'Turno']].drop_duplicates().values.tolist()
                    turmas_turnos.sort(key=lambda x: (x[2], x[0], x[3])) 
                    
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
                            for q in range(1, q_esperadas + 1):
                                df_tur[f"Q{q:02d}"] = df_tur["Respostas_Brutas"].apply(lambda x: x[q-1] if isinstance(x, str) and len(x) >= q else "-")

                            cols_editar = ["ID", "Frequencia", "Nome_Aluno"] + [f"Q{q:02d}" for q in range(1, q_esperadas+1)] + ["Digitador", "Status"]
                            config_cols_admin = {"ID": None, "Frequencia": st.column_config.TextColumn(width="small"), "Digitador": st.column_config.TextColumn(disabled=True), "Status": st.column_config.TextColumn(disabled=True)}
                            for q in range(1, q_esperadas+1): config_cols_admin[f"Q{q:02d}"] = st.column_config.SelectboxColumn(options=["A", "B", "C", "D", "-", "*", "R"], width="small")

                            df_ed = st.data_editor(df_tur[cols_editar], column_config=config_cols_admin, use_container_width=True, num_rows="dynamic", key=f"ed_adm_{eta_b}_{esc}_{ano_b}_{tur}_{tur_no}")

                            df_old = df_tur[cols_editar].reset_index(drop=True).fillna("")
                            df_new = df_ed.reset_index(drop=True).fillna("")
                            
                            if not df_old.equals(df_new):
                                freqs = df_new["Frequencia"].astype(str).str.strip().tolist()
                                if len(freqs) != len(set(freqs)):
                                    st.error("🚨 ERRO: Duplicidade de Frequência. Correção bloqueada até resolver o conflito.")
                                else:
                                    df_salvar = df_ed.copy()
                                    df_salvar["Respostas_Brutas"] = df_salvar[[f"Q{q:02d}" for q in range(1, q_esperadas + 1)]].agg(lambda x: ''.join(x.astype(str)), axis=1)
                                    records_upsert = []
                                    for _, row in df_salvar.iterrows():
                                        records_upsert.append({
                                            "id": str(row["ID"]) if pd.notna(row.get("ID")) and str(row.get("ID")) else str(uuid.uuid4()),
                                            "etapa": eta_b, "escola": esc, "ano_ensino": ano_b, 
                                            "turma": tur, "turno": tur_no, "frequencia": str(row["Frequencia"]), 
                                            "nome_aluno": str(row["Nome_Aluno"]), "respostas_brutas": str(row["Respostas_Brutas"]), 
                                            "digitador": str(row["Digitador"]) if pd.notna(row.get("Digitador")) else st.session_state['nome_logado'],
                                            "status": str(row["Status"])
                                        })
                                    supabase.table("respostas_geral").delete().eq("etapa", eta_b).eq("escola", esc).eq("ano_ensino", ano_b).eq("turma", tur).eq("turno", tur_no).execute()
                                    supabase.table("respostas_geral").upsert(records_upsert).execute()
                                    st.toast("✅ Salvo em tempo real!", icon="💾")
                                    st.rerun()
                                    
                            st.write("")
                            with st.expander("🚨 ZONA DE PERIGO: Excluir Turma", expanded=False):
                                if st.button(f"🗑️ Excluir Turma {tur} Permanentemente", key=f"del_{eta_b}_{esc}_{ano_b}_{tur}_{tur_no}"):
                                    supabase.table("respostas_geral").delete().eq("etapa", eta_b).eq("escola", esc).eq("ano_ensino", ano_b).eq("turma", tur).eq("turno", tur_no).execute()
                                    st.success("A turma foi apagada da nuvem instantaneamente.")
                                    st.rerun()
                else:
                    st.info("⬆️ Nenhum aluno encontrado para o filtro selecionado.")

                st.markdown("---")
                st.markdown("#### ⚙️ Motor Inteligente de Notas & Exportação Global")
                
                c_mot1, c_mot2 = st.columns(2)
                with c_mot1:
                    csv_export = df_final_filtro.drop(columns=["ID", "id"], errors="ignore").to_csv(index=False, sep=";")
                    st.download_button("📊 Exportar Tabela Bruta (Dados do Filtro)", csv_export, f"Dados_Brutos_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", use_container_width=True)
                
                with c_mot2:
                    if st.button("🚀 Calcular Notas do Filtro Atual e Empacotar (ZIP)", type="primary", use_container_width=True):
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
        if usa_nuvem:
            res_users = supabase.table("usuarios_oficiais").select("nome, email, perfil").execute()
            df_usuarios = pd.DataFrame(res_users.data) if res_users.data else pd.DataFrame(columns=["nome", "email", "perfil"])
            st.dataframe(df_usuarios, use_container_width=True)
            
            col_add, col_edit = st.columns(2)
            with col_add:
                with st.container(border=True):
                    st.markdown("#### ➕ Criar Novo Usuário")
                    with st.form("form_add_user", clear_on_submit=True):
                        novo_nome = st.text_input("Nome:")
                        novo_email = st.text_input("Login (E-mail):")
                        nova_senha = st.text_input("Senha:", type="password")
                        novo_perfil = st.selectbox("Perfil:", ["Digitador", "Administrador"])
                        if st.form_submit_button("Cadastrar Usuário", type="primary", use_container_width=True):
                            if novo_nome and novo_email and nova_senha:
                                if novo_email in df_usuarios['email'].values:
                                    st.error("Email já cadastrado!")
                                else:
                                    supabase.table("usuarios_oficiais").insert({"nome": novo_nome, "email": novo_email, "senha": hash_senha(nova_senha), "perfil": novo_perfil}).execute()
                                    st.rerun()
            with col_edit:
                with st.container(border=True):
                    st.markdown("#### ✏️ Editar Senha")
                    if not df_usuarios.empty:
                        user_to_edit = st.selectbox("Selecione o Usuário:", df_usuarios['email'].tolist(), key="sel_edit_user")
                        nova_senha_edit = st.text_input("Nova Senha:", type="password")
                        if st.button("Salvar Nova Senha", type="primary", use_container_width=True):
                            supabase.table("usuarios_oficiais").update({"senha": hash_senha(nova_senha_edit)}).eq("email", user_to_edit).execute()
                            st.success(f"Senha de {user_to_edit} alterada com sucesso!")
                            st.rerun()
                
                with st.container(border=True):
                    st.markdown("#### 🚨 Excluir Usuário")
                    if not df_usuarios.empty:
                        user_to_del = st.selectbox("Selecione o Usuário para remover:", df_usuarios['email'].tolist(), key="sel_del_user")
                        st.warning("⚠️ Esta ação apagará permanentemente o acesso deste usuário.")
                        if st.button(f"🗑️ Confirmar Exclusão", use_container_width=True):
                            if user_to_del == "admin":
                                st.error("Não é possível excluir o Administrador Master do sistema.")
                            else:
                                supabase.table("usuarios_oficiais").delete().eq("email", user_to_del).execute()
                                st.success(f"Acesso de {user_to_del} revogado!")
                                st.rerun()

    with tab6:
        st.markdown("### 📋 Livro Oficial de Atas")
        
        res_atas = supabase.table("atas_ocorrencias").select("*").execute() if usa_nuvem else None
        if res_atas and res_atas.data:
            df_atas = pd.DataFrame(res_atas.data)
        else:
            df_atas = pd.DataFrame(columns=["id", "etapa", "data_registro", "escola", "ano_ensino", "turma", "turno", "aplicador", "revisor_digitador", "ocorrencia"])
            
        df_atas.rename(columns={"etapa": "Etapa", "data_registro":"Data_Registro", "escola":"Escola", "ano_ensino":"Ano_Ensino", "turma":"Turma", "turno":"Turno", "aplicador":"Aplicador", "revisor_digitador":"Revisor_Digitador", "ocorrencia":"Ocorrencia"}, inplace=True)
        
        df_atas_editado = st.data_editor(df_atas, column_config={"id": None}, use_container_width=True, num_rows="dynamic", key="editor_admin_atas", height=300)
        
        col_save_atas, c1, c2 = st.columns([1.5, 1, 1])
        with col_save_atas:
            if st.button("Salvar Edições de Atas na Nuvem", use_container_width=True, type="primary") and usa_nuvem:
                if res_atas and res_atas.data:
                    c_ids = [str(r["id"]) for _, r in df_atas_editado.iterrows() if pd.notna(r.get("id")) and str(r.get("id")).strip()]
                    db_ids = [str(x["id"]) for x in res_atas.data]
                    to_del = [x for x in db_ids if x not in c_ids]
                    if to_del: supabase.table("atas_ocorrencias").delete().in_("id", to_del).execute()

                records_ata = []
                for _, row in df_atas_editado.iterrows():
                    records_ata.append({
                        "id": str(row.get("id")) if pd.notna(row.get("id")) and str(row.get("id")).strip() else str(uuid.uuid4()), 
                        "etapa": str(row.get("Etapa", "Padrão")),
                        "data_registro": str(row.get("Data_Registro", "")), "escola": str(row.get("Escola", "")),
                        "ano_ensino": str(row.get("Ano_Ensino", "")), "turma": str(row.get("Turma", "")),
                        "turno": str(row.get("Turno", "")), "aplicador": str(row.get("Aplicador", "")),
                        "revisor_digitador": str(row.get("Revisor_Digitador", "")), "ocorrencia": str(row.get("Ocorrencia", ""))
                    })
                if records_ata: supabase.table("atas_ocorrencias").upsert(records_ata).execute()
                st.success("Banco de Atas atualizado na Nuvem!")
                st.rerun()
                
        with c1: 
            csv_atas = df_atas_editado.drop(columns=["id"], errors="ignore").to_csv(index=False, sep=";")
            st.download_button("📊 Exportar Planilha (CSV)", csv_atas, f"atas_samar_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv", use_container_width=True)
        with c2: 
            st.download_button("🖨️ Baixar Documentos HTML (ZIP)", gerar_zip_atas(df_atas_editado), f"Documentos_Atas_{datetime.now().strftime('%Y%m%d')}.zip", "application/zip", use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("🚨 ZONA DE PERIGO: Excluir Ata Específica"):
            if not df_atas.empty and 'id' in df_atas.columns:
                df_atas['Label_Del'] = df_atas['Etapa'] + " | " + df_atas['Escola'] + " | " + df_atas['Ano_Ensino'] + " - Turma " + df_atas['Turma']
                ata_del_selecionada = st.selectbox("Selecione a Ata que deseja apagar permanentemente:", df_atas['Label_Del'].tolist())
                if st.button("🗑️ Excluir Ata Selecionada", type="primary"):
                    id_to_delete = df_atas[df_atas['Label_Del'] == ata_del_selecionada].iloc[0]['id']
                    supabase.table("atas_ocorrencias").delete().eq("id", str(id_to_delete)).execute()
                    st.success("Ata excluída com sucesso!")
                    st.rerun()

# ====================================================================
# ABA 3 COMPARTILHADA: A MÁGICA DO DIGITADOR 
# ====================================================================
with tab3:
    nome_operador = st.session_state['nome_logado']
    mapa_valores_global = {"A":"A", "B":"B", "C":"C", "D":"D", "Branco":"-", "Múltiplas":"*", "Rasura":"R", None: "-"}

    st.markdown("### 🖱️ Painel de Transcrição OMR")

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

        if st.session_state.msg_erro:
            st.error(st.session_state.msg_erro)
            st.session_state.msg_erro = None

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
                
                st.info("""
                **📌 Guia de Preenchimento Rápido:**
                * **Branco:** Use se a bolinha do cartão físico estiver vazia.
                * **Múltiplas:** Use se houver mais de uma letra pintada na mesma linha da questão.
                * **Rasura:** Use se o campo estiver rasgado, manchado ou ilegível.
                """)
                
                if st.session_state.msg_erro:
                    st.error(st.session_state.msg_erro)
                    st.session_state.msg_erro = None
                if st.session_state.msg_sucesso_form:
                    st.success(st.session_state.msg_sucesso_form)
                    st.session_state.msg_sucesso_form = None

                if "freq_d" not in st.session_state: st.session_state.freq_d = "0"
                if "freq_u" not in st.session_state: st.session_state.freq_u = None
                if "nome_aluno_input" not in st.session_state: st.session_state.nome_aluno_input = ""

                st.text_input("Nome do Aluno:", max_chars=100, key="nome_aluno_input")
                st.divider()

                col_f1, col_f2, col_f3 = st.columns([2, 2, 1])
                with col_f1: st.radio("Dezena (D):", ["0","1","2","3","4","5","6","7","8","9"], horizontal=True, key="freq_d")
                with col_f2: st.radio("Unidade (U):", ["0","1","2","3","4","5","6","7","8","9"], horizontal=True, key="freq_u")
                with col_f3:
                    u_val = st.session_state.freq_u if st.session_state.freq_u else "_"
                    d_val = st.session_state.freq_d if st.session_state.freq_d else "0"
                    st.markdown(
                        f"<div style='text-align: center; border: 2px dashed #0d6efd; border-radius: 10px; padding: 10px;'>"
                        f"<p style='margin:0; font-size: 14px; font-weight: bold;'>Número:</p>"
                        f"<h1 style='margin:0; font-size: 3.5rem; color: #0d6efd;'>{d_val}{u_val}</h1>"
                        f"</div>", unsafe_allow_html=True
                    )

                st.divider()
                
                with st.form("form_cartao_aluno", clear_on_submit=False):
                    cols_blocos = st.columns(len(blocos_esperados_dig)) 
                    opcoes_visuais = ["A", "B", "C", "D", "Branco", "Múltiplas", "Rasura"]
                    
                    respostas_temp = {}
                    q_num = 1
                    for i, (nome_disc, qtd_q) in enumerate(blocos_esperados_dig):
                        with cols_blocos[i]:
                            with st.container(border=True):
                                st.markdown(f"**{nome_disc}**")
                                for r in range(qtd_q):
                                    with st.container(border=True):
                                        respostas_temp[q_num] = st.radio(f"Questão {q_num:02d}", options=opcoes_visuais, index=None, horizontal=True, key=f"q_{q_num}_{st.session_state.reset_form_questoes}")
                                    q_num += 1
                                
                    st.write("")
                    submit_aluno = st.form_submit_button("Salvar Cartão deste Aluno", type="primary", use_container_width=True)
                    
                    if submit_aluno:
                        erros = []
                        if not st.session_state.nome_aluno_input.strip(): erros.append("O campo 'Nome do Aluno' não pode ficar em branco.")
                        if st.session_state.freq_u is None: erros.append("Marque a Unidade (U) da Frequência.")
                        
                        vazias = [str(q) for q, v in respostas_temp.items() if v is None]
                        if vazias: erros.append(f"Faltam marcar as questões: {', '.join(vazias)}. (Se o aluno não respondeu, marque a bolinha 'Branco').")
                        
                        nova_freq = str(st.session_state.freq_d) + str(st.session_state.freq_u)
                        
                        if not erros and usa_nuvem:
                            res_check_dup = supabase.table("respostas_geral").select("frequencia").eq("etapa", st.session_state.config_etapa).eq("escola", st.session_state.config_escola).eq("ano_ensino", st.session_state.config_ano).eq("turma", st.session_state.config_turma).eq("turno", st.session_state.config_turno).execute()
                            if res_check_dup.data and nova_freq in [x['frequencia'] for x in res_check_dup.data]:
                                erros.append(f"Já existe um aluno na tabela com a Frequência '{nova_freq}'. Exclua o antigo ou mude o número.")
                        
                        if erros:
                            for e in erros: st.error(f"⚠️ {e}")
                        else:
                            resp_str = "".join([mapa_valores_global[respostas_temp[q]] for q in range(1, q_esperadas_dig + 1)])
                            novo_dado = {
                                "id": str(uuid.uuid4()),
                                "etapa": st.session_state.config_etapa, "escola": st.session_state.config_escola, 
                                "ano_ensino": st.session_state.config_ano, "turma": st.session_state.config_turma, 
                                "turno": st.session_state.config_turno, "frequencia": nova_freq, 
                                "nome_aluno": st.session_state.nome_aluno_input, "respostas_brutas": resp_str, 
                                "digitador": nome_operador, "status": "Aberto"
                            }
                            try:
                                supabase.table("respostas_geral").insert([novo_dado]).execute()
                                st.session_state.msg_sucesso_form = f"✅ Aluno {st.session_state.nome_aluno_input} (Freq: {nova_freq}) salvo com sucesso!"
                                st.session_state.reset_form_questoes += 1
                                st.session_state.nome_aluno_input = ""
                                st.session_state.freq_d = "0"
                                st.session_state.freq_u = None
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao salvar no banco de dados: {e}")

        st.markdown("---")
        
        st.markdown(f"#### 📁 Alunos Registrados nesta Turma (Edição em Tempo Real)")
        if usa_nuvem:
            res_turma = supabase.table("respostas_geral").select("*").eq("etapa", st.session_state.config_etapa).eq("escola", st.session_state.config_escola).eq("ano_ensino", st.session_state.config_ano).eq("turma", st.session_state.config_turma).eq("turno", st.session_state.config_turno).eq("digitador", nome_operador).execute()
            
            if res_turma.data:
                df_turma = pd.DataFrame(res_turma.data)
                df_turma.rename(columns={"id": "ID", "escola": "Escola", "ano_ensino": "Ano_Ensino", "turma": "Turma", "turno": "Turno", "frequencia": "Frequencia", "nome_aluno": "Nome_Aluno", "respostas_brutas": "Respostas_Brutas", "status": "Status"}, inplace=True)
                
                for q in range(1, q_esperadas_dig + 1):
                    df_turma[f"Q{q:02d}"] = df_turma["Respostas_Brutas"].apply(lambda x: x[q-1] if isinstance(x, str) and len(x) >= q else "-")
                
                colunas_exibir = ["ID", "Frequencia", "Nome_Aluno"] + [f"Q{q:02d}" for q in range(1, q_esperadas_dig + 1)]
                config_colunas = {"ID": None, "Frequencia": st.column_config.TextColumn("Freq.", max_chars=2, width="small")}
                for q in range(1, q_esperadas_dig + 1): config_colunas[f"Q{q:02d}"] = st.column_config.SelectboxColumn(f"Q{q:02d}", options=["A", "B", "C", "D", "-", "*", "R"], width="small", required=True)

                if turma_esta_bloqueada:
                    st.caption("🔒 MODO LEITURA: A tabela abaixo está bloqueada devido às travas de segurança da Coordenação.")
                    st.dataframe(df_turma[colunas_exibir], use_container_width=True, column_config=config_colunas, height=300)
                else:
                    st.caption("Dê dois cliques na célula para corrigir uma letra ou aperte 'Delete' para apagar um aluno. O sistema salva automaticamente.")
                    
                    df_editado_ui = st.data_editor(df_turma[colunas_exibir], use_container_width=True, num_rows="dynamic", column_config=config_colunas, height=300, key=f"editor_dig_fixo")
                    
                    df_old = df_turma[colunas_exibir].reset_index(drop=True).fillna("")
                    df_new = df_editado_ui.reset_index(drop=True).fillna("")
                    
                    if not df_old.equals(df_new):
                        freqs = df_new["Frequencia"].astype(str).str.strip().tolist()
                        if len(freqs) != len(set(freqs)):
                            st.error("🚨 ERRO: Duplicidade de Frequência detectada. O salvamento em tempo real foi pausado até você corrigir.")
                        else:
                            df_salvar = df_editado_ui.copy()
                            df_salvar["Respostas_Brutas"] = df_salvar[[f"Q{q:02d}" for q in range(1, q_esperadas_dig + 1)]].agg(lambda x: ''.join(x.astype(str)), axis=1)
                            
                            records_upsert = []
                            for _, row in df_salvar.iterrows():
                                records_upsert.append({
                                    "id": str(row["ID"]) if pd.notna(row.get("ID")) and str(row.get("ID")) else str(uuid.uuid4()),
                                    "etapa": st.session_state.config_etapa, "escola": st.session_state.config_escola, 
                                    "ano_ensino": st.session_state.config_ano, "turma": st.session_state.config_turma, 
                                    "turno": st.session_state.config_turno, "frequencia": str(row["Frequencia"]), 
                                    "nome_aluno": str(row["Nome_Aluno"]), "respostas_brutas": str(row["Respostas_Brutas"]), 
                                    "digitador": nome_operador, "status": "Aberto"
                                })
                            supabase.table("respostas_geral").delete().eq("etapa", st.session_state.config_etapa).eq("escola", st.session_state.config_escola).eq("ano_ensino", st.session_state.config_ano).eq("turma", st.session_state.config_turma).eq("turno", st.session_state.config_turno).eq("digitador", nome_operador).execute()
                            supabase.table("respostas_geral").upsert(records_upsert).execute()
                            st.toast("✅ Atualizado em tempo real!", icon="☁️")
                            st.rerun()

                st.write("")
                with st.expander("🛡️ Central de Backup da Turma", expanded=False):
                    st.info("Utilize esta área para salvar o progresso no seu computador ou restaurar a turma em caso de erro fatal.")
                    c_bkp1, c_bkp2 = st.columns(2)
                    with c_bkp1:
                        csv_bkp = df_turma.drop(columns=["ID"], errors="ignore").to_csv(index=False, sep=";")
                        st.download_button("📥 Baixar Backup Atual (CSV)", csv_bkp, f"Backup_{st.session_state.config_escola}_{st.session_state.config_turma}.csv", "text/csv", use_container_width=True)
                    with c_bkp2:
                        up_bkp = st.file_uploader("📤 Restaurar Backup", type=["csv"], label_visibility="collapsed")
                        if up_bkp:
                            if st.button("⚠️ Confirmar Restauração", type="primary", use_container_width=True):
                                try:
                                    df_res = pd.read_csv(up_bkp, sep=";")
                                    records_bkp = []
                                    for _, row in df_res.iterrows():
                                        records_bkp.append({
                                            "id": str(uuid.uuid4()),
                                            "etapa": st.session_state.config_etapa, "escola": st.session_state.config_escola, 
                                            "ano_ensino": st.session_state.config_ano, "turma": st.session_state.config_turma, 
                                            "turno": st.session_state.config_turno, "frequencia": str(row["Frequencia"]), 
                                            "nome_aluno": str(row["Nome_Aluno"]), "respostas_brutas": str(row["Respostas_Brutas"]), 
                                            "digitador": nome_operador, "status": "Aberto"
                                        })
                                    supabase.table("respostas_geral").delete().eq("etapa", st.session_state.config_etapa).eq("escola", st.session_state.config_escola).eq("ano_ensino", st.session_state.config_ano).eq("turma", st.session_state.config_turma).eq("turno", st.session_state.config_turno).execute()
                                    supabase.table("respostas_geral").upsert(records_bkp).execute()
                                    st.success("Backup restaurado!")
                                    st.rerun()
                                except Exception as e:
                                    st.error("Erro ao ler o arquivo de backup.")

                st.write("")
                with st.expander("🖼️ Exportar Comprovantes Visuais (Gabaritos em Imagem)", expanded=False):
                    if st.button("Empacotar Imagens (ZIP)", key="btn_zip_dig", use_container_width=True):
                        st.session_state.gerar_zip_digitador = True
                    if st.session_state.get('gerar_zip_digitador', False):
                        with st.spinner("Injetando Cabeçalho e Gerando imagens, aguarde..."):
                            zip_data = gerar_zip_gabaritos(df_turma, conf, modelo, st.session_state.config_etapa, st.session_state.config_ano)
                            esc_cln = st.session_state.config_escola.replace(' ','_')
                            st.download_button(label="✅ Arquivo Pronto! Clique para Baixar o ZIP", data=zip_data, file_name=f"Gabaritos_{esc_cln}_{st.session_state.config_turma}.zip", mime="application/zip", type="primary", use_container_width=True)
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

                if ata_texto_existente:
                    if st.button("🗑️ Excluir Ata desta Turma"):
                        supabase.table("atas_ocorrencias").delete().eq("etapa", st.session_state.config_etapa).eq("escola", st.session_state.config_escola).eq("ano_ensino", st.session_state.config_ano).eq("turma", st.session_state.config_turma).eq("turno", st.session_state.config_turno).execute()
                        st.success("Ata apagada com sucesso da base de dados.")
                        st.rerun()

                if st.session_state.get('ultima_ata_html'):
                    st.download_button("🖨️ Baixar Via da Ata (HTML)", data=st.session_state['ultima_ata_html'], file_name="Ata.html", mime="text/html")
