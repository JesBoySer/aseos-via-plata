import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="SCA - IES Vía de la Plata", layout="wide", page_icon="🚾")

# --- 2. CSS DARK DE ALTO CONTRASTE (ESTILO TAILWIND DARK) ---
st.markdown("""
    <style>
    /* Fondo principal y texto base */
    .stApp {
        background-color: #0f172a;
        color: #f1f5f9 !important;
    }
    
    /* Contenedor de Zona (Norte/Sur) */
    .zona-container {
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 25px;
        background-color: #1e293b; /* Slate 800 */
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
        margin-bottom: 30px;
    }
    
    /* Títulos de Zona (NORTE / SUR) */
    .zona-titulo {
        color: #3b82f6 !important; /* Azul brillante para resaltar */
        font-weight: 800;
        font-size: 1.6rem !important;
        margin-bottom: 20px;
        text-align: center;
        border-bottom: 2px solid #334155;
        padding-bottom: 12px;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }

    /* Bloque interno de cada baño */
    .bano-block {
        background-color: #0f172a;
        padding: 18px;
        border-radius: 8px;
        border: 1px solid #334155;
        margin-bottom: 15px;
    }

    /* Forzar visibilidad de textos Chicos/Chicas (H4) */
    h4 {
        color: #f1f5f9 !important;
        font-weight: 700 !important;
        font-size: 1.25rem !important;
        margin-top: 5px !important;
    }

    /* Etiquetas de formularios y textos de expander */
    label, .stMarkdown p, .stCaption {
        color: #e2e8f0 !important;
    }

    /* ALARMA: Animación de parpadeo rojo para > 10 min */
    @keyframes pulse-red {
        0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); background-color: #450a0a; }
        70% { box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); background-color: #1e293b; }
        100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); background-color: #450a0a; }
    }
    .alerta-bano {
        animation: pulse-red 2s infinite;
        border: 2px solid #ef4444 !important;
        border-radius: 8px;
        padding: 5px;
        margin-bottom: 10px;
    }

    /* Estilo de los botones y selectores */
    .stButton>button {
        border-radius: 6px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. FUNCIONES DE BASE DE DATOS ---
def init_db():
    if not os.path.exists('data'):
        os.makedirs('data')
    conn = sqlite3.connect('data/historico.sqlite')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS visitas 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, planta TEXT, bano TEXT, 
                  alumno TEXT, curso TEXT, profesor TEXT, h_entrada TEXT, 
                  h_salida TEXT, estado_bano TEXT, observaciones TEXT)''')
    conn.commit()
    return conn

# --- 4. CARGA DE DATOS REALES (CSV) ---
@st.cache_data
def cargar_maestros():
    def leer_csv_robusto(ruta):
        if not os.path.exists(ruta): return None
        try:
            # Intento con UTF-8-SIG para Excel
            df = pd.read_csv(ruta, sep=',', encoding='utf-8-sig', engine='python')
        except:
            # Intento con Latin-1 si falla el anterior
            df = pd.read_csv(ruta, sep=',', encoding='latin-1', engine='python')
        
        # Limpieza de nombres de columnas
        df.columns = [str(c).strip().replace('\ufeff', '') for c in df.columns]
        return df

    df_alumnos = leer_csv_robusto('data/alumnos.csv')
    if df_alumnos is None or 'Curso' not in df_alumnos.columns:
        df_alumnos = pd.DataFrame({'Nombre': ['Error en archivo'], 'Curso': ['-']})
    
    df_p = leer_csv_robusto('data/profesores.csv')
    if df_p is not None and 'Nombre' in df_p.columns:
        lista_profesores = df_p['Nombre'].dropna().tolist()
    else:
        lista_profesores = ['Profesor de Guardia']
    
    return df_alumnos, lista_profesores

# Ejecutamos la carga
df_alumnos, lista_profesores = cargar_maestros()

# --- 5. LÓGICA DE ESTADO ---
if 'planta' not in st.session_state:
    st.session_state.planta = None

zonas_fisicas = {
    "NORTE": ["Chicos Norte", "Chicas Norte"],
    "SUR": ["Chicos Sur", "Chicas Sur"]
}

if 'ocupacion' not in st.session_state:
    st.session_state.ocupacion = {bano: [] for zona in zonas_fisicas.values() for bano in zona}

# --- 6. INTERFAZ DE USUARIO ---
if st.session_state.planta is None:
    st.title("🏛️ SCA - IES Vía de la Plata")
    st.subheader("Seleccione ubicación de guardia")
    c1, c2 = st.columns(2)
    if c1.button("🏢 PLANTA PRIMERA", use_container_width=True):
        st.session_state.planta = "Primera"
        st.rerun()
    if c2.button("🏢 PLANTA SEGUNDA", use_container_width=True):
        st.session_state.planta = "Segunda"
        st.rerun()
else:
    # Barra lateral
    st.sidebar.markdown(f"### 📍 Planta {st.session_state.planta}")
    if st.sidebar.button("🔄 Cambiar de Planta"):
        st.session_state.planta = None
        st.rerun()

    tab_mapa, tab_stats = st.tabs(["🎮 Panel de Control", "📊 Histórico"])

    # --- PESTAÑA: PANEL DE CONTROL ---
    with tab_mapa:
        for nombre_zona, lista_banos in zonas_fisicas.items():
            # Contenedor de Zona
            st.markdown(f'<div class="zona-container"><div class="zona-titulo">📍 {nombre_zona}</div>', unsafe_allow_html=True)
            
            col_izq, col_der = st.columns(2)
            for idx_b, bano in enumerate(lista_banos):
                with [col_izq, col_der][idx_b]:
                    st.markdown('<div class="bano-block">', unsafe_allow_html=True)
                    st.markdown(f"#### {bano}")
                    
                    ocupados = st.session_state.ocupacion[bano]
                    
                    # Mostrar alumnos dentro
                    for p_idx, p in enumerate(ocupados):
                        # Cálculo de tiempo para alarma
                        h_ent = datetime.strptime(p['h_entrada'], "%H:%M")
                        h_act = datetime.strptime(datetime.now().strftime("%H:%M"), "%H:%M")
                        minutos = (h_act - h_ent).seconds // 60
                        
                        estilo_clase = 'class="alerta-bano"' if minutos >= 10 else ''
                        
                        st.markdown(f'<div {estilo_clase}>', unsafe_allow_html=True)
                        with st.expander(f"👤 {p['alumno']} ({minutos} min)", expanded=True):
                            st.caption(f"Curso: {p['curso']} | Entró: {p['h_entrada']}")
                            ok_status = st.checkbox("OK", value=True, key=f"ok_{bano}_{p_idx}")
                            if st.button("Finalizar", key=f"btn_{bano}_{p_idx}", use_container_width=True, type="primary"):
                                # Guardar en DB
                                conn = init_db()
                                conn.execute("""INSERT INTO visitas 
                                    (planta, bano, alumno, curso, profesor, h_entrada, h_salida, estado_bano, observaciones) 
                                    VALUES (?,?,?,?,?,?,?,?,?)""",
                                    (st.session_state.planta, bano, p['alumno'], p['curso'], p['profesor'], 
                                     p['h_entrada'], datetime.now().strftime("%H:%M"), 
                                     "OK" if ok_status else "Problema", ""))
                                conn.commit()
                                conn.close()
                                # Liberar espacio
                                st.session_state.ocupacion[bano].remove(p)
                                st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

                    # Botón para añadir si hay sitio (máx 2)
                    if len(ocupados) < 2:
                        with st.popover("➕ Registrar Entrada", use_container_width=True):
                            curs_sel = st.selectbox("Curso", sorted(df_alumnos['Curso'].unique()), key=f"sel_c_{bano}")
                            nombres_f = df_alumnos[df_alumnos['Curso'] == curs_sel]['Nombre']
                            alum_sel = st.selectbox("Alumno/a", sorted(nombres_f), key=f"sel_a_{bano}")
                            prof_sel = st.selectbox("Autoriza", sorted(lista_profesores), key=f"sel_p_{bano}")
                            if st.button("Confirmar", key=f"conf_{bano}", use_container_width=True):
                                st.session_state.ocupacion[bano].append({
                                    "alumno": alum_sel, "curso": curs_sel, "profesor": prof_sel,
                                    "h_entrada": datetime.now().strftime("%H:%M")
                                })
                                st.rerun()
                    else:
                        st.warning("Aforo completo")
                    
                    st.markdown('</div>', unsafe_allow_html=True) # Cierre bano-block
            st.markdown('</div>', unsafe_allow_html=True) # Cierre zona-container

    # --- PESTAÑA: HISTÓRICO ---
    with tab_stats:
        st.markdown("### 📊 Registro de Visitas")
        conn = init_db()
        df_hist = pd.read_sql_query("SELECT * FROM visitas ORDER BY id DESC", conn)
        conn.close()
        
        if not df_hist.empty:
            st.dataframe(df_hist, use_container_width=True)
            csv_data = df_hist.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Descargar histórico (CSV)", csv_data, "historico_aseos.csv", "text/csv")
        else:
            st.info("No hay registros en la base de datos local.")