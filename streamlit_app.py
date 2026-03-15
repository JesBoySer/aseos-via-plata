import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime, timedelta
import time

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="SCA - IES Vía de la Plata", layout="wide", page_icon="🚾")

# --- INYECCIÓN DE ESTILO (Simulación de Tailwind + Alarma) ---
st.markdown("""
    <style>
    /* Estilo tipo Tailwind para las zonas */
    .zona-container {
        border: 1px solid #e5e7eb;
        border-radius: 0.75rem;
        padding: 1.5rem;
        background-color: #ffffff;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        margin-bottom: 2rem;
    }
    .zona-titulo {
        color: #111827;
        font-size: 1.25rem;
        font-weight: 700;
        border-bottom: 2px solid #3b82f6;
        padding-bottom: 0.5rem;
        margin-bottom: 1.5rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Animación de alerta roja parpadeante */
    @keyframes blink {
        0% { background-color: #fee2e2; border-color: #ef4444; }
        50% { background-color: #ffffff; border-color: #e5e7eb; }
        100% { background-color: #fee2e2; border-color: #ef4444; }
    }
    .alerta-bano {
        animation: blink 1.5s infinite;
        border: 2px solid #ef4444 !important;
        border-radius: 0.5rem;
        padding: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNCIONES DE PERSISTENCIA Y CARGA ---
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
    
    df_p = leer_csv_perfecto('data/profesores.csv')
    lista_p = df_p['Nombre'].dropna().tolist() if df_p is not None else ['Profesor Guardia']
    return df_alumnos, lista_p

df_alumnos, lista_profesores = cargar_maestros()

# --- LÓGICA DE ESTADO ---
if 'planta' not in st.session_state: st.session_state.planta = None

zonas_fisicas = {
    "ZONA NORTE": ["Chicos Norte", "Chicas Norte"],
    "ZONA SUR": ["Chicos Sur", "Chicas Sur"]
}

if 'ocupacion' not in st.session_state:
    st.session_state.ocupacion = {bano: [] for zona in zonas_fisicas.values() for bano in zona}

# --- INTERFAZ ---
if st.session_state.planta is None:
    st.title("🏛️ Control de Accesos - IES Vía de la Plata")
    col1, col2 = st.columns(2)
    if col1.button("🏢 PLANTA PRIMERA", use_container_width=True):
        st.session_state.planta = "Primera"; st.rerun()
    if col2.button("🏢 PLANTA SEGUNDA", use_container_width=True):
        st.session_state.planta = "Segunda"; st.rerun()
else:
    st.sidebar.title(f"📍 Planta {st.session_state.planta}")
    if st.sidebar.button("🔄 Cambiar Planta"):
        st.session_state.planta = None; st.rerun()

    tab_mapa, tab_stats = st.tabs(["🎮 Panel de Control", "📊 Estadísticas"])

    with tab_mapa:
        # Renderizamos cada zona en una caja (container)
        for nombre_zona, lista_banos in zonas_fisicas.items():
            st.markdown(f'<div class="zona-container"><div class="zona-titulo">{nombre_zona}</div>', unsafe_allow_html=True)
            
            col_izq, col_der = st.columns(2)
            for idx_b, bano in enumerate(lista_banos):
                with [col_izq, col_der][idx_b]:
                    st.subheader(f"🚻 {bano}")
                    ocupados = st.session_state.ocupacion[bano]
                    
                    for p_idx, p in enumerate(ocupados):
                        # --- LÓGICA DE ALARMA (> 10 MINUTOS) ---
                        hora_entrada = datetime.strptime(p['h_entrada'], "%H:%M")
                        hora_actual = datetime.strptime(datetime.now().strftime("%H:%M"), "%H:%M")
                        diferencia = (hora_actual - hora_entrada).seconds / 60
                        
                        estilo_alerta = 'class="alerta-bano"' if diferencia >= 10 else ""
                        
                        st.markdown(f'<div {estilo_alerta}>', unsafe_allow_html=True)
                        with st.expander(f"👤 {p['alumno']} ({int(diferencia)} min)", expanded=True):
                            ok = st.checkbox("Baño OK", value=True, key=f"ok_{bano}_{p_idx}")
                            obs = st.text_input("Notas", key=f"obs_{bano}_{p_idx}")
                            
                            if st.button("Finalizar", key=f"lib_{bano}_{p_idx}", use_container_width=True, type="primary"):
                                conn = init_db()
                                conn.execute("INSERT INTO visitas (planta, bano, alumno, curso, profesor, h_entrada, h_salida, estado_bano, observaciones) VALUES (?,?,?,?,?,?,?,?,?)",
                                            (st.session_state.planta, bano, p['alumno'], p['curso'], p['profesor'], p['h_entrada'], datetime.now().strftime("%H:%M"), "OK" if ok else "Problema", obs))
                                conn.commit(); conn.close()
                                st.session_state.ocupacion[bano].remove(p)
                                st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

                    if len(ocupados) < 2:
                        with st.popover(f"➕ Registrar en {bano}", use_container_width=True):
                            c = st.selectbox("Curso", sorted(df_alumnos['Curso'].unique()), key=f"c_{bano}")
                            a = st.selectbox("Alumno", sorted(df_alumnos[df_alumnos['Curso']==c]['Nombre']), key=f"a_{bano}")
                            pr = st.selectbox("Autoriza", sorted(lista_profesores), key=f"p_{bano}")
                            if st.button("Confirmar Entrada", key=f"conf_{bano}"):
                                st.session_state.ocupacion[bano].append({
                                    "alumno": a, "curso": c, "profesor": pr, "h_entrada": datetime.now().strftime("%H:%M")
                                })
                                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True) # Cierre de zona-container

    with tab_stats:
        conn = init_db()
        df = pd.read_sql_query("SELECT * FROM visitas", conn)
        conn.close()
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            st.bar_chart(df['alumno'].value_counts().head(10))
        else:
            st.info("No hay datos todavía.")