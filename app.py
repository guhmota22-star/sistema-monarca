import streamlit as st
import json
import os
import datetime
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai
import re

# --- 1. CONFIGURAÇÃO DE INTERFACE ---
st.set_page_config(page_title="SISTEMA: MONARCA", page_icon="🔱", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #e0e0e0; font-family: 'Orbitron', sans-serif; }
    h1, h2, h3 { color: #00d4ff; text-shadow: 0 0 10px #00d4ff; }
    [data-baseweb="tab-list"] { gap: 8px !important; display: flex !important; flex-wrap: wrap !important; justify-content: center !important; }
    button[data-baseweb="tab"] { font-size: 12px !important; padding: 8px 12px !important; border: 1px solid rgba(0, 212, 255, 0.2) !important; border-radius: 5px !important; }
    .system-card { border: 1px solid #00d4ff; padding: 20px; border-radius: 10px; background-color: rgba(0, 212, 255, 0.05); margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. MOTOR DO SISTEMA ---
SAVE_FILE = "sistema_data.json"

def carregar_dados():
    hoje = str(datetime.date.today())
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r") as f:
            data = json.load(f)
            if datetime.date.today().weekday() == 0 and data.get("reset_semanal") != hoje:
                data["descanso_usado"] = False
                data["reset_semanal"] = hoje
            return data
    return {
        "lvl": 1, "xp": 0, "rank": "E",
        "stats": {"STR": 10, "INT": 10, "SEN": 10, "VIT": 10, "EST": 10},
        "combos": {"med": 0, "gym": 0},
        "descanso_usado": False, "penalidades": [], "reset_semanal": hoje
    }

if 'data' not in st.session_state:
    st.session_state.data = carregar_dados()

def salvar():
    with open(SAVE_FILE, "w") as f:
        json.dump(st.session_state.data, f)

def ganhar_xp(valor, stat=None):
    if st.session_state.data["penalidades"]:
        st.error("🚫 DÍVIDA ATIVA!")
        return
    st.session_state.data["xp"] += valor
    if stat: st.session_state.data["stats"][stat] += 1
    if st.session_state.data["xp"] >= 100:
        st.session_state.data["lvl"] += 1
        st.session_state.data["xp"] = 0
    total = sum(st.session_state.data["stats"].values())
    ranks = [("S", 550), ("A", 400), ("B", 275), ("C", 175), ("D", 100), ("E", 0)]
    for r, v in ranks:
        if total >= v:
            st.session_state.data["rank"] = r
            break
    salvar()

# --- 3. CONFIGURAÇÃO DINÂMICA DO ORÁCULO ---
api_key = st.secrets.get("GOOGLE_API_KEY")

@st.cache_resource
def configurar_ia(key):
    if not key: return None
    try:
        genai.configure(api_key=key)
        # Tenta encontrar um modelo compatível automaticamente
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'gemini-1.5-flash' in m.name:
                    return genai.GenerativeModel(m.name)
        # Backup se não achar o Flash
        return genai.GenerativeModel('gemini-pro')
    except Exception as e:
        st.error(f"Erro ao mapear modelos: {e}")
        return None

model = configurar_ia(api_key)

# --- 4. INTERFACE ---
st.title("🔱 SISTEMA: GUH MOTA")

tabs = st.tabs(["📊 STATUS", "🩺 MEDICINA", "🏋️ ACADEMIA", "💀 PUNIÇÕES"])

with tabs[0]: # STATUS
    st.markdown(f"""<div class="system-card">
        <h2 style="margin:0;">GUH MOTA</h2>
        <p style="color:#00d4ff; margin:0;">RANK {st.session_state.data['rank']} | LVL {st.session_state.data['lvl']}</p>
    </div>""", unsafe_allow_html=True)
    col_r, col_t = st.columns([2,1])
    with col_r:
        df_radar = pd.DataFrame(dict(r=list(st.session_state.data["stats"].values()), theta=list(st.session_state.data["stats"].keys())))
        fig = go.Figure(data=go.Scatterpolar(r=df_radar['r'], theta=df_radar['theta'], fill='toself', line_color='#00d4ff'))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 30])), paper_bgcolor="rgba(0,0,0,0)", font_color="white", margin=dict(l=40, r=40, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
    with col_t:
        for s, v in st.session_state.data["stats"].items(): st.write(f"**{s}:** {v}")

with tabs[1]: # MEDICINA
    st.subheader("🏥 INTERNATO GO")
    if st.button("ENFERMARIA / MATERNIDADE"): ganhar_xp(20, "SEN"); salvar()
    if st.button("PLANTÃO (12H)"): ganhar_xp(40, "VIT"); salvar()

with tabs[2]: # ACADEMIA & ORÁCULO
    st.subheader("💪 ACADEMIA")
    if st.button("CONCLUIR TREINO"): ganhar_xp(30, "STR"); salvar()
    
    st.markdown("---")
    st.subheader("🔮 O ORÁCULO")
    relato = st.text_area("Relate seu esforço:", placeholder="Hoje o plantão em GO...")
    
    if st.button("ENVIAR AO ORÁCULO"):
        if model and relato:
            try:
                with st.spinner("O Sistema está analisando..."):
                    res = model.generate_content(f"Analise como o Sistema de Solo Leveling. Relato: '{relato}'. Retorne JSON: {{'xp': 10, 'stat': 'STR', 'msg': 'mensagem'}}")
                    match = re.search(r'\{.*\}', res.text, re.DOTALL)
                    if match:
                        js = json.loads(match.group())
                        ganhar_xp(js['xp'], js['stat'])
                        st.success(js['msg'])
                    else: st.error("Erro no formato da IA.")
            except Exception as e: st.error(f"Falha de conexão: {e}")
        else: st.warning("Sistema Offline. Verifique sua Key ou o relato.")

with tabs[3]: # PUNIÇÕES
    if st.session_state.data["penalidades"]:
        for p in st.session_state.data["penalidades"]: st.error(f"❌ {p}")
        if st.button("PAGUEI"): st.session_state.data["penalidades"] = []; salvar(); st.rerun()
    else: st.success("Caminho limpo, Monarca.")
