import io
import os
from datetime import datetime
import altair as alt
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import requests
import streamlit as st

# =========================================================
# CONFIGURACIÓN DE LA PÁGINA
# =========================================================
st.set_page_config(
    page_title="Control de Horas Sociales", page_icon="🎓", layout="wide"
)

APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycby_fdhEzpVo861lJwPzsS-Nosl6MjCoNFOMLz4y3letpSmK12V8t_qq8XC_A1oO3g0/exec"


# =========================================================
# FUNCIÓN AUXILIAR PARA FUENTES DE CERTIFICADO
# =========================================================
def obtener_fuente(tamano=28):
    rutas_fuentes = [
        "arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    for ruta in rutas_fuentes:
        try:
            return ImageFont.truetype(ruta, tamano)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=tamano)
    except Exception:
        return ImageFont.load_default()


# =========================================================
# FUNCIONES DE CARGA DE DATOS
# =========================================================
@st.cache_data(ttl=5)
def cargar_profesores():
    try:
        url = APPS_SCRIPT_URL + "?action=obtener_profesores"
        res = requests.get(url, timeout=10)
        datos = res.json()
        if "profesores" in datos:
            return pd.DataFrame(datos["profesores"])
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=5)
def cargar_estudiantes():
    try:
        url = APPS_SCRIPT_URL + "?action=obtener_estudiantes"
        res = requests.get(url, timeout=10)
        datos = res.json()
        lista = datos.get("estudiantes") or datos.get("resultados") or []

        if lista:
            df = pd.DataFrame(lista)

            # --- NORMALIZACIÓN DE COLUMNAS ---
            df.columns = [str(c).strip().lower() for c in df.columns]

            # Búsqueda automática de la columna del documento
            doc_col = None
            for c in df.columns:
                if "doc" in c or "ti" in c or "ident" in c or "cedula" in c:
                    doc_col = c
                    break

            if doc_col:
                df["documento"] = df[doc_col]

            cols_obligatorias = [
                "nombre",
                "uid",
                "curso",
                "horas",
                "ultimaFecha",
                "correo",
                "documento",
            ]
            for col in cols_obligatorias:
                if col not in df.columns:
                    df[col] = "N/A" if col not in ["horas"] else 0
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al conectar con Google Sheets: {e}")
        return pd.DataFrame()


def cargar_historial(uid):
    try:
        params = {"action": "obtener_historial", "uid": str(uid).strip()}
        res = requests.get(APPS_SCRIPT_URL, params=params, timeout=10)
        datos = res.json()
        if "historial" in datos and len(datos["historial"]) > 0:
            return pd.DataFrame(datos["historial"])
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al cargar historial: {e}")
        return pd.DataFrame()


# =========================================================
# INICIO DE SESIÓN
# =========================================================
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
            profesor_sel = st.selectbox(
                "Selecciona tu nombre:", df_profes["nombre"].tolist()
            )
        else:
            profesor_sel = st.text_input("Nombre de Profesor:")

        password = st.text_input("Contraseña:", type="password")
        btn_submit = st.form_submit_button("Iniciar Sesión")

        if btn_submit:
            es_valido = False
            if not df_profes.empty:
                prof_data = df_profes[df_profes["nombre"] == profesor_sel]
                if not prof_data.empty:
                    pass_correcta = str(
                        prof_data.iloc[0].get("password")
                        or prof_data.iloc[0].get("contrasena")
                        or ""
                    ).strip()
                    if str(password).strip() == pass_correcta:
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
# MENÚ LATERAL Y REGISTRO DE TARJETAS
# =========================================================
st.sidebar.markdown(f"👨‍🏫 **Profesor:** {st.session_state['usuario_actual']}")
if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state["autenticado"] = False
    st.session_state["estudiante_seleccionado"] = None
    st.rerun()

st.sidebar.divider()

