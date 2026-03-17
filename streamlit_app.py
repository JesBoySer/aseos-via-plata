import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
import requests
import base64

st.set_page_config(
    page_title="SCA - IES Vía de la Plata",
    layout="wide",
    page_icon="🚾"
)

# -------------------------
# CONFIG GITHUB
# -------------------------

GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = st.secrets["GITHUB_REPO"]
FILE_PATH = st.secrets["GITHUB_FILE"]

# -------------------------
# ESTILOS
# -------------------------

st.markdown("""
<style>

.stApp{
background:#0B1120;
color:#E2E8F0;
}

table{
border-collapse: collapse;
width:100%;
}

th, td{
border:1px solid #38BDF8;
padding:6px;
text-align:center;
}

th{
background:#1E293B;
}

</style>
""", unsafe_allow_html=True)

# -------------------------
# SQLITE
# -------------------------

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

# -------------------------
# GITHUB SYNC
# -------------------------

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

        df_actual = pd.read_csv(pd.compat.StringIO(csv_actual))

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

# -------------------------
# CARGA DATOS
# -------------------------

@st.cache_data
def cargar_datos():

    alumnos = pd.read_csv("data/alumnos.csv")
    profesores = pd.read_csv("data/profesores.csv")

    return alumnos, profesores

df_alumnos, df_profesores = cargar_datos()

lista_profesores = df_profesores["Nombre"].tolist()

# -------------------------
# SESSION STATE
# -------------------------

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

# -------------------------
# SELECCION PLANTA
# -------------------------

if st.session_state.planta is None:

    st.title("Sistema Control de Aseos")

    c1,c2 = st.columns(2)

    if c1.button("Planta Primera"):
        st.session_state.planta="Primera"
        st.rerun()

    if c2.button("Planta Segunda"):
        st.session_state.planta="Segunda"
        st.rerun()

    st.stop()

# -------------------------
# PANEL
# -------------------------

st.title(f"Panel Planta {st.session_state.planta}")

zonas = {
"NORTE":["Chicos Norte","Chicas Norte"],
"SUR":["Chicos Sur","Chicas Sur"]
}

for zona,banos in zonas.items():

    st.subheader(zona)

    col1,col2 = st.columns(2)

    for i,bano in enumerate(banos):

        cont = col1 if i==0 else col2

        with cont:

            st.markdown(f"### {bano}")

            ocupados = st.session_state.ocupacion[st.session_state.planta][bano]

            filas = []

            for i in range(2):

                if i < len(ocupados):

                    p = ocupados[i]

                    entrada = datetime.strptime(p["h_entrada"],"%H:%M")

                    ahora = datetime.now()

                    minutos = int((ahora - entrada.replace(year=ahora.year,month=ahora.month,day=ahora.day)).total_seconds()/60)

                    filas.append({
                        "Estado":"🔴",
                        "Alumno":p["alumno"],
                        "Curso":p["curso"],
                        "Min":minutos
                    })

                else:

                    filas.append({
                        "Estado":"🟢",
                        "Alumno":"",
                        "Curso":"",
                        "Min":""
                    })

            df = pd.DataFrame(filas)

            st.table(df)

            if len(ocupados) < 2:

                st.markdown("Registrar alumno")

                curso = st.selectbox("Curso", sorted(df_alumnos["Curso"].unique()), key=f"curso_{bano}")

                alumnos_disp = df_alumnos[df_alumnos["Curso"]==curso]["Nombre"].tolist()

                alumno = st.selectbox("Alumno", alumnos_disp, key=f"alumno_{bano}")

                profesor = st.selectbox("Profesor", lista_profesores, key=f"prof_{bano}")

                if st.button("Entrada", key=f"entrada_{bano}"):

                    st.session_state.ocupacion[st.session_state.planta][bano].append({

                        "alumno":alumno,
                        "curso":curso,
                        "profesor":profesor,
                        "h_entrada":datetime.now().strftime("%H:%M")
                    })

                    st.rerun()

            if len(ocupados) > 0:

                if st.button("Registrar salida", key=f"salida_{bano}"):

                    p = ocupados.pop()

                    conn = init_db()

                    conn.execute("""

                    INSERT INTO visitas
                    (planta,bano,alumno,curso,profesor,h_entrada,h_salida,estado,observaciones)

                    VALUES (?,?,?,?,?,?,?,?,?)

                    """,(

                        st.session_state.planta,
                        bano,
                        p["alumno"],
                        p["curso"],
                        p["profesor"],
                        p["h_entrada"],
                        datetime.now().strftime("%H:%M"),
                        "OK",
                        ""
                    ))

                    conn.commit()

                    df_nuevo = pd.DataFrame([{

                        "planta":st.session_state.planta,
                        "bano":bano,
                        "alumno":p["alumno"],
                        "curso":p["curso"],
                        "profesor":p["profesor"],
                        "h_entrada":p["h_entrada"],
                        "h_salida":datetime.now().strftime("%H:%M"),
                        "estado":"OK",
                        "observaciones":""

                    }])

                    subir_a_github(df_nuevo)

                    st.rerun()

# -------------------------
# HISTORICO
# -------------------------

st.header("Histórico")

conn = init_db()

df = pd.read_sql_query("SELECT * FROM visitas ORDER BY id DESC",conn)

st.dataframe(df,use_container_width=True)
