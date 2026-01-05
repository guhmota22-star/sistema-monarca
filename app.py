import streamlit as st
import json
import os
import random
import datetime
import pandas as pd
import plotly.graph_objects as go
import google.generativeai as genai
import re

# --- 1. CONFIGURAÇÃO DE INTERFACE & CSS ---
st.set_page_config(page_title="SISTEMA: MONARCA", page_icon="🔱", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #e0e0e0; font-family: 'Orbitron', sans-serif; }
    h1, h2, h3 { color: #00d4ff; text-shadow: 0 0 10px #00d4ff; }
    
    /* Fix para as Abas não sobreporem no celular */
    [data-baseweb="tab-list"] {
        gap: 8px !important;
        display: flex !important;
        flex-wrap: wrap !important;
        justify-content: center !important;
    }
    button[data-baseweb="tab"] {
        font-size: 12px !important;
        padding: 8px 12px !important;
        border: 1px solid rgba(0, 212, 255, 0.2) !important;
        border-radius: 5px !important;
    }

    /* Cards Estilo Solo Leveling */
    .system-card {
        border: 1px solid #00d4ff;
        padding: 20px;
        border-radius: 10px;
        background-color: rgba(0, 212, 255, 0.05);
        margin-bottom: 10px;
    }
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
        st.error("🚫 DÍVIDA ATIVA: Cumpra a punição para ganhar XP!")
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

# --- 3. CONFIGURAÇÃO DA IA (ORÁCULO) ---
# Tenta obter a chave dos Secrets do Streamlit ou do ambiente
api_key = st.secrets.get("GOOGLE_API_KEY") if "GOOGLE_API_KEY" in st.secrets else os.environ.get("GOOGLE_API_KEY")

if api_key:
    try:
        genai.configure(api_key=api_key)
        # Ajuste no nome do modelo para evitar o erro 'NotFound'
        model = genai.GenerativeModel('models/gemini-1.5-flash')
    except Exception as e:
        st.error(f"Erro ao inicializar o Oráculo: {e}")
        model = None
else:
    model = None
    st.warning("⚠️ Chave API não configurada. O Oráculo está offline.")

# --- 4. INTERFACE PRINCIPAL ---
st.title("🔱 SISTEMA: GUH MOTA")

def obter_classe(lvl):
    if lvl < 10: return "Interno: Novato da Maternidade"
    if lvl < 20: return "Interno: Vigilante Fetal"
    if lvl < 30: return "Interno: Cavaleiro da Ocitocina"
    return "Monarca da Obstetrícia"

tabs = st.tabs(["📊 STATUS", "🩺 MEDICINA", "🏋️ ACADEMIA", "💀 PUNIÇÕES"])

with tabs[0]: # STATUS RESTAURADO
    st.markdown(f"""
        <div class="system-card">
            <h2 style="margin:0;">GUH MOTA</h2>
            <p style="color:#00d4ff;">CLASSE: {obter_classe(st.session_state.data['lvl'])} | RANK {st.session_state.data['rank']}</p>
            <p>NÍVEL {st.session_state.data['lvl']} ({st.session_state.data['xp']}/100 XP)</p>
        </div>
    """, unsafe_allow_html=True)
    
    col_r, col_t = st.columns([2,1])
    with col_r:
        df_radar = pd.DataFrame(dict(r=list(st.session_state.data["stats"].values()), theta=list(st.session_state.data["stats"].keys())))
        fig = go.Figure(data=go.Scatterpolar(r=df_radar['r'], theta=df_radar['theta'], fill='toself', line_color='#00d4ff'))
        fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 30])), paper_bgcolor="rgba(0,0,0,0)", font_color="white")
        st.plotly_chart(fig, use_container_width=True)
    with col_t:
        for s, v in st.session_state.data["stats"].items():
            st.write(f"**{s}:** {v}")
        st.metric("PODER TOTAL", st.session_state.data['lvl'] * sum(st.session_state.data["stats"].values()))

with tabs[1]: # MEDICINA
    st.subheader("🏥 INTERNATO GO")
    if st.button("ENFERMARIA / MATERNIDADE"): ganhar_xp(20, "SEN"); st.session_state.data["combos"]["med"]+=1; salvar()
    if st.button("PLANTÃO (12H)"): ganhar_xp(40, "VIT"); st.session_state.data["combos"]["med"]+=1; salvar()

with tabs[2]: # ACADEMIA
    st.subheader("💪 ACADEMIA (ABCD)")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("CONCLUIR TREINO"): ganhar_xp(30, "STR"); st.session_state.data["combos"]["gym"]+=1; salvar()
    with c2:
        if not st.session_state.data["descanso_usado"]:
            if st.button("🛡️ DESCANSO SEMANAL"):
                st.session_state.data["descanso_usado"] = True; st.session_state.data["stats"]["VIT"]+=1; salvar(); st.rerun()
    
    st.markdown("---")
    relato = st.text_area("🔮 RELATO AO ORÁCULO", placeholder="Fale sobre seu dia...")
    if st.button("ENVIAR AO SISTEMA"):
        if api_key and relato:
            prompt = f"Aja como o Sistema de Solo Leveling. Analise o relato do Interno de GO Guh Mota: '{relato}'. Retorne JSON: {{'xp': int, 'stat': str, 'msg': str}}"
            res = model.generate_content(prompt)
            match = re.search(r'\{.*\}', res.text, re.DOTALL)
            if match:
                js = json.loads(match.group())
                ganhar_xp(js['xp'], js['stat']); st.success(js['msg'])
                # No botão de enviar ao Oráculo, use este formato seguro:
if st.button("ENVIAR AO SISTEMA"):
    if model is None:
        st.error("O Oráculo não foi inicializado corretamente. Verifique sua Chave API.")
    elif not relato:
        st.warning("O Oráculo exige um relato para análise.")
    else:
        try:
            with st.spinner("Analisando esforço..."):
                prompt = f"Aja como o Sistema de Solo Leveling. Analise o relato do Guh Mota: '{relato}'. Retorne JSON: {{'xp': int, 'stat': str, 'msg': str}}"
                res = model.generate_content(prompt)
                # O restante do seu código de processamento JSON...
        except Exception as e:
            st.error(f"O Oráculo encontrou uma falha na conexão: {e}")

with tabs[3]:
    if st.session_state.data["penalidades"]:
        for p in st.session_state.data["penalidades"]: st.error(f"❌ {p}")
        if st.button("PAGUEI A DÍVIDA"): st.session_state.data["penalidades"] = []; salvar(); st.rerun()
    else: st.success("Caminho limpo, Monarca.")
