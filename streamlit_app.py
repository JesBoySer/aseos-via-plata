import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
from github import Github
from streamlit_autorefresh import st_autorefresh

st.set_page_config(
    page_title="SCA - IES Vía de la Plata",
    layout="wide",
    page_icon="🚾"
)

st_autorefresh(interval=30000, key="refresh")

# -------------------------
# ESTILOS
# -------------------------

st.markdown("""
<style>

.stApp{
background:#0B1120;
color:#E2E8F0;
}

h1,h2,h3,h4{
color:white;
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

.header-box{
border:2px solid #38BDF8;
padding:6px;
border-radius:6px;
text-align:center;
font-weight:bold;
background:#020617;
}

textarea{
background:#1E293B !important;
color:white !important;
height:150px !important;
}

</style>
""", unsafe_allow_html=True)

# -------------------------
# BASE DE DATOS
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
# GUARDAR EN GITHUB
# -------------------------

def save_to_github(df):

    csv_path="data/historico.csv"
    df.to_csv(csv_path,index=False)

    token=st.secrets["GITHUB_TOKEN"]
    repo_name=st.secrets["GITHUB_REPO"]

    g=Github(token)
    repo=g.get_repo(repo_name)

    contenido=open(csv_path,"rb").read()

    try:

        file=repo.get_contents("data/historico.csv")

        repo.update_file(
            "data/historico.csv",
            f"Actualizar histórico {datetime.now()}",
            contenido,
            file.sha
        )

    except:

        repo.create_file(
            "data/historico.csv",
            f"Crear histórico {datetime.now()}",
            contenido
        )


# -------------------------
# CARGA DATOS
# -------------------------

@st.cache_data
def cargar_datos():

    alumnos=pd.read_csv("data/alumnos.csv")
    profesores=pd.read_csv("data/profesores.csv")

    return alumnos,profesores


df_alumnos,df_profesores=cargar_datos()
lista_profesores=df_profesores["Nombre"].tolist()

# -------------------------
# ESTADO
# -------------------------

if "planta" not in st.session_state:
    st.session_state.planta=None

if "ocupacion" not in st.session_state:

    st.session_state.ocupacion={
        "Primera":{
            "Chicos Norte":[],
            "Chicas Norte":[],
            "Chicos Sur":[],
            "Chicas Sur":[]
        },
        "Segunda":{
            "Chicos Norte":[],
            "Chicas Norte":[],
            "Chicos Sur":[],
            "Chicas Sur":[]
        }
    }

if "editar" not in st.session_state:
    st.session_state.editar={}

# -------------------------
# SIDEBAR
# -------------------------

with st.sidebar:

    st.title("🚾 SCA")

    if st.session_state.planta:

        st.success(f"Planta {st.session_state.planta}")

        if st.button("Cambiar planta"):

            st.session_state.planta=None
            st.rerun()

# -------------------------
# SELECCIÓN PLANTA
# -------------------------

if st.session_state.planta is None:

    st.title("Sistema Control de Aseos")

    c1,c2=st.columns(2)

    if c1.button("Planta Primera",use_container_width=True):
        st.session_state.planta="Primera"
        st.rerun()

    if c2.button("Planta Segunda",use_container_width=True):
        st.session_state.planta="Segunda"
        st.rerun()

    st.stop()

# -------------------------
# PESTAÑAS
# -------------------------

tab_panel,tab_hist=st.tabs(["Panel","Histórico"])

zonas={
"NORTE":["Chicos Norte","Chicas Norte"],
"SUR":["Chicos Sur","Chicas Sur"]
}

# -------------------------
# PANEL
# -------------------------

