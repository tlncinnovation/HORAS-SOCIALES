import streamlit as st
import pandas as pd

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Control de Horas Sociales",
    page_icon="🎓",
    layout="wide"
)

# --- PEGA AQUÍ TU ENLACE PÚBLICO CSV DE GOOGLE SHEETS ---
# (Si no usas la publicación CSV, puedes colocar la URL pública de la hoja)
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/TU_ID_DE_HOJA_AQUI/export?format=csv"

@st.cache_data(ttl=10) # Actualiza datos cada 10 segundos
def cargar_datos():
    try:
        # Lee los datos directamente desde Google Sheets
        df = pd.read_csv(GOOGLE_SHEET_URL)
        return df
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
        return pd.DataFrame()

# --- TÍTULO PRINCIPAL ---
st.title("🎓 Sistema de Control de Horas Sociales (120h)")
st.markdown("Consulta en tiempo real el avance de horas sociales de los estudiantes.")

df = cargar_datos()

if not df.empty:
    # Asegurar columnas necesarias
    cols_requeridas = ["UID Tarjeta", "Nombre Completo", "Horas Acumuladas"]
    
    # --- BARRA LATERAL (FILTROS) ---
    st.sidebar.header("🔍 Filtros de Búsqueda")
    
    # Buscador por nombre o UID
    busqueda = st.sidebar.text_input("Buscar por Nombre o UID:")
    
    # Filtro por Curso (si la columna existe en el CSV)
    if "Curso" in df.columns:
        cursos = ["Todos"] + list(df["Curso"].unique())
        curso_seleccionado = st.sidebar.selectbox("Seleccionar Curso:", cursos)
        if curso_seleccionado != "Todos":
            df = df[df["Curso"] == curso_seleccionado]

    # Aplicar búsqueda
    if busqueda:
        df = df[
            df["Nombre Completo"].str.contains(busqueda, case=False, na=False) |
            df["UID Tarjeta"].astype(str).str.contains(busqueda, case=False, na=False)
        ]

    # --- METRICAS GENERALES ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Estudiantes Registrados", len(df))
    
    total_completados = len(df[df["Horas Acumuladas"] >= 120]) if "Horas Acumuladas" in df.columns else 0
    col2.metric("Estudiantes Graduados (120h)", total_completados)
    
    promedio_horas = int(df["Horas Acumuladas"].mean()) if "Horas Acumuladas" in df.columns else 0
    col3.metric("Promedio de Horas", f"{promedio_horas} hrs")

    st.divider()

    # --- LISTA DE ESTUDIANTES Y BARRAS DE PROGRESO ---
    st.subheader("📋 Lista de Progreso")

    for index, row in df.iterrows():
        nombre = row.get("Nombre Completo", "Sin Nombre")
        horas = int(row.get("Horas Acumuladas", 0))
        porcentaje = min(100, int((horas / 120) * 100))
        faltantes = max(0, 120 - horas)
        
        with st.container():
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.markdown(f"### {nombre}")
                st.progress(porcentaje / 100)
                st.caption(f"**{horas}** de 120 horas completadas ({porcentaje}%) — **Faltan:** {faltantes} hrs")
            
            with col_b:
                if horas >= 120:
                    st.success("✅ COMPLETADO")
                else:
                    st.warning("⏳ EN PROGRESO")
            st.divider()

else:
    st.info("Pasa una tarjeta por el lector para generar los primeros registros en la base de datos.")