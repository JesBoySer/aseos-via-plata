import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
from github import Github
from streamlit_autorefresh import st_autorefresh

st_autorefresh(interval=30000, key="refresh")  # refresco automático

# --- Configuración ---
st.set_page_config(page_title="SCA - IES Vía de la Plata", layout="wide", page_icon="🚾")

# --- CSS simplificado para botones y textarea ---
st.markdown("""
<style>
.stApp {background:#0B1120;color:#E2E8F0;font-family:'Inter',sans-serif;}
.stButton>button {color:#F8FAFC;font-weight:700; background: #1E293B; border: 2px solid #38BDF8; border-radius:12px; padding:0.5rem 1rem;}
.stButton>button:hover {background:#2563EB; color:white; border-color:#7DD3FC;}
input[type="checkbox"]:checked{accent-color:#22C55E;}
textarea{border-radius:8px;background:#1E293B;color:white;width:100%;height:120px;padding:5px;}
</style>
""", unsafe_allow_html=True)

# --- Base de datos local ---
def init_db():
    if not os.path.exists('data'):
        os.makedirs('data')
    db_path = 'data/historico.sqlite'
    conn = sqlite3.connect(db_path)
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

# --- Guardar CSV local y push a GitHub ---
def save_to_github(df):
    # Guardar localmente
    csv_path = "data/historico.csv"
    df.to_csv(csv_path, index=False)
    
    # Conectar con GitHub
    token = st.secrets["GITHUB_TOKEN"]
    repo_name = st.secrets["GITHUB_REPO"]  # ej: "usuario/aseos-via-plata"
    g = Github(token)
    repo = g.get_repo(repo_name)
    
    # Leer archivo actual en GitHub
    try:
        contents = repo.get_contents("data/historico.csv")
        repo.update_file(contents.path, f"Actualizar histórico {datetime.now()}", open(csv_path,"rb").read(), contents.sha)
    except:
        # Si no existe, crear
        repo.create_file("data/historico.csv", f"Crear histórico {datetime.now()}", open(csv_path,"rb").read())

# --- Carga CSV de alumnos y profesores ---
@st.cache_data
def cargar_maestros():
    def leer_csv_robusto(ruta):
        if not os.path.exists(ruta): return pd.DataFrame({'Nombre':['Error'],'Curso':['-']})
        try: df = pd.read_csv(ruta, sep=',', encoding='utf-8-sig')
        except: df = pd.read_csv(ruta, sep=',', encoding='latin-1')
        df.columns=[c.strip() for c in df.columns]
        return df
    df_alumnos = leer_csv_robusto('data/alumnos.csv')
    df_prof = leer_csv_robusto('data/profesores.csv')
    lista_prof = df_prof['Nombre'].dropna().tolist() if 'Nombre' in df_prof.columns else ['Profesor de Guardia']
    return df_alumnos, lista_prof

df_alumnos, lista_profesores = cargar_maestros()

# --- Estado inicial ---
if 'planta' not in st.session_state: st.session_state.planta=None
if 'ocupacion' not in st.session_state: st.session_state.ocupacion = {}
if 'editar' not in st.session_state: st.session_state.editar = {}
zonas_fisicas={"NORTE":["Chicos Norte","Chicas Norte"],"SUR":["Chicos Sur","Chicas Sur"]}
for planta in ["Primera","Segunda"]:
    if planta not in st.session_state.ocupacion:
        st.session_state.ocupacion[planta]={}
        for b in [b for z in zonas_fisicas.values() for b in z]:
            st.session_state.ocupacion[planta][b]=[]

# --- Sidebar ---
with st.sidebar:
    st.title("🚾 SCA")
    st.markdown("---")
    if st.session_state.planta is None: st.info("Selecciona planta")
    else:
        st.success(f"Planta {st.session_state.planta}")
        if st.button("Cambiar planta"):
            st.session_state.planta=None
            st.rerun()

# --- Selección de planta ---
if st.session_state.planta is None:
    st.title("SCA - Control de Aseos")
    c1,c2=st.columns(2)
    if c1.button("🏢 Planta Primera",use_container_width=True):
        st.session_state.planta="Primera"; st.rerun()
    if c2.button("🏢 Planta Segunda",use_container_width=True):
        st.session_state.planta="Segunda"; st.rerun()

