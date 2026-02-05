import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import json
import calendar
import time

# --- 1. CONFIGURACIÓN DEL SISTEMA ---
st.set_page_config(
    page_title="MISA OS | V4 Ultimate",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS "High Tech"
st.markdown("""
    <style>
    .main {background-color: #0E1117;}
    .stMetric {background-color: #1A1C24; border: 1px solid #333; padding: 15px; border-radius: 10px;}
    div[data-testid="stExpander"] {background-color: #1A1C24; border-radius: 10px;}
    </style>
    """, unsafe_allow_html=True)

# Archivos de persistencia
DB_FILE = 'movimientos_db.csv'
CONFIG_FILE = 'config_presupuesto.json'

# --- 2. MÓDULOS DE BACKEND ---

def init_system():
    # Inicializar DB si no existe
    if not os.path.exists(DB_FILE):
        df = pd.DataFrame(columns=["Fecha", "Concepto", "Categoria", "Monto", "Metodo"])
        df.to_csv(DB_FILE, index=False)
    
    # Inicializar Configuración si no existe
    if not os.path.exists(CONFIG_FILE):
        default_config = {
            "ingreso_neto": 14600,
            "presupuestos": {
                "Renta": 3200, "Transporte": 1800, "Supermercado": 2050,
                "Comidas Fuera": 1500, "Hobbies": 2500, "Servicios": 600, 
                "Social": 500, "Otros": 200
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

def update_db_full(df_edited):
    df_edited.to_csv(DB_FILE, index=False)

# Login System
def check_auth():
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False
    
    if not st.session_state['authenticated']:
        c1, c2, c3 = st.columns([1,2,1])
        with c2:
            st.title("🛡️ MISA SECURE LOGIN")
            password = st.text_input("Ingrese Clave de Acceso", type="password")
            if st.button("Acceder"):
                if password == "admin123": # <--- CAMBIA TU CONTRASEÑA AQUÍ
                    st.session_state['authenticated'] = True
                    st.success("Acceso Autorizado. Cargando módulos...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Acceso Denegado")
        return False
    return True

# --- 3. INICIO DE EJECUCIÓN ---
init_system()

if check_auth():
    # Cargar datos base
    config = load_config()
    presupuestos = config["presupuestos"]
    df_all = load_data()

    # --- 4. SIDEBAR: CENTRO DE MANDO ---
    with st.sidebar:
        st.title("🎛️ CONTROL CENTER")
        st.caption(f"v4.0 Ultimate | {datetime.now().strftime('%d-%m-%Y')}")
        
        # A. Filtros Temporales
        st.subheader("📅 Periodo")
        today = datetime.now()
        years = list(range(today.year, 2020, -1))
        selected_year = st.selectbox("Año", years)
        month_names = list(calendar.month_name)[1:]
        selected_month_name = st.selectbox("Mes", month_names, index=today.month-1)
        selected_month_idx = month_names.index(selected_month_name) + 1
        
        st.markdown("---")
        
        # B. Gestión de Presupuestos (Dinámica)
        with st.expander("⚙️ Configuración Financiera"):
            st.markdown("**Ingreso Neto Mensual**")
            new_income = st.number_input("Monto ($)", value=config["ingreso_neto"], step=100)
            if new_income != config["ingreso_neto"]:
                config["ingreso_neto"] = new_income
                save_config(config)
            
            st.markdown("**Límites por Categoría**")
            for cat, val in presupuestos.items():
                new_val = st.number_input(f"{cat}", value=val, key=f"limit_{cat}")
                if new_val != val:
                    presupuestos[cat] = new_val
                    config["presupuestos"] = presupuestos
                    save_config(config)
            
            # Agregar Categoría
            st.markdown("---")
            new_cat = st.text_input("Nueva Categoría")
            if st.button("➕ Agregar"):
                if new_cat and new_cat not in presupuestos:
                    presupuestos[new_cat] = 0
                    config["presupuestos"] = presupuestos
                    save_config(config)
                    st.rerun()

        if st.button("🔒 Cerrar Sesión"):
            st.session_state['authenticated'] = False
            st.rerun()

    # --- 5. LÓGICA DE FILTRADO Y CÁLCULOS ---
    # Filtrar DF por fecha seleccionada
    df_filtered = df_all[
        (df_all["Fecha"].dt.year == selected_year) & 
        (df_all["Fecha"].dt.month == selected_month_idx)
    ].copy()
    
    # Cálculos KPIs
    total_gastado = df_filtered["Monto"].sum()
    presupuesto_total = sum(presupuestos.values())
    disponible = presupuesto_total - total_gastado
    ahorro_teorico = config["ingreso_neto"] - total_gastado
    
    # Cálculos de Proyección (Forecasting V2)
    days_in_month = calendar.monthrange(selected_year, selected_month_idx)[1]
    # Determinar día actual para cálculo (si es mes pasado, usamos total de días)
    is_current_month = (today.year == selected_year and today.month == selected_month_idx)
    current_day_calc = today.day if is_current_month else days_in_month
    
    avg_daily_spend = total_gastado / current_day_calc if current_day_calc > 0 else 0
    projected_spend = avg_daily_spend * days_in_month

    # --- 6. INTERFAZ PRINCIPAL (TABS) ---
    st.title(f"🚀 MISA Financial OS | {selected_month_name} {selected_year}")
    
    # Pestañas Maestras
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Dashboard Ejecutivo", 
        "🧠 Insights & Inteligencia", 
        "📝 Centro de Operaciones", 
        "🗃️ Base de Datos Maestra"
    ])

    # --- TAB 1: EXECUTIVE DASHBOARD (Lo Visto + Hormiga) ---
    with tab1:
        # Fila 1: KPIs
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Presupuesto Global", f"${presupuesto_total:,.0f}")
        col2.metric("Gasto Actual", f"${total_gastado:,.0f}", delta=f"{(total_gastado/presupuesto_total)*100:.1f}% Uso", delta_color="inverse")
        col3.metric("Disponible Real", f"${disponible:,.0f}")
        col4.metric("Cashflow (vs Ingreso)", f"${ahorro_teorico:,.0f}", delta="Ahorro Potencial")
        
        st.markdown("---")
        
        # Fila 2: Gráficas Principales
        c_chart1, c_chart2 = st.columns([2, 1])
        
        with c_chart1:
            st.subheader("🆚 Análisis Presupuestal (Budget vs Real)")
            # Data preparation
            cats = list(presupuestos.keys())
            limits = list(presupuestos.values())
            reals = [df_filtered[df_filtered["Categoria"]==c]["Monto"].sum() for c in cats]
            
            # Advanced Plotly Chart
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=cats, y=reals, name="Gastado", 
                marker_color=['#EF553B' if r > l else '#00CC96' for r, l in zip(reals, limits)]
            ))
            fig.add_trace(go.Scatter(
                x=cats, y=limits, mode='markers', name='Límite',
                marker=dict(symbol='line-ew', color='white', size=30, line=dict(width=2))
            ))
            fig.update_layout(barmode='overlay', height=400, template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
            
        with c_chart2:
            st.subheader("💳 Por Método")
            if not df_filtered.empty:
                # DONA CORREGIDA
                fig_pie = px.pie(df_filtered, values="Monto", names="Metodo", hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Sin datos")

        # Fila 3: Radar Hormiga (Feature V3)
        st.markdown("### 🐜 Radar de Gastos Hormiga (< $150)")
        ant_expenses = df_filtered[df_filtered["Monto"] < 150]
        if not ant_expenses.empty:
            ant_total = ant_expenses["Monto"].sum()
            ant_count = len(ant_expenses)
            st.warning(f"⚠️ Alerta: Has realizado **{ant_count} compras pequeñas** que suman **${ant_total:,.2f}**. Estos gastos suelen pasar desapercibidos.")
            with st.expander("Ver detalle de gastos hormiga"):
                st.dataframe(ant_expenses[["Fecha", "Concepto", "Monto"]], use_container_width=True)
        else:
            st.success("✅ Zona limpia: No hay gastos hormiga significativos este mes.")

    # --- TAB 2: INSIGHTS AVANZADOS (Lo perdido de la V2 recuperado) ---
    with tab2:
        if df_filtered.empty:
            st.info("Necesitamos datos para generar inteligencia.")
        else:
            col_i1, col_i2 = st.columns(2)
            
            # A. Forecasting (V2 Feature)
            with col_i1:
                st.markdown("### 🔮 Proyección Financiera (AI Light)")
                st.write(f"Día actual de análisis: **{current_day_calc} de {days_in_month}**")
                
                delta_forecast = projected_spend - presupuesto_total
                color_forecast = "inverse" if projected_spend > presupuesto_total else "normal"
                
                st.metric(
                    "Gasto Proyectado al Cierre de Mes", 
                    f"${projected_spend:,.0f}", 
                    delta=f"${delta_forecast:,.0f} vs Presupuesto", 
                    delta_color=color_forecast
                )
                
                if projected_spend > config["ingreso_neto"]:
                    st.error("🚨 ALERTA CRÍTICA: La proyección indica que gastarás más de lo que ganas.")
                elif projected_spend > presupuesto_total:
                    st.warning("⚠️ CUIDADO: Vas encaminado a romper el presupuesto, aunque cubres con ingresos.")
                else:
                    st.success("✅ RITMO SALUDABLE: Vas excelente.")

            # B. Timeline Acumulativa (V2 Feature)
            with col_i2:
                st.markdown("### 📈 Velocidad de Gasto")
                daily_sum = df_filtered.groupby("Fecha")["Monto"].sum().reset_index()
                daily_sum = daily_sum.sort_values("Fecha")
                daily_sum["Acumulado"] = daily_sum["Monto"].cumsum()
                
                fig_line = px.line(daily_sum, x="Fecha", y="Acumulado", markers=True, title="Curva de Gasto Acumulado")
                fig_line.add_hline(y=presupuesto_total, line_dash="dash", line_color="red", annotation_text="Límite Presupuesto")
                st.plotly_chart(fig_line, use_container_width=True)
            
            st.markdown("---")
            
            # C. Treemap (V2 Feature - Recuperado)
            st.markdown("### 🗺️ Mapa Térmico de Categorías (Treemap)")
            st.caption("Tamaño = Monto Gastado. Úsalo para ver qué concepto específico consume más.")
            fig_tree = px.treemap(
                df_filtered, 
                path=[px.Constant("Total"), 'Categoria', 'Concepto'], 
                values='Monto',
                color='Monto',
                color_continuous_scale='RdBu_r'
            )
            st.plotly_chart(fig_tree, use_container_width=True)

    # --- TAB 3: OPERACIONES (Manual + Import) ---
    with tab3:
        c_op1, c_op2 = st.columns([1,1])
        
        # A. Registro Manual
        with c_op1:
            st.subheader("📝 Registro Manual")
            with st.form("manual_entry", clear_on_submit=True):
                f_date = st.date_input("Fecha", datetime.now())
                f_desc = st.text_input("Concepto (Ej. Uber, Cena)")
                f_cat = st.selectbox("Categoría", list(presupuestos.keys()))
                
                row_val = st.columns(2)
                f_amount = row_val[0].number_input("Monto ($)", min_value=0.0, step=10.0)
                f_method = row_val[1].selectbox("Método", ["BBVA", "Efectivo", "TDC", "Vales", "Otro"])
                
                if st.form_submit_button("💾 Guardar Gasto", use_container_width=True):
                    if f_amount > 0:
                        save_transaction(f_date, f_desc, f_cat, f_amount, f_method)
                        st.toast("✅ Gasto registrado con éxito!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("El monto debe ser mayor a 0")

        # B. Importador Masivo (V3 Feature)
        with c_op2:
            st.subheader("📂 Importador Bancario (CSV)")
            st.info("Sube un archivo CSV con columnas: Fecha, Concepto, Monto")
            uploaded_file = st.file_uploader("Seleccionar archivo", type=["csv"])
            
            if uploaded_file is not None:
                if st.button("Procesar Archivo"):
                    try:
                        df_imp = pd.read_csv(uploaded_file)
                        # Validación básica de columnas
                        required = {"Fecha", "Concepto", "Monto"}
                        if not required.issubset(df_imp.columns):
                            st.error(f"El CSV debe tener las columnas: {required}")
                        else:
                            # Completar datos faltantes
                            df_imp["Categoria"] = "Sin Clasificar"
                            df_imp["Metodo"] = "Importado"
                            # Convertir fecha
                            df_imp["Fecha"] = pd.to_datetime(df_imp["Fecha"])
                            
                            # Guardar
                            final_df = pd.concat([load_data(), df_imp], ignore_index=True)
                            update_db_full(final_df)
                            st.success(f"✅ Se importaron {len(df_imp)} registros exitosamente.")
                            time.sleep(1)
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error al leer CSV: {e}")

    # --- TAB 4: DATA MANAGER (CRUD V3) ---
    with tab4:
        st.subheader("🗄️ Gestión Total de Base de Datos")
        st.warning("⚠️ Edición Directa: Los cambios aquí son permanentes en el archivo CSV.")
        
        # Cargar TODA la data (sin filtro de mes) para poder corregir historial
        df_full_edit = load_data().sort_values("Fecha", ascending=False)
        
        edited_df = st.data_editor(
            df_full_edit,
            num_rows="dynamic",
            use_container_width=True,
            height=600
        )
        
        col_save, col_down = st.columns([1,4])
        with col_save:
            if st.button("💾 GUARDAR CAMBIOS", type="primary"):
                update_db_full(edited_df)
                st.success("Base de datos actualizada.")
                st.rerun()
        
        with col_down:
            csv_data = edited_df.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Descargar Backup", csv_data, "backup_finanzas.csv", "text/csv")
