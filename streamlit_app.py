import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
import requests
import base64
from io import StringIO
from streamlit_autorefresh import st_autorefresh

st.set_page_config(
    page_title="SCA - IES Vía de la Plata",
    layout="wide",
    page_icon="🚾"
)

st_autorefresh(interval=30000, key="refresh")

MAX_MINUTOS = 10

GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = st.secrets["GITHUB_REPO"]
FILE_PATH = st.secrets["GITHUB_FILE"]

st.markdown("""
<style>

.stApp{
background:#0B1120;
color:#E2E8F0;
}

/* === SELECTBOX / MULTISELECT: fondo negro y texto blanco === */

/* Caja del control (cerrado) */
.stSelectbox div[data-baseweb="select"] > div,
.stMultiSelect div[data-baseweb="select"] > div {
  background: #000000 !important;     /* negro */
  color: #ffffff !important;           /* texto blanco */
  border-color: #334155 !important;    /* slate-700 */
  border-radius: 8px !important;
}

/* Texto del input y placeholder */
.stSelectbox div[data-baseweb="select"] input,
.stMultiSelect div[data-baseweb="select"] input,
.stSelectbox div[data-baseweb="select"] div[aria-hidden="true"],
.stMultiSelect div[data-baseweb="select"] div[aria-hidden="true"] {
  color: #ffffff !important;           /* texto blanco */
}

/* Color algo más tenue para el placeholder (si aplica) */
.stSelectbox div[data-baseweb="select"] div[aria-hidden="true"],
.stMultiSelect div[data-baseweb="select"] div[aria-hidden="true"] {
  opacity: 0.7 !important;             /* simula placeholder */
}

/* Icono "chevron" (flecha) */
.stSelectbox svg, 
.stMultiSelect svg {
  fill: #ffffff !important;
  color: #ffffff !important;
}

/* Menú desplegable */
.stSelectbox div[data-baseweb="select"] div[role="listbox"],
.stMultiSelect div[data-baseweb="select"] div[role="listbox"] {
  background: #0a0a0a !important;      /* negro casi puro */
  color: #ffffff !important;
  border: 1px solid #334155 !important;
}

/* Opción del menú (estado normal) */
.stSelectbox div[role="option"],
.stMultiSelect div[role="option"] {
  background: #0a0a0a !important;
  color: #ffffff !important;
}

/* Opción con hover */
.stSelectbox div[role="option"]:hover,
.stMultiSelect div[role="option"]:hover {
  background: #1f2937 !important;      /* gris oscuro (tailwind slate-800) */
}

/* Opción seleccionada/activa */
.stSelectbox div[aria-selected="true"],
.stMultiSelect div[aria-selected="true"] {
  background: #111827 !important;      /* slate-900 */
  color: #ffffff !important;
}

/* Borde/halo de foco para accesibilidad */
.stSelectbox div[data-baseweb="select"] > div:focus-within,
.stMultiSelect div[data-baseweb="select"] > div:focus-within {
  outline: 2px solid #2563EB !important;  /* azul */
  outline-offset: 1px !important;
}

/* Alineado centrado (ya lo tenías, lo refuerzo) */
.stSelectbox div[data-baseweb="select"],
.stMultiSelect div[data-baseweb="select"] {
  text-align: center;
}


.stButton>button{
border:none;
border-radius:8px;
background:#1E293B;
color:#F8FAFC;
font-weight:600;
}

.stButton>button:hover{
background:#2563EB;
color:white;
}

.cabecera-bano{
border-bottom:1px solid #38BDF8;
padding:4px;
font-weight:bold;
}

.minutos-alerta{
color:#ef4444;
font-weight:bold;
}

.ok-verde{
color:#22c55e;
font-weight:bold;
}

/* CHECKBOX MÁS PEQUEÑOS */
.stCheckbox > label > div{
transform:scale(0.75);
}

/* Centrar contenido de columnas */
[data-testid="column"] {
    text-align: center;
}

/* centrar selectbox */
.stSelectbox div[data-baseweb="select"] {
    text-align: center;
}

/* centrar checkbox */
.stCheckbox {
    display: flex;
    justify-content: center;
}

/* Alinear botones con selectboxes sin label */
div[data-testid="column"] > div > div > div > div > .stButton {
    margin-top: 28px;
}

</style>
""", unsafe_allow_html=True)

