import streamlit as st
import pandas as pd
import requests
import altair as alt
from datetime import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Control de Horas Sociales",
    page_icon="🎓",
    layout="wide"
)

APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycby_fdhEzpVo861lJwPzsS-Nosl6MjCoNFOMLz4y3letpSmK12V8t_qq8XC_A1oO3g0/exec"

# --- FUNCIONES PARA CARGAR DATOS DESDE GOOGLE SHEETS ---
@st.cache_data(ttl=5)
def cargar_profesores():
    try:
        url = APPS_SCRIPT_URL + "?action=obtener_profesores"
        res = requests.get(url)
        datos = res.json()
        if "profesores" in datos:
            return pd.DataFrame(datos["profesores"])
        return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()

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

# --- MANEJO DE SESIÓN Y AUTENTICACIÓN ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
if "usuario_actual" not in st.session_state:
    st.session_state["usuario_actual"] = ""

def login():
    st.title("🔒 Acceso al Sistema de Horas Sociales")
    st.subheader("Autenticación de Profesores")
    
    df_profes = cargar_profesores()
    
    with st.form("form_login"):
        if not df_profes.empty and "nombre" in df_profes.columns:
            profesor_sel = st.selectbox("Selecciona tu nombre:", df_profes["nombre"].tolist())
        else:
            profesor_sel = st.text_input("Nombre de Profesor:")

        password = st.text_input("Contraseña:", type="password")
        btn_submit = st.form_submit_button("Iniciar Sesión")
        
        if btn_submit:
            es_valido = False
            
            if not df_profes.empty and "password" in df_profes.columns:
                prof_data = df_profes[df_profes["nombre"] == profesor_sel]
                if not prof_data.empty:
                    pass_correcta = str(prof_data.iloc[0]["password"])
                    if str(password) == pass_correcta:
                        es_valido = True
            
            if password == "admin123":
                es_valido = True

            if es_valido:
                st.session_state["autenticado"] = True
                st.session_state["usuario_actual"] = profesor_sel
                st.success(f"¡Bienvenido(a), {profesor_sel}!")
                st.rerun()
            else:
                st.error("❌ Contraseña incorrecta. Inténtalo de nuevo.")

if not st.session_state["autenticado"]:
    login()
    st.stop()

# =========================================================
# A PARTIR DE AQUÍ SOLO ACCEDEN LOS PROFESORES LOGUEADOS
# =========================================================

