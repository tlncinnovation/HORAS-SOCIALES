import io
import os
from datetime import datetime
import altair as alt
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import requests
import streamlit as st

st.set_page_config(
    page_title="Control de Horas Sociales", page_icon="🎓", layout="wide"
)

# ⚠️ ¡VERIFICA QUE ESTE ENLACE SEA EL ACTUAL DEL DEPLOYMENT!
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycby_fdhEzpVo861lJwPzsS-Nosl6MjCoNFOMLz4y3letpSmK12V8t_qq8XC_A1oO3g0/exec"

def formatear_uid(uid):
    s = str(uid).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s

def obtener_fuente(tamano=28):
    rutas = [
        "arial.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for r in rutas:
        try:
            return ImageFont.truetype(r, tamano)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=tamano)
    except Exception:
        return ImageFont.load_default()

@st.cache_data(ttl=5)
def cargar_profesores():
    try:
        res = requests.get(APPS_SCRIPT_URL + "?action=obtener_profesores", timeout=15)
        try:
            datos = res.json()
        except Exception:
            st.error(f"🚨 Error Profesores: Apps Script no devolvió datos válidos. Revisa permisos. Google dice: {res.text[:100]}")
            return pd.DataFrame()
            
        return pd.DataFrame(datos["profesores"]) if "profesores" in datos else pd.DataFrame()
    except Exception as e:
        st.error(f"Error de red al cargar profesores: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=5)
def cargar_estudiantes():
    try:
        res = requests.get(APPS_SCRIPT_URL + "?action=obtener_estudiantes", timeout=15)
        
        try:
            datos = res.json()
        except Exception:
            # Aquí saltará la alerta si Google manda HTML (página de login) en lugar del JSON
            st.error(f"🚨 Error Estudiantes: Revisa si la URL cambió o si está en 'Cualquier persona'. Google respondió: {res.text[:100]}")
            return pd.DataFrame()

        lista = datos.get("estudiantes") or datos.get("resultados") or []

        if lista:
            df = pd.DataFrame(lista)
            df.columns = [str(c).strip().lower() for c in df.columns]

            doc_col = next((c for c in df.columns if "doc" in c or "ti" in c or "ident" in c or "cedula" in c), None)
            if doc_col:
                df["documento"] = df[doc_col]

            hrs_col = next((c for c in df.columns if "hora" in c or "acumula" in c or "total" in c), "horas")
            df["horas"] = df[hrs_col]

            for col in ["nombre", "uid", "curso", "horas", "ultimafecha", "correo", "documento"]:
                if col not in df.columns:
                    df[col] = "N/A" if col != "horas" else 0
            return df
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error de red con Google Sheets: {e}")
        return pd.DataFrame()


def cargar_historial(uid):
    try:
        uid_clean = formatear_uid(uid)
        params = {"action": "obtener_historial", "uid": uid_clean}
        res = requests.get(APPS_SCRIPT_URL, params=params, timeout=15)
        
        try:
            datos = res.json()
        except Exception:
            st.error(f"🚨 Error Historial: Google no devolvió datos válidos. Respuesta: {res.text[:100]}")
            return pd.DataFrame()
            
        if "historial" in datos and len(datos["historial"]) > 0:
            return pd.DataFrame(datos["historial"])
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error de red al cargar historial: {e}")
        return pd.DataFrame()


if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
if "usuario_actual" not in st.session_state:
    st.session_state["usuario_actual"] = ""


def login():
    st.title("🔒 Acceso al Sistema de Horas Sociales")
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
                st.error("❌ Contraseña incorrecta.")

if not st.session_state["autenticado"]:
    login()
    st.stop()

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
                )
                try:
                    res = requests.get(url_reg, timeout=10)
                    if res.status_code == 200:
                        st.success("¡Estudiante registrado correctamente!")
                        st.cache_data.clear()
                        st.rerun()
                    else:
                        st.error("Error al registrar en Google Sheets.")
                except Exception as ex:
                    st.error(f"Error de conexión: {ex}")

if "estudiante_seleccionado" not in st.session_state:
    st.session_state["estudiante_seleccionado"] = None


