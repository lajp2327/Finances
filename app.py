import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import json
import calendar
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="MISA OS | V3",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- ESTILOS CSS "CYBERPUNK/PRO" ---
st.markdown("""
    <style>
    .main {background-color: #0E1117;}
    .stMetric {background-color: #1E1E1E; padding: 15px; border-radius: 10px; border: 1px solid #333;}
    .stButton>button {width: 100%; border-radius: 5px; font-weight: bold;}
    div[data-testid="stExpander"] details summary {font-weight: bold; font-size: 1.1em;}
    </style>
    """, unsafe_allow_html=True)

# --- ARCHIVOS DE PERSISTENCIA ---
DB_FILE = 'movimientos_db.csv'
CONFIG_FILE = 'config_presupuesto.json'

# --- 1. MÓDULO DE SEGURIDAD (Simulado) ---
def check_password():
    """Retorna True si el usuario está logueado correctamente"""
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.markdown("## 🔒 MISA Secure Access")
            password = st.text_input("Ingrese Credencial de Acceso", type="password")
            if st.button("Autenticar"):
                # CONTRASEÑA: admin123 (Puedes cambiarla aquí)
                if password == "admin123":
                    st.session_state['logged_in'] = True
                    st.success("Acceso Concedido")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("⛔ Acceso Denegado")
        return False
    return True

# --- 2. GESTIÓN DE DATOS ---
def init_files():
    if not os.path.exists(DB_FILE):
        df = pd.DataFrame(columns=["Fecha", "Concepto", "Categoria", "Monto", "Metodo"])
        df.to_csv(DB_FILE, index=False)
    
    if not os.path.exists(CONFIG_FILE):
        # Configuración inicial por defecto
        default_config = {
            "ingreso_neto": 14600,
            "presupuestos": {
                "Renta": 3200, "Alimentos": 2050, "Transporte": 1800,
                "Diversion": 1500, "Servicios": 600, "Otros": 500
            }
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(default_config, f)

def load_data():
    df = pd.read_csv(DB_FILE)
    df["Fecha"] = pd.to_datetime(df["Fecha"])
    return df

def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def save_config(config_data):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_data, f)

def save_transaction(fecha, concepto, categoria, monto, metodo):
    df = load_data()
    new_row = pd.DataFrame({
        "Fecha": [pd.to_datetime(fecha)],
        "Concepto": [concepto],
        "Categoria": [categoria],
        "Monto": [float(monto)],
        "Metodo": [metodo]
    })
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(DB_FILE, index=False)

def update_db(df_edited):
    df_edited.to_csv(DB_FILE, index=False)

# --- 3. MÓDULO IMPORTADOR (IA Simple) ---
def process_uploaded_file(uploaded_file):
    try:
        # Intenta leer CSV (adaptar según tu banco, ejemplo genérico BBVA)
        df_bank = pd.read_csv(uploaded_file)
        
        # Mapeo simple de columnas (Esto deberías ajustarlo a tu CSV real)
        # Asumimos que el CSV tiene columnas parecidas a: 'Date', 'Description', 'Amount'
        # Si no, creamos un df dummy para el ejemplo
        if 'Fecha' not in df_bank.columns:
             st.error("El CSV debe tener columna 'Fecha'. Formato esperado: Fecha, Concepto, Monto")
             return

        # Normalización
        df_bank["Categoria"] = "Sin Clasificar" # Asignar default
        df_bank["Metodo"] = "Importado"
        
        # Guardar
        current_df = load_data()
        final_df = pd.concat([current_df, df_bank], ignore_index=True)
        final_df.to_csv(DB_FILE, index=False)
        st.success(f"✅ Se importaron {len(df_bank)} movimientos exitosamente.")
    except Exception as e:
        st.error(f"Error al procesar archivo: {e}")

# --- EJECUCIÓN PRINCIPAL ---
init_files()