with tab_panel:

    for zona,banos in zonas.items():

        st.subheader(zona)

        col1,col2=st.columns(2)

        for i,bano in enumerate(banos):

            cont=col1 if i==0 else col2

            with cont:

                st.markdown(f"### {bano}")

                cab=st.columns([1,3,2,2,1,1])

                cab[0].markdown('<div class="header-box">Estado</div>',unsafe_allow_html=True)
                cab[1].markdown('<div class="header-box">Alumno</div>',unsafe_allow_html=True)
                cab[2].markdown('<div class="header-box">Curso</div>',unsafe_allow_html=True)
                cab[3].markdown('<div class="header-box">Minutos</div>',unsafe_allow_html=True)
                cab[4].markdown('<div class="header-box">OK</div>',unsafe_allow_html=True)
                cab[5].markdown('<div class="header-box">Salida</div>',unsafe_allow_html=True)

                ocupados=st.session_state.ocupacion[st.session_state.planta][bano]

                for fila in range(2):

                    cols=st.columns([1,3,2,2,1,1])

                    key=f"{bano}_{fila}_{st.session_state.planta}"

                    if fila<len(ocupados):

                        p=ocupados[fila]

                        h_ent=datetime.strptime(p["h_entrada"],"%H:%M")
                        ahora=datetime.now()

                        minutos=int((ahora-h_ent.replace(
                        year=ahora.year,
                        month=ahora.month,
                        day=ahora.day)).total_seconds()/60)

                        cols[0].button("🔴",key=f"estado_{key}")

                        cols[1].write(p["alumno"])
                        cols[2].write(p["curso"])
                        cols[3].write(f"{minutos} min")

                        ok=cols[4].checkbox("",True,key=f"ok_{key}")

                        obs=""

                        if not ok:
                            obs=st.text_area("Observaciones",key=f"obs_{key}")

                        if cols[5].button("Salida",key=f"fin_{key}"):

                            conn=init_db()

                            conn.execute("""
                            INSERT INTO visitas
                            (planta,bano,alumno,curso,profesor,
                            h_entrada,h_salida,estado,observaciones)
                            VALUES (?,?,?,?,?,?,?,?,?)
                            """,
                            (
                            st.session_state.planta,
                            bano,
                            p["alumno"],
                            p["curso"],
                            p["profesor"],
                            p["h_entrada"],
                            datetime.now().strftime("%H:%M"),
                            "OK" if ok else "Problema",
                            obs
                            ))

                            conn.commit()

                            df=pd.read_sql_query("SELECT * FROM visitas",conn)
                            conn.close()

                            save_to_github(df)

                            st.session_state.ocupacion[
                            st.session_state.planta][bano].remove(p)

                            st.rerun()

                    else:

                        if key not in st.session_state.editar:
                            st.session_state.editar[key]=False

                        if cols[0].button("🟢",key=f"libre_{key}"):

                            st.session_state.editar[key]=not st.session_state.editar[key]

                        if st.session_state.editar[key]:

                            curso=st.selectbox(
                            "Curso",
                            sorted(df_alumnos["Curso"].unique()),
                            key=f"curso_{key}"
                            )

                            alumno=st.selectbox(
                            "Alumno",
                            df_alumnos[df_alumnos["Curso"]==curso]["Nombre"],
                            key=f"alumno_{key}"
                            )

                            profesor=st.selectbox(
                            "Profesor",
                            lista_profesores,
                            key=f"prof_{key}"
                            )

                            if st.button("Registrar entrada",key=f"entrada_{key}"):

                                st.session_state.ocupacion[
                                st.session_state.planta][bano].append({

                                "alumno":alumno,
                                "curso":curso,
                                "profesor":profesor,
                                "h_entrada":datetime.now().strftime("%H:%M")

                                })

                                st.session_state.editar[key]=False
                                st.rerun()

# -------------------------
# HISTORICO
# -------------------------

with tab_hist:

    st.subheader("Histórico de visitas")

    conn=init_db()

    df=pd.read_sql_query("""
    SELECT *,
    (strftime('%s',h_salida)-strftime('%s',h_entrada))/60 AS minutos
    FROM visitas
    ORDER BY id DESC
    """,conn)

    conn.close()

    if len(df)==0:
        st.info("No hay visitas registradas")
    else:
        st.dataframe(df,use_container_width=True)
