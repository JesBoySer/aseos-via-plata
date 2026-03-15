import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# ---------------------------------------------------
# REFRESCO AUTOMÁTICO (cada 30 segundos)
# ---------------------------------------------------

st_autorefresh(interval=30000, key="refresh")

# ---------------------------------------------------
# CONFIGURACIÓN
# ---------------------------------------------------

st.set_page_config(
    page_title="SCA - IES Vía de la Plata",
    layout="wide",
    page_icon="🚾"
)

# ---------------------------------------------------
# ESTILOS
# ---------------------------------------------------

st.markdown("""
<style>

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

.stApp{
    background:#0B1120;
    color:#E2E8F0;
    font-family:'Inter',sans-serif;
}

.zona-titulo{
    font-size:1.6rem;
    font-weight:800;
    color:#38BDF8;
    border-bottom:2px solid #38BDF8;
    margin-top:10px;
    margin-bottom:20px;
}

.bano-card{
    background:#0F172A;
    padding:18px;
    border-radius:18px;
    border:1px solid #334155;
    margin-bottom:16px;
}

input[type="checkbox"]:checked{
    accent-color:#22C55E;
}

</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------
# BASE DE DATOS
# ---------------------------------------------------

def init_db():

    if not os.path.exists('data'):
        os.makedirs('data')

    conn = sqlite3.connect('data/historico.sqlite')

    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS visitas 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 planta TEXT,
                 bano TEXT,
                 alumno TEXT,
                 curso TEXT,
                 profesor TEXT,
                 h_entrada TEXT,
                 h_salida TEXT,
                 estado_bano TEXT,
                 observaciones TEXT)''')

    conn.commit()

    return conn

# ---------------------------------------------------
# CARGA CSV
# ---------------------------------------------------

@st.cache_data
def cargar_maestros():

    def leer_csv_robusto(ruta):

        if not os.path.exists(ruta):
            return None

        try:
            df = pd.read_csv(ruta, sep=',', encoding='utf-8-sig')
        except:
            df = pd.read_csv(ruta, sep=',', encoding='latin-1')

        df.columns=[c.strip() for c in df.columns]

        return df

    df_alumnos=leer_csv_robusto('data/alumnos.csv')

    if df_alumnos is None:
        df_alumnos=pd.DataFrame({'Nombre':['Error'],'Curso':['-']})

    df_prof=leer_csv_robusto('data/profesores.csv')

    if df_prof is not None and 'Nombre' in df_prof.columns:
        lista_prof=df_prof['Nombre'].dropna().tolist()
    else:
        lista_prof=['Profesor de Guardia']

    return df_alumnos, lista_prof


df_alumnos, lista_profesores = cargar_maestros()

# ---------------------------------------------------
# ESTADO
# ---------------------------------------------------

if 'planta' not in st.session_state:
    st.session_state.planta=None

zonas_fisicas={
"NORTE":["Chicos Norte","Chicas Norte"],
"SUR":["Chicos Sur","Chicas Sur"]
}

if 'ocupacion' not in st.session_state:
    st.session_state.ocupacion={
        b:[] for zona in zonas_fisicas.values() for b in zona
    }

# ---------------------------------------------------
# SIDEBAR
# ---------------------------------------------------

with st.sidebar:

    st.title("🚾 SCA")

    st.markdown("---")

    if st.session_state.planta is None:
        st.info("Selecciona planta")
    else:
        st.success(f"Planta {st.session_state.planta}")

        if st.button("Cambiar planta"):
            st.session_state.planta=None
            st.rerun()

# ---------------------------------------------------
# SELECCIÓN PLANTA
# ---------------------------------------------------

if st.session_state.planta is None:

    st.title("SCA - Control de Aseos")

    c1,c2=st.columns(2)

    if c1.button("🏢 Planta Primera",use_container_width=True):
        st.session_state.planta="Primera"
        st.rerun()

    if c2.button("🏢 Planta Segunda",use_container_width=True):
        st.session_state.planta="Segunda"
        st.rerun()

# ---------------------------------------------------
# PANEL
# ---------------------------------------------------

else:

    tab_mapa, tab_stats = st.tabs(["Panel", "Histórico"])

    with tab_mapa:

        for zona,banos in zonas_fisicas.items():

            st.markdown(f'<div class="zona-titulo">{zona}</div>',unsafe_allow_html=True)

            col1,col2=st.columns(2)

            for idx,bano in enumerate(banos):

                cont = col1 if idx==0 else col2

                with cont:

                    icono="🚹" if "Chicos" in bano else "🚺"

                    ocupados=st.session_state.ocupacion[bano]
                    num=len(ocupados)

                    st.markdown('<div class="bano-card">',unsafe_allow_html=True)

                    st.subheader(f"{icono} {bano}")

                    # BOLAS ESTADO

                    bolas=st.columns(2)

                    for i in range(2):

                        if i < num:
                            bolas[i].markdown("🔴")
                        else:
                            bolas[i].markdown("🟢")

                    st.markdown("---")

                    # CABECERA

                    cab=st.columns([3,2,1,1,1])

                    cab[0].markdown("**Alumno**")
                    cab[1].markdown("**Curso**")
                    cab[2].markdown("**Tiempo**")
                    cab[3].markdown("**OK**")
                    cab[4].markdown("**Salida**")

                    for p_idx,p in enumerate(ocupados):

                        h_ent=datetime.strptime(p['h_entrada'],"%H:%M")
                        ahora=datetime.now()
                        h_real=ahora.replace(hour=h_ent.hour,minute=h_ent.minute)

                        minutos=int((ahora-h_real).total_seconds()/60)

                        fila=st.columns([3,2,1,1,1])

                        fila[0].markdown(f"**{p['alumno']}**")
                        fila[1].markdown(p['curso'])
                        fila[2].markdown(f"{minutos} min")

                        ok=fila[3].checkbox("",True,key=f"ok{bano}{p_idx}")

                        if fila[4].button("Salida",key=f"fin{bano}{p_idx}"):

                            conn=init_db()

                            conn.execute(
                            """INSERT INTO visitas
                            (planta,bano,alumno,curso,profesor,h_entrada,h_salida,estado_bano,observaciones)
                            VALUES (?,?,?,?,?,?,?,?,?)""",
                            (
                            st.session_state.planta,
                            bano,
                            p['alumno'],
                            p['curso'],
                            p['profesor'],
                            p['h_entrada'],
                            datetime.now().strftime("%H:%M"),
                            "OK" if ok else "Problema",
                            ""
                            )
                            )

                            conn.commit()
                            conn.close()

                            st.session_state.ocupacion[bano].remove(p)

                            st.rerun()

                    st.markdown("---")

                    cols_entrada=st.columns(2)

                    for plaza in range(2):

                        if plaza >= num:

                            with cols_entrada[plaza]:

                                with st.popover(f"➕ Entrada {plaza+1}"):

                                    cursos=sorted(df_alumnos['Curso'].unique())

                                    curso=st.selectbox("Curso",cursos,key=bano+f"c{plaza}")

                                    alumnos=df_alumnos[df_alumnos['Curso']==curso]['Nombre']

                                    alumno=st.selectbox("Alumno",sorted(alumnos),key=bano+f"a{plaza}")

                                    prof=st.selectbox("Autoriza",lista_profesores,key=bano+f"p{plaza}")

                                    if st.button("Registrar entrada",key=bano+f"ok{plaza}"):

                                        st.session_state.ocupacion[bano].append({

                                        "alumno":alumno,
                                        "curso":curso,
                                        "profesor":prof,
                                        "h_entrada":datetime.now().strftime("%H:%M")

                                        })

                                        st.rerun()

                    st.markdown('</div>',unsafe_allow_html=True)

    # HISTÓRICO

    with tab_stats:

        conn=init_db()
        df=pd.read_sql_query("SELECT * FROM visitas ORDER BY id DESC",conn)
        conn.close()

        if not df.empty:

            st.dataframe(df,use_container_width=True)

            csv=df.to_csv(index=False).encode('utf-8')

            st.download_button(
                "Descargar CSV",
                csv,
                "historico.csv",
                "text/csv"
            )

        else:
            st.info("No hay registros aún")
