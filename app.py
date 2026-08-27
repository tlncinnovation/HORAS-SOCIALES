import streamlit as st
import pandas as pd
import requests
import plotly.express as px

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Control de Horas Sociales",
    page_icon="🎓",
    layout="wide"
)

APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycby_fdhEzpVo861lJwPzsS-Nosl6MjCoNFOMLz4y3letpSmK12V8t_qq8XC_A1oO3g0/exec"

@st.cache_data(ttl=5)
def cargar_estudiantes():
    try:
        url = APPS_SCRIPT_URL + "?action=buscar_web&q="
        res = requests.get(url)
        datos = res.json()
        if "resultados" in datos:
            return pd.DataFrame(datos["resultados"])
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
        return pd.DataFrame()

def cargar_historial(uid):
    try:
        url = f"{APPS_SCRIPT_URL}?action=obtener_historial&uid={uid}"
        res = requests.get(url)
        datos = res.json()
        if "historial" in datos:
            return pd.DataFrame(datos["historial"])
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al cargar historial: {e}")
        return pd.DataFrame()

# Manejo de navegación / vista en sesión
if "estudiante_seleccionado" not in st.session_state:
    st.session_state["estudiante_seleccionado"] = None

# =========================================================
# VISTA 2: PERFIL Y DETALLES DEL ESTUDIANTE
# =========================================================
if st.session_state["estudiante_seleccionado"] is not None:
    est = st.session_state["estudiante_seleccionado"]
    
    if st.button("⬅️ Volver a la lista general"):
        st.session_state["estudiante_seleccionado"] = None
        st.rerun()

    st.title(f"👤 {est['nombre']}")
    st.subheader(f"Curso: {est['curso']} | UID: `{est['uid']}`")
    st.divider()

    horas_actuales = int(est["horas"])
    faltantes = max(0, 120 - horas_actuales)

    # --- FILA DE MÉTRICAS Y GRÁFICO CIRCULAR ---
    col_metrics, col_chart = st.columns([1, 1])

    with col_metrics:
        st.metric("Horas Completadas", f"{horas_actuales} / 120 hrs")
        st.metric("Horas Faltantes", f"{faltantes} hrs")
        porcentaje = min(100, int((horas_actuales / 120) * 100))
        
        if horas_actuales >= 120:
            st.success("🎉 ¡Meta Alcanzada! Estudiante Apto para Graduación.")
        else:
            st.info(f"Progreso Actual: {porcentaje}% completado.")

    with col_chart:
        # Gráfico Circular (Donut Chart)
        df_pie = pd.DataFrame({
            "Estado": ["Horas Completadas", "Horas Faltantes"],
            "Horas": [horas_actuales, faltantes]
        })
        fig_pie = px.pie(
            df_pie, 
            values="Horas", 
            names="Estado", 
            hole=0.5,
            color="Estado",
            color_discrete_map={"Horas Completadas": "#2ecc71", "Horas Faltantes": "#e74c3c"},
            title="Porcentaje de Avance (120h)"
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    st.divider()

    # --- SECCIÓN DE HISTORIAL Y GRÁFICO DE BARRAS POR DÍA ---
    st.subheader("📊 Historial de Registros y Asistencia")
    df_hist = cargar_historial(est["uid"])

    if not df_hist.empty:
        # Formatear fechas para gráfico de barras por día
        df_hist["fecha_dt"] = pd.to_datetime(df_hist["fecha"])
        df_hist["dia"] = df_hist["fecha_dt"].dt.strftime('%Y-%m-%d')
        
        # Agrupar horas por día
        df_por_dia = df_hist.groupby("dia")["horas"].sum().reset_index()

        # Gráfico de Barras de Horas por Día
        fig_bar = px.bar(
            df_por_dia, 
            x="dia", 
            y="horas", 
            labels={"dia": "Fecha", "horas": "Horas Registradas"},
            title="Horas Sumadas por Día",
            color_discrete_sequence=["#3498db"]
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        # Tabla de Asistencia / Historial
        st.markdown("### 📋 Tabla de Asistencia")
        df_tabla = df_hist[["fechaTxt", "horas", "profesor"]].rename(columns={
            "fechaTxt": "Fecha y Hora",
            "horas": "Horas Sumadas",
            "profesor": "Autorizado Por (Profesor)"
        })
        st.dataframe(df_tabla, use_container_width=True)
    else:
        st.warning("Este estudiante aún no tiene registros detallados en el Historial (se actualizarán al pasar la tarjeta nuevamente).")

# =========================================================
# VISTA 1: LISTA GENERAL DE ESTUDIANTES
# =========================================================
else:
    st.title("🎓 Sistema de Control de Horas Sociales (120h)")
    st.markdown("Consulta en tiempo real el avance de horas sociales de los estudiantes.")

    df = cargar_estudiantes()

    if not df.empty:
        st.sidebar.header("🔍 Filtros de Búsqueda")
        busqueda = st.sidebar.text_input("Buscar por Nombre, UID o Curso:")
        
        cursos_disponibles = ["Todos"] + sorted(list(df["curso"].unique()))
        curso_seleccionado = st.sidebar.selectbox("Filtrar por Curso:", cursos_disponibles)
        
        if curso_seleccionado != "Todos":
            df = df[df["curso"] == curso_seleccionado]

        if busqueda:
            df = df[
                df["nombre"].str.contains(busqueda, case=False, na=False) |
                df["uid"].astype(str).str.contains(busqueda, case=False, na=False) |
                df["curso"].str.contains(busqueda, case=False, na=False)
            ]

        # Métricas principales
        col1, col2, col3 = st.columns(3)
        col1.metric("Estudiantes Registrados", len(df))
        col2.metric("Graduados (120h)", len(df[df["horas"] >= 120]))
        prom = int(df["horas"].mean()) if len(df) > 0 else 0
        col3.metric("Promedio de Horas", f"{prom} hrs")

        st.divider()
        st.subheader("📋 Lista de Estudiantes")

        for index, row in df.iterrows():
            nombre = row["nombre"]
            curso = row["curso"]
            horas = int(row["horas"])
            porcentaje = min(100, int((horas / 120) * 100))
            
            with st.container():
                col_info, col_btn = st.columns([4, 1])
                
                with col_info:
                    st.markdown(f"### {nombre} `Curso: {curso}`")
                    st.progress(porcentaje / 100)
                    st.caption(f"**{horas}** / 120 hrs ({porcentaje}%) | ÚLTIMA MARCA: {row.get('ultimaFecha', 'N/A')}")
                
                with col_btn:
                    st.write("") # Espaciador
                    if st.button("👁️ Ver Perfil", key=f"btn_{row['uid']}"):
                        st.session_state["estudiante_seleccionado"] = row
                        st.rerun()
                
                st.divider()
    else:
        st.info("No se encontraron estudiantes o la base de datos está vacía.")