# --- Panel principal ---
else:
    tab_mapa, tab_stats = st.tabs(["Panel","Histórico"])
    with tab_mapa:
        for zona,banos in zonas_fisicas.items():
            st.markdown(f"### {zona}")
            col1,col2 = st.columns(2)
            for idx,bano in enumerate(banos):
                cont = col1 if idx==0 else col2
                with cont:
                    st.markdown(f"#### {bano}")
                    ocupados = st.session_state.ocupacion[st.session_state.planta][bano]
                    num = len(ocupados)
                    # Dos filas por baño
                    for i in range(2):
                        fila = st.columns([1.2,3,2,2,1,1])
                        key_fila=f"{bano}_{i}_{st.session_state.planta}"
                        if i<num:
                            p=ocupados[i]
                            h_ent=datetime.strptime(p['h_entrada'],"%H:%M")
                            ahora=datetime.now()
                            h_real=ahora.replace(hour=h_ent.hour,minute=h_ent.minute)
                            minutos=int((ahora-h_real).total_seconds()/60)
                            estado_emoji = "🔴"
                            if fila[0].button(estado_emoji,key=f"info_{key_fila}"):
                                st.info(f"Alumno: {p['alumno']}\nCurso: {p['curso']}\nProfesor: {p['profesor']}\nEntrada: {p['h_entrada']}")
                            fila[1].markdown(f"**{p['alumno']}**")
                            fila[2].markdown(p['curso'])
                            fila[3].markdown(f"{minutos} min")
                            ok_val=fila[4].checkbox("",True,key=f"ok_{key_fila}")
                            obs=""
                            if not ok_val:
                                obs=fila[4].text_area("Observaciones",key=f"obs_{key_fila}",height=120)
                            if fila[5].button("Salida",key=f"fin_{key_fila}"):
                                conn=init_db()
                                conn.execute(
                                    """INSERT INTO visitas
                                    (planta,bano,alumno,curso,profesor,h_entrada,h_salida,estado_bano,observaciones)
                                    VALUES (?,?,?,?,?,?,?,?,?)""",
                                    (st.session_state.planta,bano,p['alumno'],p['curso'],p['profesor'],
                                     p['h_entrada'],datetime.now().strftime("%H:%M"),
                                     "OK" if ok_val else "Problema", obs)
                                )
                                conn.commit(); conn.close()
                                df_hist=pd.read_sql_query("SELECT * FROM visitas ORDER BY id ASC",init_db())
                                save_to_github(df_hist)
                                st.session_state.ocupacion[st.session_state.planta][bano].remove(p)
                                st.rerun()
                        else:
                            if key_fila not in st.session_state.editar: st.session_state.editar[key_fila]=False
                            if fila[0].button("🟢",key=f"libre_{key_fila}"):
                                st.session_state.editar[key_fila] = not st.session_state.editar[key_fila]
                            fila[1].markdown("-"); fila[2].markdown("-"); fila[3].markdown("-")
                            fila[4].markdown("-"); fila[5].markdown("-")
                            if st.session_state.editar[key_fila]:
                                curso_sel = st.selectbox("Curso",[""]+sorted(df_alumnos['Curso'].unique()),key=f"curso_{key_fila}",format_func=lambda x:"Curso" if x=="" else x)
                                alumno_sel=st.selectbox("Alumno",[""]+sorted(df_alumnos[df_alumnos['Curso']==curso_sel]['Nombre']) if curso_sel else [""],key=f"alumno_{key_fila}",format_func=lambda x:"Alumno" if x=="" else x)
                                prof_sel=st.selectbox("Profesor",[""]+lista_profesores,key=f"prof_{key_fila}",format_func=lambda x:"Profesor" if x=="" else x)
                                if st.button("Registrar Entrada",key=f"entrada_new_{key_fila}"):
                                    if alumno_sel and curso_sel and prof_sel:
                                        st.session_state.ocupacion[st.session_state.planta][bano].append({
                                            "alumno":alumno_sel,
                                            "curso":curso_sel,
                                            "profesor":prof_sel,
                                            "h_entrada":datetime.now().strftime("%H:%M")
                                        })
                                        st.session_state.editar[key_fila]=False
                                        st.rerun()

    with tab_stats:
        st.subheader("Histórico CSV / GitHub")
        st.info("Todas las visitas se guardan en GitHub automáticamente en `data/historico.csv`.")
