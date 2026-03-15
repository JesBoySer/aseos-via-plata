import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="SCA - IES Vía de la Plata", layout="wide", page_icon="🚾")

# --- INYECCIÓN DE ESTILO DARK TAILWIND ---
st.markdown("""
    <style>
    /* Contenedor Principal de Zona */
    .zona-container {
        border: 1px solid #374151;
        border-radius: 0.75rem;
        padding: 1.5rem;
        background-color: #1f2937; /* Slate-800 */
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.4);
        margin-bottom: 2rem;
    }
    
    /* Títulos de Zona */
    .zona-titulo {
        color: #f3f4f6;
        font-size: 1.1rem;
        font-weight: 700;
        border-left: 4px solid #3b82f6; /* Acento azul a la izquierda */
        padding-left: 1rem;
        margin-bottom: 1.5rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Animación de Alerta para Modo Oscuro */
    @keyframes blink-dark {
        0% { background-color: #7f1d1d; border-color: #ef4444; } /* Rojo oscuro */
        50% { background-color: #1f2937; border-color: #374151; }
        100% { background-color: #7f1d1d; border-color: #ef4444; }
    }
    
    .alerta-bano-dark {
        animation: blink-dark 2s infinite;
        border: 2px solid #ef4444 !important;
        border-radius: 0.5rem;
        padding: 10px;
        margin-bottom: 5px;
    }

    /* Ajuste de los expanders para que no desentonen */
    .streamlit-expanderHeader {
        background-color: #374151 !important;
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CARGA DE DATOS (Sin cambios en la lógica) ---
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
        except:
            df = pd.read_csv(ruta, sep=',', encoding='latin-1', engine='python')
        df.columns = [str(c).strip().replace('\ufeff', '') for c in df.columns]
        return df
    df_alumnos = leer_csv_perfecto('data/alumnos.csv')
    df_p = leer_csv_perfecto('data/profesores.csv')
    lista_p = df_p['Nombre'].dropna().tolist() if df_p is not None else ['Prof. Guardia']
    return df_alumnos, lista_p

df_alumnos, lista_profesores = cargar_maestros()

if 'planta' not in st.session_state: st.session_state.planta = None

zonas_fisicas = {
    "ZONA NORTE": ["Chicos Norte", "Chicas Norte"],
    "ZONA SUR": ["Chicos Sur", "Chicas Sur"]
}

if 'ocupacion' not in st.session_state:
    st.session_state.ocupacion = {bano: [] for zona in zonas_fisicas.values() for bano in zona}

# --- INTERFAZ ---
if st.session_state.planta is None:
    st.title("🏛️ SCA - IES Vía de la Plata")
    st.subheader("Selección de Planta")
    c1, c2 = st.columns(2)
    if c1.button("🏢 PLANTA PRIMERA", use_container_width=True):
        st.session_state.planta = "Primera"; st.rerun()
    if c2.button("🏢 PLANTA SEGUNDA", use_container_width=True):
        st.session_state.planta = "Segunda"; st.rerun()
else:
    st.sidebar.markdown(f"### 📍 Planta {st.session_state.planta}")
    if st.sidebar.button("🔄 Cambiar Planta"):
        st.session_state.planta = None; st.rerun()

    tab_mapa, tab_stats = st.tabs(["🎮 Panel de Control", "📊 Estadísticas"])

    with tab_mapa:
        for nombre_zona, lista_banos in zonas_fisicas.items():
            # Contenedor de Zona con estilo Dark
            st.markdown(f'<div class="zona-container"><div class="zona-titulo">{nombre_zona}</div>', unsafe_allow_html=True)
            
            cols = st.columns(2)
            for idx_b, bano in enumerate(lista_banos):
                with cols[idx_b]:
                    st.markdown(f"#### 🚻 {bano}")
                    ocupados = st.session_state.ocupacion[bano]
                    
                    for p_idx, p in enumerate(ocupados):
                        # Lógica de tiempo
                        h_ent = datetime.strptime(p['h_entrada'], "%H:%M")
                        h_act = datetime.strptime(datetime.now().strftime("%H:%M"), "%H:%M")
                        diff = (h_act - h_ent).seconds / 60
                        
                        # Clase de alerta si pasa de 10 min
                        clase_alerta = 'class="alerta-bano-dark"' if diff >= 10 else ""
                        
                        st.markdown(f'<div {clase_alerta}>', unsafe_allow_html=True)
                        with st.expander(f"👤 {p['alumno']} ({int(diff)} min)", expanded=True):
                            ok = st.checkbox("Baño OK", value=True, key=f"ok_{bano}_{p_idx}")
                            obs = st.text_input("Obs", key=f"obs_{bano}_{p_idx}")
                            if st.button("Finalizar", key=f"f_{bano}_{p_idx}", use_container_width=True, type="primary"):
                                conn = init_db()
                                conn.execute("INSERT INTO visitas (planta, bano, alumno, curso, profesor, h_entrada, h_salida, estado_bano, observaciones) VALUES (?,?,?,?,?,?,?,?,?)",
                                            (st.session_state.planta, bano, p['alumno'], p['curso'], p['profesor'], p['h_entrada'], datetime.now().strftime("%H:%M"), "OK" if ok else "Problema", obs))
                                conn.commit(); conn.close()
                                st.session_state.ocupacion[bano].remove(p); st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

                    if len(ocupados) < 2:
                        with st.popover(f"➕ Registrar", use_container_width=True):
                            c_sel = st.selectbox("Curso", sorted(df_alumnos['Curso'].unique()), key=f"c_{bano}")
                            a_sel = st.selectbox("Alumno", sorted(df_alumnos[df_alumnos['Curso']==c_sel]['Nombre']), key=f"a_{bano}")
                            p_sel = st.selectbox("Autoriza", sorted(lista_profesores), key=f"p_{bano}")
                            if st.button("Confirmar", key=f"conf_{bano}", use_container_width=True):
                                st.session_state.ocupacion[bano].append({"alumno": a_sel, "curso": c_sel, "profesor": p_sel, "h_entrada": datetime.now().strftime("%H:%M")})
                                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    with tab_stats:
        # Tu lógica de estadísticas habitual
        st.write("Historial de acceso...")