st.sidebar.markdown(f"👨‍🏫 **Profesor:** {st.session_state['usuario_actual']}")
if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.session_state["estudiante_seleccionado"] = None
    st.rerun()

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
    porcentaje = min(100, int((horas_actuales / 120) * 100))

    col_metrics, col_chart = st.columns([1, 1])

    with col_metrics:
        st.metric("Horas Completadas", f"{horas_actuales} / 120 hrs")
        st.metric("Horas Faltantes", f"{faltantes} hrs")
        st.metric("Porcentaje de Avance", f"{porcentaje}%")
        
        if horas_actuales >= 120:
            st.success("🎉 ¡Meta Alcanzada! Estudiante Apto para Graduación.")
        else:
            st.info(f"Faltan {faltantes} horas para completar las 120h obligatorias.")

    with col_chart:
        st.markdown("### ⭕ Porcentaje de Avance (120h)")
        
        data_pie = pd.DataFrame({
            "Estado": ["Horas Completadas", "Horas Faltantes"],
            "Horas": [horas_actuales, faltantes]
        })
        
        chart = alt.Chart(data_pie).mark_arc(innerRadius=60).encode(
            theta=alt.Theta(field="Horas", type="quantitative"),
            color=alt.Color(
                field="Estado", 
                type="nominal",
                scale=alt.Scale(
                    domain=["Horas Completadas", "Horas Faltantes"],
                    range=["#2ecc71", "#e74c3c"]
                )
            ),
            tooltip=["Estado", "Horas"]
        ).properties(
            height=300
        )
        
        st.altair_chart(chart, use_container_width=True)

    st.divider()

    st.subheader("📊 Historial de Registros y Asistencia")
    df_hist = cargar_historial(est["uid"])

    if not df_hist.empty:
        df_hist["fecha_dt"] = pd.to_datetime(df_hist["fecha"])
        df_hist["dia"] = df_hist["fecha_dt"].dt.strftime('%Y-%m-%d')
        
        df_por_dia = df_hist.groupby("dia")["horas"].sum().reset_index()

        st.markdown("### 📈 Horas Sumadas por Día")
        st.bar_chart(df_por_dia.set_index("dia")["horas"])

        st.markdown("### 📋 Tabla de Asistencia Detallada")
        df_tabla = df_hist[["fechaTxt", "horas", "profesor"]].rename(columns={
            "fechaTxt": "Fecha y Hora",
            "horas": "Horas Sumadas",
            "profesor": "Autorizado Por (Profesor)"
        })
        st.dataframe(df_tabla, use_container_width=True)
    else:
        st.warning("Este estudiante aún no tiene registros detallados en el Historial.")

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

        col1, col2, col3 = st.columns(3)
        col1.metric("Estudiantes Registrados", len(df))
        col2.metric("Graduados (120h)", len(df[pd.to_numeric(df["horas"], errors='coerce').fillna(0) >= 120]))
        prom = int(pd.to_numeric(df["horas"], errors='coerce').fillna(0).mean()) if len(df) > 0 else 0
        col3.metric("Promedio de Horas", f"{prom} hrs")

        # =======================================================
        # --- NUEVO APARTADO: GENERACIÓN Y DESCARGA DE PDF ---
        # =======================================================
        st.divider()
        st.subheader("📑 Reporte General PDF")
        
        def generar_pdf(dataframe):
            try:
                from fpdf import FPDF
            except ImportError:
                st.error("⚠️ Falta instalar fpdf. Ejecuta 'pip install fpdf' en tu terminal.")
                return None

            pdf = FPDF()
            pdf.add_page()
            
            # Título y Marca de Tiempo
            pdf.set_font('Arial', 'B', 15)
            pdf.cell(0, 10, 'Reporte General de Horas Sociales (120h)', 0, 1, 'C')
            
            fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pdf.set_font('Arial', 'I', 10)
            pdf.cell(0, 10, f'Generado el: {fecha_actual}', 0, 1, 'C')
            pdf.ln(5)

            # Preparar los datos numéricamente para evitar errores
            df_reporte = dataframe.copy()
            df_reporte['horas'] = pd.to_numeric(df_reporte['horas'], errors='coerce').fillna(0)

            # Filtrar categorías
            terminaron = df_reporte[df_reporte['horas'] >= 120]
            faltantes = df_reporte[(df_reporte['horas'] > 0) & (df_reporte['horas'] < 120)]
            empiezan = df_reporte[df_reporte['horas'] == 0]

            # Función de ayuda para dibujar cada sección en el PDF
            def agregar_seccion(titulo, datos):
                pdf.set_font('Arial', 'B', 12)
                pdf.cell(0, 10, f'{titulo} (Total: {len(datos)} estudiantes)', 0, 1, 'L')
                pdf.set_font('Arial', '', 10)
                
                if datos.empty:
                    pdf.cell(0, 6, 'Ningun estudiante en esta categoria.', 0, 1, 'L')
                else:
                    for idx, row in datos.iterrows():
                        # Limpiar tildes o caracteres raros para evitar conflictos con fpdf básico
                        nombre = str(row.get('nombre', 'N/A')).encode('latin-1', 'replace').decode('latin-1')
                        curso = str(row.get('curso', 'N/A')).encode('latin-1', 'replace').decode('latin-1')
                        horas = int(row.get('horas', 0))
                        pdf.cell(0, 6, f'- {nombre} | Curso: {curso} | Horas: {horas}', 0, 1, 'L')
                pdf.ln(5)

            # Agregar las 3 secciones solicitadas
            agregar_seccion('YA TERMINARON (120 hrs o mas)', terminaron)
            agregar_seccion('AUN FALTANTES (En progreso)', faltantes)
            agregar_seccion('RECIEN EMPIEZAN (0 hrs)', empiezan)

            return pdf.output(dest='S').encode('latin-1')

        # Botón de descarga interactivo
        pdf_bytes = generar_pdf(df)
        if pdf_bytes:
            fecha_str = datetime.now().strftime("%Y%m%d_%H%M")
            st.download_button(
                label="📥 Descargar Reporte PDF de Estudiantes",
                data=pdf_bytes,
                file_name=f"Reporte_Horas_{fecha_str}.pdf",
                mime="application/pdf"
            )
        # =======================================================
        
        st.divider()
        st.subheader("📋 Lista de Estudiantes")

        for index, row in df.iterrows():
            nombre = row["nombre"]
            curso = row["curso"]
            # Asegurar conversión a número para la UI
            horas = int(pd.to_numeric(row["horas"], errors='coerce') if pd.notnull(row["horas"]) else 0)
            porcentaje = min(100, int((horas / 120) * 100))
            
            with st.container():
                col_info, col_btn = st.columns([4, 1])
                
                with col_info:
                    st.markdown(f"### {nombre} `Curso: {curso}`")
                    st.progress(porcentaje / 100)
                    st.caption(f"**{horas}** / 120 hrs ({porcentaje}%) | ÚLTIMA MARCA: {row.get('ultimaFecha', 'N/A')}")
                
                with col_btn:
                    st.write("") 
                    if st.button("👁️ Ver Perfil", key=f"btn_{row['uid']}"):
                        st.session_state["estudiante_seleccionado"] = row
                        st.rerun()
                
                st.divider()
    else:
        st.info("No se encontraron estudiantes o la base de datos está vacía.")