def init_db():

    if not os.path.exists("data"):
        os.makedirs("data")

    conn = sqlite3.connect("data/historico.sqlite", check_same_thread=False)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS visitas(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        planta TEXT,
        bano TEXT,
        alumno TEXT,
        curso TEXT,
        profesor TEXT,
        h_entrada TEXT,
        h_salida TEXT,
        estado TEXT,
        observaciones TEXT
    )
    """)

    conn.commit()

    return conn


def subir_a_github(df_nuevo):

    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"

    headers = {
        "Authorization": f"token {GITHUB_TOKEN}"
    }

    r = requests.get(url, headers=headers)

    if r.status_code == 200:

        contenido = r.json()

        sha = contenido["sha"]

        csv_actual = base64.b64decode(contenido["content"]).decode()

        df_actual = pd.read_csv(StringIO(csv_actual))

        df_total = pd.concat([df_actual, df_nuevo]).drop_duplicates()

    else:

        sha = None
        df_total = df_nuevo

    nuevo_csv = df_total.to_csv(index=False)

    data = {
        "message": "Actualizar histórico aseos",
        "content": base64.b64encode(nuevo_csv.encode()).decode(),
        "sha": sha
    }

    requests.put(url, headers=headers, json=data)


@st.cache_data
def cargar_datos():

    alumnos = pd.read_csv("data/alumnos.csv")
    profesores = pd.read_csv("data/profesores.csv")

    return alumnos, profesores


df_alumnos, df_profesores = cargar_datos()

lista_profesores = df_profesores["Nombre"].tolist()

if "planta" not in st.session_state:
    st.session_state.planta = None

if "ocupacion" not in st.session_state:

    st.session_state.ocupacion = {

        "Primera": {
            "Chicos Norte":[],
            "Chicas Norte":[],
            "Chicos Sur":[],
            "Chicas Sur":[]
        },

        "Segunda": {
            "Chicos Norte":[],
            "Chicas Norte":[],
            "Chicos Sur":[],
            "Chicas Sur":[]
        }
    }

if "editar" not in st.session_state:
    st.session_state.editar = {}

with st.sidebar:

    st.title("🚾 SCA")

    if st.session_state.planta:

        st.success(f"Planta {st.session_state.planta}")

        if st.button("Cambiar planta"):

            st.session_state.planta = None
            st.rerun()

if st.session_state.planta is None:

    st.title("Sistema Control de Aseos")

    c1, c2 = st.columns(2)

    if c1.button("Planta Primera", use_container_width=True):

        st.session_state.planta = "Primera"
        st.rerun()

    if c2.button("Planta Segunda", use_container_width=True):

        st.session_state.planta = "Segunda"
        st.rerun()

    st.stop()

def alumno_en_bano(nombre):

    for planta in st.session_state.ocupacion.values():

        for bano in planta.values():

            for p in bano:

                if p["alumno"] == nombre:

                    return True

    return False

tab_panel, tab_hist = st.tabs(["Panel", "Histórico"])

zonas = {
    "NORTE": ["Chicos Norte", "Chicas Norte"],
    "SUR": ["Chicos Sur", "Chicas Sur"]
}

with tab_panel:

    for zona, banos in zonas.items():

        st.subheader(zona)

        col1, col2 = st.columns(2)

        for i, bano in enumerate(banos):

            cont = col1 if i == 0 else col2

            with cont:

                icono = "🚹" if "Chicos" in bano else "🚺"

                st.markdown(f"### {icono} {bano}")

                cab = st.columns([2,3,3,1,1,1])

                cab[0].markdown('<div class="cabecera-bano">Curso</div>', unsafe_allow_html=True)
                cab[1].markdown('<div class="cabecera-bano">Alumno</div>', unsafe_allow_html=True)
                cab[2].markdown('<div class="cabecera-bano">Profesor</div>', unsafe_allow_html=True)
                cab[3].markdown('<div class="cabecera-bano">Min</div>', unsafe_allow_html=True)
                cab[4].markdown('<div class="cabecera-bano">OK</div>', unsafe_allow_html=True)
                cab[5].markdown('<div class="cabecera-bano">➡</div>', unsafe_allow_html=True)

                ocupados = st.session_state.ocupacion[st.session_state.planta][bano]

                for fila in range(2):

                    cols = st.columns([2,3,3,1,1,1])

                    key = f"{bano}_{fila}_{st.session_state.planta}"

                    if fila < len(ocupados):

                        p = ocupados[fila]

                        h_ent = datetime.strptime(p["h_entrada"], "%H:%M")

                        ahora = datetime.now()

                        minutos = int((ahora - h_ent.replace(
                            year=ahora.year,
                            month=ahora.month,
                            day=ahora.day)).total_seconds()/60)

                        cols[0].write(p["curso"])
                        cols[1].write(p["alumno"])
                        cols[2].write(p["profesor"])

                        if minutos > MAX_MINUTOS:
                            cols[3].markdown(
                                f'<span class="minutos-alerta">{minutos}</span>',
                                unsafe_allow_html=True)
                        else:
                            cols[3].write(minutos)

                        ok = cols[4].checkbox("", value=True, key=f"ok_{key}")

                        obs = ""

                        if not ok:
                            obs = st.text_input("", key=f"obs_{key}", placeholder="Observaciones")

                        if cols[5].button("➡", key=f"fin_{key}"):

                            estado_final = "OK" if ok else "INCIDENCIA"

                            conn = init_db()

                            conn.execute("""
                                INSERT INTO visitas
                                (planta,bano,alumno,curso,profesor,h_entrada,h_salida,estado,observaciones)
                                VALUES (?,?,?,?,?,?,?,?,?)
                            """, (

                                st.session_state.planta,
                                bano,
                                p["alumno"],
                                p["curso"],
                                p["profesor"],
                                p["h_entrada"],
                                datetime.now().strftime("%H:%M"),
                                estado_final,
                                obs
                            ))

                            conn.commit()

                            df_nuevo = pd.DataFrame([{

                                "planta":st.session_state.planta,
                                "bano":bano,
                                "curso":p["curso"],
                                "alumno":p["alumno"],
                                "profesor":p["profesor"],
                                "h_entrada":p["h_entrada"],
                                "h_salida":datetime.now().strftime("%H:%M"),
                                "estado":estado_final,
                                "observaciones":obs

                            }])

                            subir_a_github(df_nuevo)

                            st.session_state.ocupacion[st.session_state.planta][bano].remove(p)

                            st.rerun()

                    else:

                        cursos = ["Seleccionar"] + sorted(df_alumnos["Curso"].unique())

                        curso = cols[0].selectbox("", cursos, key=f"curso_{key}")

                        alumnos_disp = []

                        if curso != "Seleccionar":
                            alumnos_disp = df_alumnos[
                                df_alumnos["Curso"]==curso
                            ]["Nombre"].tolist()

                        alumnos_disp = ["Seleccionar"] + alumnos_disp

                        alumno = cols[1].selectbox("", alumnos_disp, key=f"alumno_{key}")

                        profesores = ["Seleccionar"] + lista_profesores

                        profesor = cols[2].selectbox("", profesores, key=f"prof_{key}")

                        cols[3].write("")
                        cols[4].write("")
                        cols[5].write("")

                        if alumno_en_bano(alumno):
                            st.warning("Este alumno ya está en otro baño")

                        elif cols[5].button("🟢", key=f"entrada_{key}"):

                            if curso=="Seleccionar" or alumno=="Seleccionar" or profesor=="Seleccionar":
                                st.warning("Debes seleccionar curso, alumno y profesor")
                            else:

                                st.session_state.ocupacion[
                                    st.session_state.planta][bano].append({

                                    "alumno": alumno,
                                    "curso": curso,
                                    "profesor": profesor,
                                    "h_entrada": datetime.now().strftime("%H:%M")

                                })

                                st.rerun()


with tab_hist:

    st.subheader("Histórico de visitas")
  
    conn = init_db()

    df = pd.read_sql_query("""
        SELECT id, planta, bano, curso, alumno, profesor,
        h_entrada, h_salida,
        (strftime('%s',h_salida)-strftime('%s',h_entrada))/60 as minutos,
        estado, observaciones
        FROM visitas
        ORDER BY id DESC
    """, conn)

    conn.close()

    st.dataframe(df, use_container_width=True)