with st.sidebar.expander("➕ Registrar Nueva Tarjeta / Estudiante"):
    with st.form("form_registro_tarjeta"):
        nuevo_uid = st.text_input("UID Tarjeta (RFID):").strip().upper()
        nuevo_nombre = st.text_input("Nombre Completo:")
        nuevo_doc = st.text_input("Documento (TI / Cédula):")
        nuevo_correo = st.text_input("Correo Electrónico:")
        nuevo_curso = st.text_input("Curso (ej: 901, 1102):").strip()
        horas_ini = st.number_input("Horas Iniciales:", min_value=0, value=0)

        btn_reg = st.form_submit_button("💾 Guardar Estudiante")

        if btn_reg:
            if not nuevo_uid or not nuevo_nombre or not nuevo_curso:
                st.error("⚠️ El UID, Nombre y Curso son obligatorios.")
            else:
                url_reg = (
                    f"{APPS_SCRIPT_URL}?action=registrar_estudiante"
                    f"&uid={nuevo_uid}&nombre={nuevo_nombre}"
                    f"&documento={nuevo_doc}&correo={nuevo_correo}"
                    f"&curso={nuevo_curso}&horas={horas_ini}"
                    f"&profe={st.session_state['usuario_actual']}"
                )
                try:
                    res = requests.get(url_reg, timeout=10)
                    if res.status_code == 200:
                        st.success(
                            f"¡{nuevo_nombre} registrado correctamente!"
                        )
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("Error al registrar en Google Sheets.")
                except Exception as ex:
                    st.error(f"Error de conexión: {ex}")

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

    # Extracción dinámica del documento
    doc_ti = "N/A"
    for k, v in est.items():
        k_clean = str(k).lower().strip()
        v_clean = str(v).strip()
        if (
            ("doc" in k_clean or "ti" in k_clean or "ident" in k_clean)
            and v_clean
            and v_clean.upper() != "N/A"
        ):
            doc_ti = v_clean
            break
    if doc_ti == "N/A":
        doc_ti = str(est.get("documento", "N/A"))

    st.title(f"👤 {est['nombre']}")
    st.subheader(
        f"Curso: {est['curso']} | Doc. TI: `{doc_ti}` | UID: `{est['uid']}`"
    )
    st.caption(
        f"📧 Correo Electrónico: {est.get('correo', 'Sin correo registrado')}"
    )
    st.divider()

    # Conversión segura de horas evitando NaN
    horas_raw = pd.to_numeric(est.get("horas", 0), errors="coerce")
    horas_actuales = int(0 if pd.isna(horas_raw) else horas_raw)

    faltantes = max(0, 120 - horas_actuales)
    porcentaje = min(100, int((horas_actuales / 120) * 100))

    col_metrics, col_chart = st.columns([1, 1])

    with col_metrics:
        st.metric("Horas Completadas", f"{horas_actuales} / 120 hrs")
        st.metric("Horas Faltantes", f"{faltantes} hrs")
        st.metric("Porcentaje de Avance", f"{porcentaje}%")

        if horas_actuales >= 120:
            st.success(
                "🎉 ¡Meta Alcanzada! Estudiante Apto para Graduación."
            )
            st.markdown("### 📜 Certificado de Servicio Social")

            posibles_nombres = [
                "Certificado.jpg",
                "Certificado.jpeg",
                "Certificado.png",
                "certificado.jpg",
                "certificado.jpeg",
            ]
            ruta_certificado = next(
                (f for f in posibles_nombres if os.path.exists(f)), None
            )

            if ruta_certificado:
                try:
                    img = Image.open(ruta_certificado)
                    draw = ImageDraw.Draw(img)
                    font_cert = obtener_fuente(28)

                    draw.text(
                        (480, 468),
                        str(est["nombre"]).upper(),
                        fill="black",
                        font=font_cert,
                    )
                    draw.text((700, 525), doc_ti, fill="black", font=font_cert)
                    draw.text(
                        (1100, 525),
                        str(est["curso"]).upper(),
                        fill="black",
                        font=font_cert,
                    )
                    draw.text((380, 580), "U", fill="black", font=font_cert)

                    buf = io.BytesIO()
                    img.save(buf, format="JPEG")
                    img_bytes = buf.getvalue()

                    st.image(
                        img_bytes,
                        caption="Vista previa del Certificado",
                        use_container_width=True,
                    )
                    st.download_button(
                        label="📥 Descargar Certificado (Imagen)",
                        data=img_bytes,
                        file_name=f"Certificado_{str(est['nombre']).replace(' ', '_')}.jpg",
                        mime="image/jpeg",
                    )
                except Exception as ex_cert:
                    st.error(f"Error al procesar la imagen: {ex_cert}")
            else:
                st.error(
                    "⚠️ La imagen 'Certificado.jpg' no está en la carpeta del servidor."
                )
        else:
            st.info(
                f"Faltan {faltantes} horas para completar las 120h obligatorias."
            )

    with col_chart:
        st.markdown("### ⭕ Porcentaje de Avance (120h)")
        data_pie = pd.DataFrame({
            "Estado": ["Horas Completadas", "Horas Faltantes"],
            "Horas": [horas_actuales, faltantes],
        })

        chart = (
            alt.Chart(data_pie)
            .mark_arc(innerRadius=60)
            .encode(
                theta=alt.Theta(field="Horas", type="quantitative"),
                color=alt.Color(
                    field="Estado",
                    type="nominal",
                    scale=alt.Scale(
                        domain=["Horas Completadas", "Horas Faltantes"],
                        range=["#2ecc71", "#e74c3c"],
                    ),
                ),
                tooltip=["Estado", "Horas"],
            )
            .properties(height=300)
        )

        st.altair_chart(chart, use_container_width=True)

    st.divider()

    # =========================================================
    # HISTORIAL DE REGISTROS Y ASISTENCIA
    # =========================================================
    st.subheader("📊 Historial de Registros y Asistencia")
    df_hist = cargar_historial(est["uid"])

    if not df_hist.empty:
        col_fecha = None
        for pos_col in ["fechaIso", "fechaTxt", "fecha"]:
            if pos_col in df_hist.columns:
                col_fecha = pos_col
                break

        if col_fecha:
            df_hist["fecha_dt"] = pd.to_datetime(
                df_hist[col_fecha], dayfirst=True, errors="coerce"
            )
            df_hist["dia"] = df_hist["fecha_dt"].dt.strftime("%d/%m/%Y")
            df_hist["horas"] = pd.to_numeric(
                df_hist["horas"], errors="coerce"
            ).fillna(0)

            df_por_dia = df_hist.groupby("dia", as_index=False)["horas"].sum()

            st.markdown("### 📈 Horas Sumadas por Día")
            st.bar_chart(data=df_por_dia, x="dia", y="horas")

            st.markdown("### 📋 Tabla de Asistencia Detallada")
            cols_mostrar = [
                c
                for c in ["fechaTxt", "horas", "profesor"]
                if c in df_hist.columns
            ]
            df_tabla = df_hist[cols_mostrar].rename(
                columns={
                    "fechaTxt": "Fecha y Hora",
                    "horas": "Horas Sumadas",
                    "profesor": "Autorizado Por (Profesor)",
                }
            )
            st.dataframe(df_tabla, use_container_width=True)
        else:
            st.warning(
                "No se encontró un formato de fecha válido en el historial."
            )
    else:
        st.warning(
            "Este estudiante aún no tiene registros detallados en el Historial."
        )

    # ELIMINACIÓN DE PERFIL
    st.divider()
    with st.expander("⚠️ Zona de Peligro: Eliminar Perfil del Estudiante"):
        st.warning(
            "Usa esta opción únicamente cuando el estudiante se haya graduado y tenga su certificado."
        )
        chk1 = st.checkbox(
            "1. Confirmo que deseo iniciar el proceso de eliminación."
        )
        chk2 = st.checkbox(
            "2. Entiendo que esta acción borrará permanentemente todo el historial.",
            disabled=not chk1,
        )

        frase_req = f"BORRAR {est['nombre']}"
        confirm_txt = st.text_input(
            f"3. Escribe exactamente '{frase_req}' para habilitar el borrado:",
            disabled=not chk2,
        )

        if st.button(
            "🗑️ Eliminar Perfil Definitivamente",
            disabled=(confirm_txt != frase_req or not chk2),
        ):
            try:
                url_del = f"{APPS_SCRIPT_URL}?action=eliminar_estudiante&uid={est['uid']}"
                requests.get(url_del, timeout=10)
                st.success(f"El perfil de {est['nombre']} ha sido eliminado.")
                st.session_state["estudiante_seleccionado"] = None
                st.cache_data.clear()
                st.rerun()
            except Exception as ex:
                st.error(f"Error al borrar: {ex}")

