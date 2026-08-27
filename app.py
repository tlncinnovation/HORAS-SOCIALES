import streamlit as st
import pandas as pd
import requests

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Control de Horas Sociales",
    page_icon="🎓",
    layout="wide"
)

# PEGA AQUÍ LA URL DE TU WEB APP DE GOOGLE APPS SCRIPT
# (La misma URL que empieza con https://script.google.com/macros/s/.../exec)
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycby_fdhEzpVo861lJwPzsS-Nosl6MjCoNFOMLz4y3letpSmK12V8t_qq8XC_A1oO3g0/exec"

@st.cache_data(ttl=5) # Refresca datos cada 5 segundos
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

# --- TÍTULO PRINCIPAL ---
st.title("🎓 Sistema de Control de Horas Sociales (120h)")
st.markdown("Consulta en tiempo real el avance de horas sociales de los estudiantes.")

df = cargar_estudiantes()

if not df.empty:
    # --- BARRA LATERAL (FILTROS) ---
    st.sidebar.header("🔍 Filtros de Búsqueda")
    
    busqueda = st.sidebar.text_input("Buscar por Nombre, UID o Curso:")
    
    # Filtro dinámico por Cursos (pestañas)
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

    # --- MÉTRICAS ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Estudiantes Registrados", len(df))
    
    graduados = len(df[df["horas"] >= 120])
    col2.metric("Estudiantes Graduados (120h)", graduados)
    
    promedio = int(df["horas"].mean()) if len(df) > 0 else 0
    col3.metric("Promedio de Horas", f"{promedio} hrs")

    st.divider()

    # --- LISTA DE ESTUDIANTES ---
    st.subheader("📋 Lista de Progreso por Estudiante")

    for index, row in df.iterrows():
        nombre = row["nombre"]
        curso = row["curso"]
        horas = int(row["horas"])
        porcentaje = min(100, int((horas / 120) * 100))
        faltantes = max(0, 120 - horas)
        
        with st.container():
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.markdown(f"### {nombre}  `Curso: {curso}`")
                st.progress(porcentaje / 100)
                st.caption(f"**{horas}** de 120 horas completadas ({porcentaje}%) — **Faltan:** {faltantes} hrs | **Última marca:** {row.get('ultimaFecha', 'N/A')}")
            
            with col_b:
                if horas >= 120:
                    st.success("✅ COMPLETADO")
                else:
                    st.warning("⏳ EN PROGRESO")
            st.divider()

else:
    st.info("No se encontraron estudiantes o la base de datos está vacía.")
