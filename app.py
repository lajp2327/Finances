import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import json
import calendar
import time
import hashlib
import google.generativeai as genai

# --- 1. CONFIGURACIÓN E INTEGRACIÓN API ---
st.set_page_config(
    page_title="TITAN Finance OS | AI Powered",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- CLAVE API ---
GOOGLE_API_KEY = "AIzaSyB9_HSrUTq9SacuCS5iaBh87VNLwLu9OLs"

# --- 2. MOTOR DE IA (CONFIGURACIÓN ROBUSTA) ---
def configure_ai():
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        
        available_models = []
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append(m.name)
        except:
            pass 
        
        target_model = "models/gemini-pro"
        for m in available_models:
            if "gemini-2.5-flash" in m:
                target_model = m
                break
            elif "gemini-2.0-flash" in m:
                target_model = m
                break
            elif "gemini-1.5-flash" in m:
                target_model = m
        
        print(f"Modelo seleccionado: {target_model}")
        return genai.GenerativeModel(target_model), target_model, True

    except Exception as e:
        return None, str(e), False

# Inicializamos IA
model, model_name, AI_AVAILABLE = configure_ai()

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .main {background-color: #0E1117;}
    div[data-testid="metric-container"] {
        background-color: #1A1C24; border: 1px solid #333; padding: 10px; border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CONSTANTES ---
DB_FILE = 'titan_transactions.csv'
USERS_FILE = 'titan_users.json'

# --- 3. CLASE TITAN AI ---
class TitanGemini:
    def __init__(self, df, available_categories):
        self.df = df
        self.categories = available_categories

    def predict_transaction(self, concept):
        """Categorización automática"""
        if not AI_AVAILABLE:
            return "Otros", "General"
        
        # OJO: Aquí usamos doble llave {{ }} para que Python no se confunda
        prompt = f"""
        Actúa como contador. Tengo un gasto: '{concept}'.
        Categorías disponibles: {', '.join(self.categories)}.
        
        Tarea:
        1. Elige la mejor categoría de MI lista.
        2. Crea una Subcategoría corta (1-2 palabras).
        
        Responde SOLO JSON puro:
        {{"categoria": "Alimentos", "subcategoria": "Restaurante"}}
        """
        try:
            response = model.generate_content(prompt)
            clean_json = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)
            return data.get("categoria", "Otros"), data.get("subcategoria", "General")
        except:
            return "Otros", "AI_Error"

    def ask_data_analyst(self, user_question):
        """Analista financiero"""
        if not AI_AVAILABLE: return "⚠️ IA desconectada."
        if self.df.empty: return "No hay datos para analizar."

        data_context = self.df[["Fecha", "Concepto", "Categoria", "Monto", "Metodo"]].to_csv(index=False)
        
        # AQUÍ ES DONDE SOLÍA FALLAR: Aseguramos el cierre de comillas
        prompt = f"""
        Eres TITAN, analista financiero.
        Datos CSV:
        {data_context}
        
        Pregunta usuario: "{user_question}"
        
        Responde breve, directo y en Markdown.
        """
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error: {e}"

# --- 4. GESTIÓN DE USUARIOS Y DATOS ---
def init_system():
    # Inicializar Base de Datos
    if not os.path.exists(DB_FILE):
        df = pd.DataFrame(columns=["User", "Fecha", "Concepto", "Categoria", "Subcategoria", "Monto", "Metodo"])
        df.to_csv(DB_FILE, index=False)
    
    # Inicializar Usuarios (Esta es la línea que daba error antes)
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            json.dump({}, f)

def load_users():
    with open(USERS_FILE, 'r') as f: return json.load(f)

def save_user(username, password, config):
    users = load_users()
    users[username] = {
        "password": hashlib.sha256(password.encode()).hexdigest(),
        "config": config
    }
    with open(USERS_FILE, 'w') as f: json.dump(users, f)

def authenticate(username, password):
    users = load_users()
    if username in users:
        hashed_input = hashlib.sha256(password.encode()).hexdigest()
        if users[username]["password"] == hashed_input:
            return users[username]["config"]
    return None

def update_user_config(username, new_config):
    users = load_users()
    if username in users:
        users[username]["config"] = new_config
        with open(USERS_FILE, 'w') as f: json.dump(users, f)

# --- 5. DATA MANAGER BLINDADO ---
def load_transactions(username):
    expected_cols = ["User", "Fecha", "Concepto", "Categoria", "Subcategoria", "Monto", "Metodo"]
    try:
        df = pd.read_csv(DB_FILE)
        for col in expected_cols:
            if col not in df.columns: df[col] = None
    except:
        df = pd.DataFrame(columns=expected_cols)

    # Convertir fecha sin errores
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors='coerce')

    if "User" in df.columns:
        return df[df["User"] == username].copy()
    return pd.DataFrame(columns=expected_cols)

def save_transaction(username, fecha, concepto, cat, subcat, monto, metodo):
    df = pd.read_csv(DB_FILE)
    new_row = pd.DataFrame({
        "User": [username],
        "Fecha": [pd.to_datetime(fecha)],
        "Concepto": [concepto],
        "Categoria": [cat],
        "Subcategoria": [subcat],
        "Monto": [float(monto)],
        "Metodo": [metodo]
    })
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(DB_FILE, index=False)

# --- 6. INTERFAZ DE LOGIN ---
def login_page():
    c1, c2, c3 = st.columns([1,1.5,1])
    with c2:
        st.markdown("<h1 style='text-align: center;'>🦅 TITAN | AI Powered</h1>", unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["Ingresar", "Registrarse"])
        
        with tab1:
            u = st.text_input("Usuario")
            p = st.text_input("Password", type="password")
            if st.button("Entrar", type="primary", use_container_width=True):
                cfg = authenticate(u, p)
                if cfg:
                    st.session_state['user'] = u
                    st.session_state['config'] = cfg
                    st.rerun()
                else:
                    st.error("Credenciales inválidas")
        
        with tab2:
            nu = st.text_input("Nuevo Usuario")
            np = st.text_input("Nueva Contraseña", type="password")
            if st.button("Crear Cuenta", use_container_width=True):
                users = load_users()
                if nu in users:
                    st.error("Usuario existente")
                elif nu and np:
                    def_cfg = {"ingreso_neto": 15000, "presupuestos": {"Vivienda": 4000, "Alimentos": 3000, "Transporte": 1000, "Otros": 1000}}
                    save_user(nu, np, def_cfg)
                    st.success("Creado. Inicia sesión.")

# --- 7. APP PRINCIPAL ---
def main_app():
    user = st.session_state['user']
    config = st.session_state['config']
    
    # --- SIDEBAR ---
    with st.sidebar:
        st.title(f"👤 {user.upper()}")
        if AI_AVAILABLE:
            st.success(f"🟢 Conectado: {model_name.replace('models/', '')}")
        else:
            st.error(f"🔴 Error AI")
            
        today = datetime.now()
        y_opt = list(range(today.year, 2023, -1))
        sel_year = st.selectbox("Año", y_opt)
        m_opt = list(calendar.month_name)[1:]
        sel_month = st.selectbox("Mes", m_opt, index=today.month-1)
        month_idx = m_opt.index(sel_month) + 1
        
        with st.expander("⚙️ Presupuestos"):
            new_inc = st.number_input("Ingreso", value=config.get("ingreso_neto", 0))
            if new_inc != config.get("ingreso_neto"):
                config["ingreso_neto"] = new_inc
                update_user_config(user, config)
            
            pres = config.get("presupuestos", {})
            to_del = []
            for k, v in pres.items():
                c1, c2 = st.columns([3,1])
                nv = c1.number_input(k, value=v, key=f"b_{k}")
                if c2.button("✖️", key=f"d_{k}"): to_del.append(k)
                if nv != v: pres[k] = nv
            
            for k in to_del: del pres[k]
            
            st.markdown("---")
            nc = st.text_input("Nueva Categoría")
            if st.button("➕ Agregar"):
                if nc: 
                    pres[nc] = 0
                    config["presupuestos"] = pres
                    update_user_config(user, config)
                    st.rerun()

        if st.button("Cerrar Sesión"):
            del st.session_state['user']
            st.rerun()

    # --- CARGA DE DATOS ---
    df_all = load_transactions(user)
    
    if not df_all.empty:
        df = df_all[
            (df_all["Fecha"].dt.year == sel_year) & 
            (df_all["Fecha"].dt.month == month_idx)
        ].copy()
    else:
        df = df_all.copy()

    # --- DASHBOARD UI ---
    st.markdown(f"## 📊 TITAN Dashboard: {sel_month} {sel_year}")
    
    tabs = st.tabs(["👁️ Visión Global", "🤖 Gemini Chat", "⚡ Smart Add", "🔬 Insights", "🗃️ Data"])
    
    # TAB 1: VISION
    with tabs[0]:
        tot = df["Monto"].sum()
        bud = sum(config["presupuestos"].values())
        
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Ingreso", f"${config['ingreso_neto']:,.0f}")
        k2.metric("Gasto Total", f"${tot:,.0f}", delta=f"{(tot/bud)*100:.1f}% Uso" if bud>0 else "0%")
        k3.metric("Disponible", f"${bud-tot:,.0f}")
        k4.metric("Ahorro Real", f"${config['ingreso_neto']-tot:,.0f}", delta="Cashflow")
        
        g1, g2 = st.columns([2,1])
        with g1:
            st.subheader("Budget vs Realidad")
            b_df = pd.DataFrame(list(config["presupuestos"].items()), columns=["Categoria", "Limite"])
            r_df = df.groupby("Categoria")["Monto"].sum().reset_index()
            m_df = pd.merge(b_df, r_df, on="Categoria", how="left").fillna(0)
            
            fig = go.Figure()
            fig.add_trace(go.Bar(x=m_df["Categoria"], y=m_df["Limite"], name="Límite", marker_color='rgba(255,255,255,0.1)'))
            fig.add_trace(go.Bar(x=m_df["Categoria"], y=m_df["Monto"], name="Gastado", marker_color='#00CC96'))
            fig.update_layout(barmode='overlay', template="plotly_dark", height=350)
            st.plotly_chart(fig, use_container_width=True)
            
        with g2:
            st.subheader("Distribución Solar")
            if not df.empty:
                fig_s = px.sunburst(df, path=['Categoria', 'Subcategoria'], values='Monto', color='Categoria')
                st.plotly_chart(fig_s, use_container_width=True)
            else:
                st.info("Sin datos para graficar")

    # TAB 2: GEMINI CHAT
    with tabs[1]:
        st.subheader("💬 Habla con TITAN (Powered by Google Gemini)")
        st.info("La IA tiene acceso a tus transacciones visibles. Pregunta libremente.")
        
        if "messages" not in st.session_state:
            st.session_state.messages = []

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("Ej: ¿En qué estoy gastando más?"):
            st.chat_message("user").markdown(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            ai = TitanGemini(df, list(config["presupuestos"].keys()))
            with st.spinner("Gemini analizando..."):
                response = ai.ask_data_analyst(prompt)
            
            with st.chat_message("assistant"):
                st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

    # TAB 3: SMART ADD
    with tabs[2]:
        st.subheader("⚡ Registro Inteligente")
        with st.form("add_smart"):
            col_a, col_b = st.columns([2,1])
            desc = col_a.text_input("Concepto (Ej. 'Cena en Mochomos')")
            date_v = col_b.date_input("Fecha", datetime.now())
            
            st.caption("✨ Gemini clasificará automáticamente la categoría y subcategoría.")
            
            c_v1, c_v2, c_v3 = st.columns(3)
            monto = c_v1.number_input("Monto", min_value=0.0, step=10.0)
            metodo = c_v2.selectbox("Método", ["TDC", "Débito", "Efectivo", "Transferencia"])
            manual_cat = c_v3.selectbox("Forzar Categoría", ["Auto (IA)"] + list(config["presupuestos"].keys()))
            
            if st.form_submit_button("Guardar Transacción", use_container_width=True):
                if desc and monto > 0:
                    final_cat = manual_cat
                    final_sub = "IA_Generated"
                    
                    if manual_cat == "Auto (IA)":
                        with st.status("🧠 Gemini clasificando..."):
                            bot = TitanGemini(None, list(config["presupuestos"].keys()))
                            final_cat, final_sub = bot.predict_transaction(desc)
                            st.write(f"Clasificado: **{final_cat}** > *{final_sub}*")
                    else:
                        final_cat = manual_cat
                        final_sub = "Manual"
                        
                    save_transaction(user, date_v, desc, final_cat, final_sub, monto, metodo)
                    st.success("Registrado!")
                    time.sleep(1)
                    st.rerun()

    # TAB 4: INSIGHTS
    with tabs[3]:
        st.subheader("🔬 Deep Insights")
        if not df.empty:
            c_i1, c_i2 = st.columns(2)
            with c_i1:
                st.markdown("**Gastos por Día**")
                d_g = df.groupby("Fecha")["Monto"].sum().reset_index()
                fig_l = px.line(d_g, x="Fecha", y="Monto", markers=True)
                st.plotly_chart(fig_l, use_container_width=True)
            with c_i2:
                st.markdown("**Top Gastos**")
                st.dataframe(df.nlargest(5, "Monto")[["Concepto", "Categoria", "Monto"]], use_container_width=True)
        else:
            st.info("Necesitas registrar gastos primero.")

    # TAB 5: DATA
    with tabs[4]:
        st.subheader("Editor de Base de Datos")
        edited = st.data_editor(df_all, num_rows="dynamic", use_container_width=True)
        if st.button("Guardar Cambios BD"):
            edited.to_csv(DB_FILE, index=False)
            st.success("Guardado")

# --- EJECUCIÓN ---
init_system()
if 'user' not in st.session_state:
    login_page()
else:
    main_app()
