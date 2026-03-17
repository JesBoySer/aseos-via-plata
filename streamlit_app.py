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

.stButton>button{
border:2px solid #38BDF8;
border-radius:10px;
color:#F8FAFC;
background:#1E293B;
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

                cab = st.columns([1,2,3,3,1,1,1])

                cab[0].markdown('<div class="cabecera-bano">Estado</div>', unsafe_allow_html=True)
                cab[1].markdown('<div class="cabecera-bano">Curso</div>', unsafe_allow_html=True)
                cab[2].markdown('<div class="cabecera-bano">Alumno</div>', unsafe_allow_html=True)
                cab[3].markdown('<div class="cabecera-bano">Profesor</div>', unsafe_allow_html=True)
                cab[4].markdown('<div class="cabecera-bano">Min</div>', unsafe_allow_html=True)
                cab[5].markdown('<div class="cabecera-bano">OK</div>', unsafe_allow_html=True)
                cab[6].markdown('<div class="cabecera-bano">➡</div>', unsafe_allow_html=True)

                ocupados = st.session_state.ocupacion[st.session_state.planta][bano]

                for fila in range(2):

                    cols = st.columns([1,2,3,3,1,1,1])

                    key = f"{bano}_{fila}_{st.session_state.planta}"

                    if fila < len(ocupados):

                        p = ocupados[fila]

                        h_ent = datetime.strptime(p["h_entrada"], "%H:%M")

                        ahora = datetime.now()

                        minutos = int((ahora - h_ent.replace(
                            year=ahora.year,
                            month=ahora.month,
                            day=ahora.day)).total_seconds()/60)

                        cols[0].write("🔴")
                        cols[1].write(p["curso"])
                        cols[2].write(p["alumno"])
                        cols[3].write(p["profesor"])

                        if minutos > MAX_MINUTOS:
                            cols[4].markdown(
                                f'<span class="minutos-alerta">{minutos}</span>',
                                unsafe_allow_html=True)
                        else:
                            cols[4].write(minutos)

                        cols[5].markdown('<span class="ok-verde">✔</span>', unsafe_allow_html=True)

                        ok = True
                        obs = ""

                        if cols[6].button("➡", key=f"fin_{key}"):

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
                                "OK",
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
                                "estado":"OK",
                                "observaciones":obs

                            }])

                            subir_a_github(df_nuevo)

                            st.session_state.ocupacion[st.session_state.planta][bano].remove(p)

                            st.rerun()

                    else:

                        cols[0].write("🟢")

                        curso = cols[1].selectbox(
                            "",
                            sorted(df_alumnos["Curso"].unique()),
                            key=f"curso_{key}",
                            label_visibility="collapsed"
                        )

                        alumnos_disp = df_alumnos[
                            df_alumnos["Curso"]==curso
                        ]["Nombre"].tolist()

                        alumno = cols[2].selectbox(
                            "",
                            alumnos_disp,
                            key=f"alumno_{key}",
                            label_visibility="collapsed"
                        )

                        profesor = cols[3].selectbox(
                            "",
                            lista_profesores,
                            key=f"prof_{key}",
                            label_visibility="collapsed"
                        )

                        cols[4].write("")
                        cols[5].write("")

                        if alumno_en_bano(alumno):

                            st.warning("Este alumno ya está en otro baño")

                        elif cols[6].button("🟢", key=f"entrada_{key}"):

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
