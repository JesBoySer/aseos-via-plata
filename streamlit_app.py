import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="SCA - IES Vía de la Plata", layout="wide", page_icon="🚾")

# --- CSS DARK TOTAL ---
st.markdown("""
    <style>
    /* Fondo principal de la app */
    .stApp {
        background-color: #0f172a;
    }
    
    /* Caja de Zona (Norte/Sur) */
    .zona-container {
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 20px;
        background-color: #1e293b; /* Slate 800 */
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5);
        margin-bottom: 25px;
    }
    
    .zona-titulo {
        color: #3b82f6;
        font-weight: 800;
        font-size: 1.3rem;
        margin-bottom: 15px;
        text-align: center;
        border-bottom: 1px solid #334155;
        padding-bottom: 10px;
    }

    /* Estilo para los bloques de baños dentro de la zona */
    .bano-block {
        background-color: #0f172a;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #334155;
    }

    /* Alarma Parpadeante Dark */
    @keyframes pulse-red {
        0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); background-color: #450a0a; }
        70% { box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); background-color: #0f172a; }
        100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); background-color: #450a0a; }
    }
    .alerta-bano {
        animation: pulse-red 2s infinite;
        border: 1px solid #ef4444 !important;
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- BASE DE DATOS ---
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

# --- CARGA DE DATOS ---
@st.cache_data
def cargar_maestros():
    def leer(ruta):
        if not os.path.exists(ruta): return None
        try:
            df = pd.read_csv(ruta, sep=',', encoding='utf-8-sig')
            df.columns = [str(c).strip().replace('\ufeff', '') for c in df.columns]
            return df
        except: return None

    df_a = leer('data/alumnos.csv')
    df_p = leer('data/profesores.csv')
    
    if df_a is None: df_a = pd.DataFrame({'Nombre': ['Sin datos'], 'Curso': ['-']})
    lista_p = df_p['Nombre'].dropna().tolist() if df_p is not None else ['Guardia']
    return df_a, lista_p

df_alumnos, lista_profesores = cargar_maestros()

# --- LÓGICA ---
if 'planta' not in st.session_state: st.session_state.planta = None
zonas = {"NORTE": ["Chicos Norte", "Chicas Norte"], "SUR": ["Chicos Sur", "Chicas Sur"]}
if 'ocupacion' not in st.session_state:
    st.session_state.ocupacion = {bano: [] for z in zonas.values() for bano in z}

# --- UI ---
if st.session_state.planta is None:
    st.title("🚾 SCA - IES Vía de la Plata")
    c1, c2 = st.columns(2)
    if c1.button("🏢 PLANTA PRIMERA", use_container_width=True):
        st.session_state.planta = "Primera"; st.rerun()
    if c2.button("🏢 PLANTA SEGUNDA", use_container_width=True):
        st.session_state.planta = "Segunda"; st.rerun()
else:
    st.sidebar.subheader(f"📍 Planta {st.session_state.planta}")
    if st.sidebar.button("🔄 Cambiar Planta"):
        st.session_state.planta = None; st.rerun()

    t_mapa, t_stats = st.tabs(["🎮 Control", "📊 Histórico"])

    with t_mapa:
        for nombre_zona, lista_banos in zonas.items():
            st.markdown(f'<div class="zona-container"><div class="zona-titulo">📍 {nombre_zona}</div>', unsafe_allow_html=True)
            
            cols = st.columns(2)
            for idx, bano in enumerate(lista_banos):
                with cols[idx]:
                    st.markdown(f'<div class="bano-block">', unsafe_allow_html=True)
                    st.markdown(f"#### {bano}")
                    
                    ocupados = st.session_state.ocupacion[bano]
                    for p_idx, p in enumerate(ocupados):
                        # Cálculo de tiempo
                        h_ent = datetime.strptime(p['h_entrada'], "%H:%M")
                        h_act = datetime.strptime(datetime.now().strftime("%H:%M"), "%H:%M")
                        minutos = (h_act - h_ent).seconds // 60
                        
                        estilo = 'class="alerta-bano"' if minutos >= 10 else ''
                        
                        st.markdown(f'<div {estilo}>', unsafe_allow_html=True)
                        with st.expander(f"👤 {p['alumno']} ({minutos} min)", expanded=True):
                            ok = st.checkbox("OK", value=True, key=f"ok_{bano}_{p_idx}")
                            if st.button("Finalizar", key=f"f_{bano}_{p_idx}", use_container_width=True, type="primary"):
                                conn = init_db()
                                conn.execute("INSERT INTO visitas (planta, bano, alumno, curso, profesor, h_entrada, h_salida, estado_bano, observaciones) VALUES (?,?,?,?,?,?,?,?,?)",
                                            (st.session_state.planta, bano, p['alumno'], p['curso'], p['profesor'], p['h_entrada'], datetime.now().strftime("%H:%M"), "OK" if ok else "Problema", ""))
                                conn.commit(); conn.close()
                                st.session_state.ocupacion[bano].remove(p); st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

                    if len(ocupados) < 2:
                        with st.popover("➕ Entrada", use_container_width=True):
                            c = st.selectbox("Curso", sorted(df_alumnos['Curso'].unique()), key=f"cs_{bano}")
                            a = st.selectbox("Alumno", sorted(df_alumnos[df_alumnos['Curso']==c]['Nombre']), key=f"as_{bano}")
                            pr = st.selectbox("Autoriza", sorted(lista_profesores), key=f"ps_{bano}")
                            if st.button("Confirmar", key=f"cf_{bano}"):
                                st.session_state.ocupacion[bano].append({"alumno": a, "curso": c, "profesor": pr, "h_entrada": datetime.now().strftime("%H:%M")})
                                st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    with t_stats:
        conn = init_db()
        df_h = pd.read_sql_query("SELECT * FROM visitas", conn)
        conn.close()
        if not df_h.empty:
            st.dataframe(df_h, use_container_width=True)
            csv = df_h.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Descargar histórico CSV", csv, "historico.csv")
        else:
            st.info("No hay datos guardados aún.")