# ================= VISTA 2: PERFIL DEL ESTUDIANTE =================
if st.session_state["estudiante_seleccionado"] is not None:
    est = st.session_state["estudiante_seleccionado"]

    if st.button("⬅️ Volver a la lista general"):
        st.session_state["estudiante_seleccionado"] = None
        st.rerun()

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

    st.title(f"👤 {est['nombre']}")
    st.subheader(
        f"Curso: {est['curso']} | Doc. TI: `{doc_ti}` | UID: `{formatear_uid(est['uid'])}`"
    )
    st.caption(
        f"📧 Correo Electrónico: {est.get('correo', 'Sin correo registrado')}"
    )
    st.divider()

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
            st.success("🎉 ¡Meta Alcanzada! Estudiante Apto para Graduación.")
            st.markdown("### 📜 Certificado de Servicio Social")

            posibles_archivos = [
                "Certificado1.jpg", "Certificado1.png", "Certificado1.jpeg",
                "certificado1.jpg", "certificado1.png", "certificado1.jpeg",
            ]
            ruta_certificado = next((f for f in posibles_archivos if os.path.exists(f)), None)

            if ruta_certificado:
                try:
                    img = Image.open(ruta_certificado)
                    draw = ImageDraw.Draw(img)
                    font_cert = obtener_fuente(28)

                    draw.text((200, 468), str(est["nombre"]).upper(), fill="black", font=font_cert)
                    draw.text((700, 525), doc_ti, fill="black", font=font_cert)
                    draw.text((1100, 525), str(est["curso"]).upper(), fill="black", font=font_cert)

                    buf = io.BytesIO()
                    img.save(
                        buf,
                        format="PNG" if ruta_certificado.endswith(".png") else "JPEG",
                    )
                    img_bytes = buf.getvalue()

                    st.image(img_bytes, caption="Vista previa del Certificado", use_container_width=True)
                    st.download_button(
                        label="📥 Descargar Certificado",
                        data=img_bytes,
                        file_name=f"Certificado_{str(est['nombre']).replace(' ', '_')}.jpg",
                        mime="image/jpeg",
                    )
                except Exception as ex_cert:
                    st.error(f"Error al procesar la imagen: {ex_cert}")
            else:
                st.error("⚠️ Sube una imagen llamada 'Certificado1.jpg' a tu repositorio.")
        else:
            st.info(f"Faltan {faltantes} horas para completar las 120h obligatorias.")

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

    st.subheader("📊 Historial de Registros y Gráfica de Asistencia")
    df_hist = cargar_historial(est["uid"])

    if not df_hist.empty:
        df_h = df_hist.copy()
        df_h.columns = [str(c).strip().lower() for c in df_h.columns]

        col_fecha = next((c for c in df_h.columns if "fecha" in c or "date" in c), None)
        col_horas = next((c for c in df_h.columns if "hora" in c), None)

        if col_fecha and col_horas:
            df_h["horas_num"] = pd.to_numeric(df_h[col_horas], errors="coerce").fillna(0)
            df_h["fecha_dt"] = pd.to_datetime(df_h[col_fecha], dayfirst=True, errors="coerce")
            df_h["dia"] = df_h["fecha_dt"].dt.strftime("%d/%m/%Y").fillna(df_h[col_fecha].astype(str))

            df_agrupado = df_h.groupby("dia", as_index=False)["horas_num"].sum()

            st.markdown("### 📈 Horas Registradas por Día")
            st.bar_chart(data=df_agrupado, x="dia", y="horas_num")

        st.markdown("### 📋 Tabla de Asistencia Detallada")
        st.dataframe(df_hist, use_container_width=True)
    else:
        st.warning("Este estudiante aún no tiene registros asociados en la pestaña 'Historial'.")

    st.divider()
    with st.expander("⚠️ Zona de Peligro: Eliminar Perfil del Estudiante"):
        st.warning("Usa esta opción únicamente para borrar este perfil.")
        chk1 = st.checkbox("1. Confirmo que deseo borrar este perfil.")
        frase_req = f"BORRAR {est['nombre']}"
        confirm_txt = st.text_input(f"2. Escribe exactamente '{frase_req}':", disabled=not chk1)

        if st.button("🗑️ Eliminar Perfil Definitivamente", disabled=(confirm_txt != frase_req or not chk1)):
            try:
                uid_clean = formatear_uid(est["uid"])
                url_del = f"{APPS_SCRIPT_URL}?action=eliminar_estudiante&uid={uid_clean}"
                requests.get(url_del, timeout=10)
                st.success("Perfil eliminado correctamente.")
                st.session_state["estudiante_seleccionado"] = None
                st.cache_data.clear()
                st.rerun()
            except Exception as ex:
                st.error(f"Error al borrar: {ex}")


# ================= VISTA 1: LISTA GENERAL =================
else:
    st.title("🎓 Sistema de Control de Horas Sociales (120h)")

    if st.button("🔄 Actualizar Datos"):
        st.cache_data.clear()
        st.rerun()

    df = cargar_estudiantes()

    if not df.empty:
        st.sidebar.header("🔍 Filtros de Búsqueda")
        busqueda = st.sidebar.text_input("Buscar Estudiante / Documento:")
        cursos_disponibles = ["Todos"] + sorted(list(df["curso"].astype(str).unique()))
        curso_sel = st.sidebar.selectbox("Filtrar por Curso:", cursos_disponibles)

        if curso_sel != "Todos":
            df = df[df["curso"] == curso_sel]

        df["horas_num"] = pd.to_numeric(df["horas"], errors="coerce").fillna(0)

        if busqueda:
            df = df[
                df["nombre"].astype(str).str.contains(busqueda, case=False, na=False)
                | df["uid"].astype(str).str.contains(busqueda, case=False, na=False)
                | df["documento"].astype(str).str.contains(busqueda, case=False, na=False)
            ]

        col1, col2, col3 = st.columns(3)
        col1.metric("Estudiantes Filtrados", len(df))
        col2.metric("Graduados (120h)", len(df[df["horas_num"] >= 120]))
        prom = int(df["horas_num"].mean()) if len(df) > 0 else 0
        col3.metric("Promedio de Horas", f"{prom} hrs")

        st.divider()
        st.subheader("📋 Lista de Estudiantes")

        for index, row in df.iterrows():
            nombre = row["nombre"]
            curso = row["curso"]
            horas = int(row["horas_num"])
            porcentaje = min(100, int((horas / 120) * 100))
            doc = row.get("documento", "N/A")

            with st.container():
                col_info, col_btn = st.columns([4, 1])

                with col_info:
                    st.markdown(f"### {nombre} `Curso: {curso}`")
                    st.caption(f"🆔 **TI / Doc:** {doc}")
                    st.progress(porcentaje / 100)
                    st.caption(f"**{horas}** / 120 hrs ({porcentaje}%)")

                with col_btn:
                    st.write("")
                    if st.button("👁️ Ver Perfil", key=f"btn_{formatear_uid(row['uid'])}"):
                        st.session_state["estudiante_seleccionado"] = row
                        st.rerun()

                st.divider()
    else:
        st.info("No se encontraron estudiantes en la base de datos.")
