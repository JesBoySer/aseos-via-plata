import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
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

/* Contenedor principal del baño */
.bano-container {
    border: 1px solid #334155;
    border-radius: 10px;
    padding: 15px;
    background: #111827;
    margin-bottom: 20px;
}

/* Estilo para simular bordes de fila */
.fila-tabla {
    border-bottom: 1px solid #1E293B;
    padding-top: 10px;
    padding-bottom: 10px;
}

.header-tabla {
    border-bottom: 2px solid #38BDF8;
    padding-bottom: 5px;
    margin-bottom: 10px;
    font-weight: bold;
    color: #38BDF8;
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
# CARGA DATOS
# -------------------------

@st.cache_data
def cargar_datos():
    # Simulación de carga (asegúrate de que los archivos existan)
    try:
        alumnos = pd.read_csv("data/alumnos.csv")
        profesores = pd.read_csv("data/profesores.csv")
    except FileNotFoundError:
        alumnos = pd.DataFrame(columns=["Nombre", "Curso"])
        profesores = pd.DataFrame(columns=["Nombre"])
    return alumnos, profesores

df_alumnos, df_profesores = cargar_datos()
lista_profesores = df_profesores["Nombre"].tolist()

# -------------------------
# ESTADO
# -------------------------

if "planta" not in st.session_state:
    st.session_state.planta = None

if "ocupacion" not in st.session_state:
    st.session_state.ocupacion = {
        "Primera": {"Chicos Norte":[], "Chicas Norte":[], "Chicos Sur":[], "Chicas Sur":[]},
        "Segunda": {"Chicos Norte":[], "Chicas Norte":[], "Chicos Sur":[], "Chicas Sur":[]}
    }

if "editar" not in st.session_state:
    st.session_state.editar = {}

# -------------------------
# SIDEBAR
# -------------------------

with st.sidebar:
    st.title("🚾 SCA")
    if st.session_state.planta:
        st.success(f"Planta {st.session_state.planta}")
        if st.button("Cambiar planta"):
            st.session_state.planta = None
            st.rerun()

# -------------------------
# SELECCIÓN PLANTA
# -------------------------

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

# -------------------------
# PESTAÑAS
# -------------------------

tab_panel, tab_hist = st.tabs(["Panel", "Histórico"])

zonas = {
    "NORTE": ["Chicos Norte", "Chicas Norte"],
    "SUR": ["Chicos Sur", "Chicas Sur"]
}

# -------------------------
# PANEL
# -------------------------

with tab_panel:
    for zona, banos in zonas.items():
        st.subheader(f"ZONA {zona}")
        col1, col2 = st.columns(2)
        
        for i, bano in enumerate(banos):
            target_col = col1 if i == 0 else col2
            
            with target_col:
                # Envolvemos cada baño en un div con borde
                st.markdown(f'<div class="bano-container">', unsafe_allow_html=True)
                
                icono = "🚹" if "Chicos" in bano else "🚺"
                st.markdown(f"### {icono} {bano}")
                
                # Cabecera de la "tabla"
                st.markdown('<div class="header-tabla">', unsafe_allow_html=True)
                cab = st.columns([1,3,2,2,1,1])
                cab[0].write("Est.")
                cab[1].write("Alumno")
                cab[2].write("Curso")
                cab[3].write("Tiempo")
                cab[4].write("OK")
                cab[5].write("Fin")
                st.markdown('</div>', unsafe_allow_html=True)

                ocupados = st.session_state.ocupacion[st.session_state.planta][bano]

                # Filas (siempre 2 puestos por baño)
                for fila in range(2):
                    st.markdown('<div class="fila-tabla">', unsafe_allow_html=True)
                    cols = st.columns([1,3,2,2,1,1])
                    key = f"{bano}_{fila}_{st.session_state.planta}"

                    if fila < len(ocupados):
                        p = ocupados[fila]
                        h_ent = datetime.strptime(p["h_entrada"], "%H:%M")
                        ahora = datetime.now()
                        minutos = int((ahora - h_ent.replace(year=ahora.year, month=ahora.month, day=ahora.day)).total_seconds()/60)

                        cols[0].button("🔴", key=f"estado_{key}")
                        cols[1].write(f"**{p['alumno']}**")
                        cols[2].write(p["curso"])
                        cols[3].write(f"{minutos} min")
                        ok = cols[4].checkbox("", True, key=f"ok_{key}")
                        
                        if not ok:
                            obs = st.text_area("Observaciones", key=f"obs_{key}")
                        else:
                            obs = ""

                        if cols[5].button("Salir", key=f"fin_{key}"):
                            conn = init_db()
                            conn.execute("""
                                INSERT INTO visitas 
                                (planta,bano,alumno,curso,profesor,h_entrada,h_salida,estado,observaciones)
                                VALUES (?,?,?,?,?,?,?,?,?)
                            """, (
                                st.session_state.planta, bano, p["alumno"], p["curso"],
                                p["profesor"], p["h_entrada"], datetime.now().strftime("%H:%M"),
                                "OK" if ok else "Problema", obs
                            ))
                            conn.commit()
                            conn.close()
                            st.session_state.ocupacion[st.session_state.planta][bano].remove(p)
                            st.rerun()
                    else:
                        if key not in st.session_state.editar:
                            st.session_state.editar[key] = False
                        
                        if cols[0].button("🟢", key=f"libre_{key}"):
                            st.session_state.editar[key] = not st.session_state.editar[key]
                        
                        cols[1].write("*Disponible*")

                        if st.session_state.editar[key]:
                            with st.expander("Registrar Entrada", expanded=True):
                                cursos_disponibles = sorted(df_alumnos["Curso"].unique()) if not df_alumnos.empty else ["---"]
                                curso = st.selectbox("Curso", cursos_disponibles, key=f"curso_{key}")

                                alumnos_disponibles = df_alumnos[df_alumnos["Curso"]==curso]["Nombre"].tolist() if not df_alumnos.empty else ["---"]
                                alumno = st.selectbox("Alumno", alumnos_disponibles, key=f"alumno_{key}")

                                profesor = st.selectbox("Profesor", lista_profesores if lista_profesores else ["---"], key=f"prof_{key}")

                                if st.button("Registrar entrada", key=f"entrada_{key}"):
                                    st.session_state.ocupacion[st.session_state.planta][bano].append({
                                        "alumno": alumno,
                                        "curso": curso,
                                        "profesor": profesor,
                                        "h_entrada": datetime.now().strftime("%H:%M")
                                    })
                                    st.session_state.editar[key] = False
                                    st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True) # Cierre bano-container

# -------------------------
# HISTORICO
# -------------------------
with tab_hist:
    st.subheader("Histórico de visitas")
    conn = init_db()
    df = pd.read_sql_query("SELECT * FROM visitas ORDER BY id DESC", conn)
    conn.close()
    if df.empty:
        st.info("No hay visitas registradas")
    else:
        st.dataframe(df, use_container_width=True)