if check_password():
    # Cargar Configuración Dinámica
    config = load_config()
    presupuestos = config["presupuestos"]
    
    # --- SIDEBAR AVANZADO ---
    with st.sidebar:
        st.title("🎛️ SYSTEM CONTROL")
        st.image("https://cdn-icons-png.flaticon.com/512/9672/9672132.png", width=50) # Icono Tech
        
        st.markdown("### 📅 Filtros")
        today = datetime.now()
        y_opt = list(range(today.year, 2020, -1))
        year_sel = st.selectbox("Año", y_opt)
        month_list = list(calendar.month_name)[1:]
        month_sel = st.selectbox("Mes", month_list, index=today.month-1)
        month_idx = month_list.index(month_sel) + 1
        
        st.markdown("---")
        with st.expander("⚙️ Ajustes de Presupuesto"):
            new_income = st.number_input("Ingreso Neto", value=config["ingreso_neto"])
            if new_income != config["ingreso_neto"]:
                config["ingreso_neto"] = new_income
                save_config(config)
            
            st.write("Límites por Categoría:")
            for cat, val in presupuestos.items():
                new_val = st.number_input(f"{cat}", value=val, key=f"bud_{cat}")
                if new_val != val:
                    presupuestos[cat] = new_val
                    config["presupuestos"] = presupuestos
                    save_config(config)
            
            # Añadir nueva categoría
            new_cat_name = st.text_input("Nueva Categoría")
            if st.button("➕ Crear Categoría"):
                if new_cat_name and new_cat_name not in presupuestos:
                    presupuestos[new_cat_name] = 0
                    config["presupuestos"] = presupuestos
                    save_config(config)
                    st.rerun()

        if st.button("🔒 Cerrar Sesión"):
            st.session_state['logged_in'] = False
            st.rerun()

    # --- DATOS FILTRADOS ---
    df_all = load_data()
    df = df_all[(df_all["Fecha"].dt.year == year_sel) & (df_all["Fecha"].dt.month == month_idx)].copy()
    
    # --- DASHBOARD UI ---
    st.title(f"MISA COMMAND | {month_sel.upper()} {year_sel}")
    
    # KPIs SUPERIOR
    total_gasto = df["Monto"].sum()
    total_budget = sum(presupuestos.values())
    
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Ingreso", f"${config['ingreso_neto']:,.0f}")
    kpi2.metric("Gastado", f"${total_gasto:,.0f}", delta=f"{total_budget - total_gasto:,.0f} Restante")
    
    # Semáforo inteligente
    percent_spent = (total_gasto / total_budget) * 100 if total_budget > 0 else 0
    state_color = "normal" if percent_spent < 80 else ("off" if percent_spent < 100 else "inverse")
    kpi3.metric("% Ejecución", f"{percent_spent:.1f}%", delta_color=state_color)
    
    # Cashflow Forecast
    days_in_month = calendar.monthrange(year_sel, month_idx)[1]
    current_day = min(today.day, days_in_month) if (today.year == year_sel and today.month == month_idx) else days_in_month
    projection = (total_gasto / current_day) * days_in_month if current_day > 0 else 0
    kpi4.metric("Proyección Fin de Mes", f"${projection:,.0f}", help="Basado en gasto diario promedio")

    # TABS PRINCIPALES
    tab_dash, tab_add, tab_imp, tab_data = st.tabs(["📊 Visión General", "📝 Registro Manual", "📂 Importar Banco", "💾 Base de Datos"])

    with tab_dash:
        c1, c2 = st.columns([2, 1])
        
        with c1:
            st.subheader("Análisis de Desviación")
            # Preparar datos comparativos
            cats = list(presupuestos.keys())
            vals_budget = list(presupuestos.values())
            vals_real = [df[df["Categoria"]==c]["Monto"].sum() for c in cats]
            
            fig = go.Figure()
            fig.add_trace(go.Bar(x=cats, y=vals_real, name='Real', marker_color='#00CC96'))
            fig.add_trace(go.Bar(x=cats, y=vals_budget, name='Presupuesto', marker_color='#19D3F3', opacity=0.3))
            fig.update_layout(barmode='overlay', height=400, margin=dict(t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)

        with c2:
            st.subheader("Distribución")
            if not df.empty:
                # CORRECCIÓN DE DONA AQUI
                fig_pie = px.pie(df, values='Monto', names='Categoria', hole=0.6, color_discrete_sequence=px.colors.qualitative.Prism)
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Sin datos para graficar")

        # Gasto Hormiga Detector
        st.markdown("### 🐜 Radar de Gastos Hormiga (< $100)")
        hormiga_df = df[df["Monto"] < 100]
        if not hormiga_df.empty:
            hormiga_total = hormiga_df["Monto"].sum()
            st.warning(f"Has gastado **${hormiga_total:,.0f}** en {len(hormiga_df)} compras pequeñas. ¡Ojo ahí!")
        else:
            st.success("¡Excelente! No se detectan gastos hormiga significativos.")

    with tab_add:
        st.markdown("#### Nuevo Movimiento")
        with st.form("add_form", clear_on_submit=True):
            col_f1, col_f2, col_f3 = st.columns(3)
            fecha = col_f1.date_input("Fecha", datetime.now())
            monto = col_f2.number_input("Monto", min_value=0.0, step=10.0)
            metodo = col_f3.selectbox("Método", ["BBVA", "Efectivo", "TDC", "Vales"])
            
            col_f4, col_f5 = st.columns([2,1])
            desc = col_f4.text_input("Concepto")
            cat = col_f5.selectbox("Categoría", list(presupuestos.keys()))
            
            if st.form_submit_button("🚀 Registrar Transacción", use_container_width=True):
                save_transaction(fecha, desc, cat, monto, metodo)
                st.success("Registrado")
                time.sleep(0.5)
                st.rerun()

    with tab_imp:
        st.markdown("#### 🤖 Importador Inteligente (CSV)")
        st.info("Sube un CSV con columnas: Fecha, Concepto, Monto")
        uploaded = st.file_uploader("Arrastra tu estado de cuenta aquí", type="csv")
        if uploaded:
            if st.button("Procesar Archivo"):
                process_uploaded_file(uploaded)

    with tab_data:
        st.markdown("#### 🛠️ Editor Maestro")
        edited_df = st.data_editor(df_all, num_rows="dynamic", use_container_width=True, height=500)
        if st.button("💾 Guardar Cambios Masivos"):
            update_db(edited_df)
            st.success("Base de datos actualizada")
            st.rerun()