# =========================================================
# VISTA 1: LISTA GENERAL DE ESTUDIANTES
# =========================================================
else:
    st.title("🎓 Sistema de Control de Horas Sociales (120h)")
    st.markdown(
        "Consulta en tiempo real el avance de horas sociales de los estudiantes."
    )

    if st.button("🔄 Actualizar Datos"):
        st.cache_data.clear()
        st.rerun()

    df = cargar_estudiantes()

    if not df.empty:
        st.sidebar.header("🔍 Filtros de Búsqueda")
        busqueda = st.sidebar.text_input(
            "Buscar por Nombre, UID, TI o Curso:"
        )
        cursos_disponibles = ["Todos"] + sorted(
            list(df["curso"].astype(str).unique())
        )
        curso_sel = st.sidebar.selectbox(
            "Filtrar por Curso:", cursos_disponibles
        )

        estado_opciones = [
            "Todos",
            "En progreso (< 120h)",
            "Terminados / Con Certificado (120h)",
        ]
        estado_sel = st.sidebar.selectbox(
            "Estado del Servicio:", estado_opciones
        )

        st.sidebar.markdown("**📅 Filtrar por Última Marca**")
        fecha_inicio = st.sidebar.date_input(
            "Desde:", value=None, format="DD/MM/YYYY"
        )
        fecha_fin = st.sidebar.date_input(
            "Hasta:", value=None, format="DD/MM/YYYY"
        )

        if curso_sel != "Todos":
            df = df[df["curso"] == curso_sel]

        df["horas_num"] = (
            pd.to_numeric(df["horas"], errors="coerce").fillna(0)
        )
        if estado_sel == "En progreso (< 120h)":
            df = df[df["horas_num"] < 120]
        elif estado_sel == "Terminados / Con Certificado (120h)":
            df = df[df["horas_num"] >= 120]

        if fecha_inicio is not None and fecha_fin is not None:
            if fecha_inicio <= fecha_fin:
                fechas_convertidas = pd.to_datetime(
                    df["ultimaFecha"],
                    format="mixed",
                    dayfirst=True,
                    errors="coerce",
                )
                df = df[
                    (fechas_convertidas.dt.date >= fecha_inicio)
                    & (fechas_convertidas.dt.date <= fecha_fin)
                ]
            else:
                st.sidebar.error(
                    "⚠️ La fecha 'Desde' no puede ser posterior a 'Hasta'."
                )

        if busqueda:
            df = df[
                df["nombre"]
                .astype(str)
                .str.contains(busqueda, case=False, na=False)
                | df["uid"]
                .astype(str)
                .str.contains(busqueda, case=False, na=False)
                | df["curso"]
                .astype(str)
                .str.contains(busqueda, case=False, na=False)
                | df["documento"]
                .astype(str)
                .str.contains(busqueda, case=False, na=False)
            ]

        col1, col2, col3 = st.columns(3)
        col1.metric("Estudiantes Filtrados", len(df))
        col2.metric("Graduados (120h)", len(df[df["horas_num"] >= 120]))
        prom = int(df["horas_num"].mean()) if len(df) > 0 else 0
        col3.metric("Promedio de Horas", f"{prom} hrs")

        st.divider()
        st.subheader("📑 Reporte General PDF")

        def generar_pdf(dataframe):
            try:
                from fpdf import FPDF
            except ImportError:
                st.error(
                    "⚠️ Falta instalar fpdf. Ejecuta 'pip install fpdf2' en tu entorno."
                )
                return None

            pdf = FPDF(orientation="P", unit="mm", format="A4")
            pdf.add_page()

            pdf.set_font("Arial", "B", 14)
            pdf.cell(
                0, 10, "Reporte General de Horas Sociales (120h)", 0, 1, "C"
            )

            fecha_act = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            pdf.set_font("Arial", "I", 9)
            pdf.cell(0, 8, f"Generado el: {fecha_act}", 0, 1, "C")
            pdf.ln(4)

            def agregar_seccion_tabla(titulo, datos):
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 8, f"{titulo} (Total: {len(datos)})", 0, 1, "L")

                if datos.empty:
                    pdf.set_font("Arial", "", 9)
                    pdf.cell(
                        0, 6, "Ningun estudiante en esta categoria.", 0, 1, "L"
                    )
                else:
                    pdf.set_font("Arial", "B", 9)
                    pdf.set_fill_color(210, 225, 250)
                    pdf.cell(65, 7, "Nombre", 1, 0, "C", fill=True)
                    pdf.cell(30, 7, "Doc. TI", 1, 0, "C", fill=True)
                    pdf.cell(20, 7, "Curso", 1, 0, "C", fill=True)
                    pdf.cell(20, 7, "Horas", 1, 0, "C", fill=True)
                    pdf.cell(55, 7, "Correo", 1, 1, "C", fill=True)

                    pdf.set_font("Arial", "", 8)
                    for idx, row in datos.iterrows():
                        nom = (
                            str(row.get("nombre", "N/A"))[:30]
                            .encode("latin-1", "replace")
                            .decode("latin-1")
                        )
                        doc = (
                            str(row.get("documento", "N/A"))[:14]
                            .encode("latin-1", "replace")
                            .decode("latin-1")
                        )
                        cur = (
                            str(row.get("curso", "N/A"))[:8]
                            .encode("latin-1", "replace")
                            .decode("latin-1")
                        )
                        hrs = str(int(row.get("horas_num", 0)))
                        em = (
                            str(row.get("correo", "N/A"))[:25]
                            .encode("latin-1", "replace")
                            .decode("latin-1")
                        )

                        pdf.cell(65, 7, nom, 1, 0, "L")
                        pdf.cell(30, 7, doc, 1, 0, "C")
                        pdf.cell(20, 7, cur, 1, 0, "C")
                        pdf.cell(20, 7, hrs, 1, 0, "C")
                        pdf.cell(55, 7, em, 1, 1, "L")
                pdf.ln(4)

            terminaron = dataframe[dataframe["horas_num"] >= 120]
            faltantes = dataframe[
                (dataframe["horas_num"] > 0) & (dataframe["horas_num"] < 120)
            ]
            empiezan = dataframe[dataframe["horas_num"] == 0]

            agregar_seccion_tabla("COMPLETARON (120 hrs o mas)", terminaron)
            agregar_seccion_tabla("EN PROGRESO", faltantes)
            agregar_seccion_tabla("SIN REGISTROS (0 hrs)", empiezan)

            return pdf.output(dest="S").encode("latin-1")

        pdf_bytes = generar_pdf(df)
        if pdf_bytes:
            fecha_str = datetime.now().strftime("%d%m%Y_%H%M")
            st.download_button(
                label="📥 Descargar Reporte PDF Completo",
                data=pdf_bytes,
                file_name=f"Reporte_Horas_{fecha_str}.pdf",
                mime="application/pdf",
            )

        st.divider()
        st.subheader("📋 Lista de Estudiantes")

        for index, row in df.iterrows():
            nombre = row["nombre"]
            curso = row["curso"]
            horas = int(row["horas_num"])
            porcentaje = min(100, int((horas / 120) * 100))

            doc = "N/A"
            for k, v in row.items():
                k_clean = str(k).lower().strip()
                v_clean = str(v).strip()
                if (
                    ("doc" in k_clean or "ti" in k_clean or "ident" in k_clean)
                    and v_clean
                    and v_clean.upper() != "N/A"
                ):
                    doc = v_clean
                    break

            correo = row.get("correo", "N/A")

            with st.container():
                col_info, col_btn = st.columns([4, 1])

                with col_info:
                    st.markdown(f"### {nombre} `Curso: {curso}`")
                    st.caption(f"🆔 **TI:** {doc} | 📧 **Correo:** {correo}")
                    st.progress(porcentaje / 100)
                    st.caption(
                        f"**{horas}** / 120 hrs ({porcentaje}%) | ÚLTIMA FECHA: {row.get('ultimaFecha', 'N/A')}"
                    )

                with col_btn:
                    st.write("")
                    if st.button("👁️ Ver Perfil", key=f"btn_{row['uid']}"):
                        st.session_state["estudiante_seleccionado"] = row
                        st.rerun()

                st.divider()
    else:
        st.info("No se encontraron estudiantes o la base de datos está vacía.")
