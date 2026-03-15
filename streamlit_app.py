import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="SCA - IES Vía de la Plata", layout="wide", page_icon="🚾")

# --- INYECCIÓN DE CSS PARA DISEÑO AVANZADO ---
st.markdown("""
    <style>
    .zona-card {
        background-color: #f0f2f6;
        border-radius: 15px;
        padding: 20px;
        border: 2px solid #e0e0e0;
        margin-bottom: 20px;
    }
    .ordenanza-panel {
        background-color: #ffffff;
        border: 2px dashed #3498db;
        border-radius: 15px;
        padding: 15px;
        text-align: center;
        margin: 20px 0px;
    }
    .stButton>button {
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES DE CARGA Y DB (Mantener las que ya tienes) ---
def init_db():
    if not os.path.exists('data'): os.makedirs('data')
    conn = sqlite3.connect('data/historico.sqlite')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS visitas 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, planta TEXT, bano TEXT, 
                  alumno TEXT, curso TEXT, profesor TEXT, h_entrada TEXT, 
                  h_salida TEXT, estado_bano TEXT, observaciones TEXT)''')
    conn.commit()
    return conn

@st.cache_data
def cargar_maestros():
    def leer_csv_perfecto(ruta):
        if not os.path.exists(ruta): return None
        try:
            df = pd.read_csv(ruta, sep=',', encoding='utf-8-sig', engine='python')
        except UnicodeDecodeError:
            df = pd.read_csv(ruta, sep=',', encoding='latin-1', engine='python')
        df.columns = [str(c).strip().replace('\ufeff', '') for c in df.columns]
        return df
    df_alumnos = leer_csv_perfecto('data/alumnos.csv')
    if df_alumnos is None or 'Curso' not in df_alumnos.columns:
        df_alumnos = pd.DataFrame({'Nombre': ['Error'], 'Curso': ['REVISAR']})
    df_prof = leer_csv_perfecto('data/profesores.csv')
    df_profesores = df_prof['Nombre'].dropna().tolist() if df_prof is not None else ['Profesor Prueba']
    return df_alumnos, df_profesores

df_alumnos, lista_profesores = cargar_maestros()

if 'planta' not in st.session_state: st.session_state.planta = None

# Definición física de los baños: 2 zonas x 2 géneros
zonas = {
    "NORTE": ["Chicos Norte", "Chicas Norte"],
    "SUR": ["Chicos Sur", "Chicas Sur"]
}

if 'ocupacion' not in st.session_state:
    st.session_state.ocupacion = {bano: [] for zona in zonas.values() for bano in zona}

# --- INTERFAZ ---
if st.session_state.planta is None:
    st.title("🏛️ Control de Accesos - IES Vía de la Plata")
    col_p1, col_p2 = st.columns(2)
    if col_p1.button("🏢 PLANTA PRIMERA", use_container_width=True):
        st.session_state.planta = "Primera"; st.rerun()
    if col_p2.button("🏢 PLANTA SEGUNDA", use_container_width=True):
        st.session_state.planta = "Segunda"; st.rerun()
else:
    st.sidebar.title(f"📍 Planta {st.session_state.planta}")
    if st.sidebar.button("🔄 Cambiar Planta"):
        st.session_state.planta = None; st.rerun()

    tab_ctrl, tab_hist = st.tabs(["🎮 Panel de Control (Mapa)", "📊 Estadísticas"])

    with tab_ctrl:
        # --- ZONA NORTE ---
        st.markdown('<div class="zona-card">', unsafe_allow_html=True)
        st.markdown("### ❄️ ZONA NORTE (Extremo Pasillo)")
        col_n1, col_n2 = st.columns(2)
        
        for i, nombre_bano in enumerate(zonas["NORTE"]):
            with [col_n1, col_n2][i]:
                # Lógica de renderizado de baño (Simplificada para el ejemplo)
                ocupados = st.session_state.ocupacion[nombre_bano]
                st.subheader(f"🚹 {nombre_bano}" if "Chicos" in nombre_bano else f"🚺 {nombre_bano}")
                
                for p_idx, p in enumerate(ocupados):
                    with st.expander(f"👤 {p['alumno']}", expanded=True):
                        if st.button("Liberar", key=f"lib_{nombre_bano}_{p_idx}", use_container_width=True):
                            conn = init_db(); conn.execute("INSERT INTO visitas ... VALUES ...") # (Tu lógica de guardado)
                            st.session_state.ocupacion[nombre_bano].remove(p); st.rerun()
                
                if len(ocupados) < 2:
                    with st.popover("➕ Entrada"):
                        c = st.selectbox("Curso", sorted(df_alumnos['Curso'].unique()), key=f"c_{nombre_bano}")
                        a = st.selectbox("Alumno", sorted(df_alumnos[df_alumnos['Curso']==c]['Nombre']), key=f"a_{nombre_bano}")
                        pr = st.selectbox("Autoriza", sorted(lista_profesores), key=f"p_{nombre_bano}")
                        if st.button("Confirmar", key=f"conf_{nombre_bano}"):
                            st.session_state.ocupacion[nombre_bano].append({"alumno": a, "curso": c, "profesor": pr, "h_entrada": datetime.now().strftime("%H:%M")})
                            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # --- ZONA ORDENANZAS (CENTRO) ---
        st.markdown('<div class="ordenanza-panel">', unsafe_allow_html=True)
        st.markdown(f"### 👮 PUESTO DE CONTROL CENTRAL - PLANTA {st.session_state.planta.upper()}")
        t_total = sum(len(v) for v in st.session_state.ocupacion.values())
        st.write(f"Alumnos fuera actualmente: **{t_total}**")
        st.markdown('</div>', unsafe_allow_html=True)

        # --- ZONA SUR ---
        st.markdown('<div class="zona-card">', unsafe_allow_html=True)
        st.markdown("### ☀️ ZONA SUR (Extremo Pasillo)")
        col_s1, col_s2 = st.columns(2)
        
        for i, nombre_bano in enumerate(zonas["SUR"]):
            with [col_s1, col_s2][i]:
                ocupados = st.session_state.ocupacion[nombre_bano]
                st.subheader(f"🚹 {nombre_bano}" if "Chicos" in nombre_bano else f"🚺 {nombre_bano}")
                
                for p_idx, p in enumerate(ocupados):
                    with st.expander(f"👤 {p['alumno']}", expanded=True):
                        if st.button("Liberar", key=f"lib_{nombre_bano}_{p_idx}", use_container_width=True):
                            # (Tu lógica de guardado aquí)
                            st.session_state.ocupacion[nombre_bano].remove(p); st.rerun()
                
                if len(ocupados) < 2:
                    with st.popover("➕ Entrada"):
                        c = st.selectbox("Curso", sorted(df_alumnos['Curso'].unique()), key=f"c_{nombre_bano}")
                        a = st.selectbox("Alumno", sorted(df_alumnos[df_alumnos['Curso']==c]['Nombre']), key=f"a_{nombre_bano}")
                        pr = st.selectbox("Autoriza", sorted(lista_profesores), key=f"p_{nombre_bano}")
                        if st.button("Confirmar", key=f"conf_{nombre_bano}"):
                            st.session_state.ocupacion[nombre_bano].append({"alumno": a, "curso": c, "profesor": pr, "h_entrada": datetime.now().strftime("%H:%M")})
                            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with tab_hist:
        # (Aquí va tu código de estadísticas)
        st.write("Estadísticas de acceso...")