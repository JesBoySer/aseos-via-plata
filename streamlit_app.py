import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="SCA - IES Vía de la Plata",
    layout="wide",
    page_icon="🚾"
)

# --- 2. CSS MEJORADO (SIN CONTENEDORES EXTERNOS) ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

/* Fondo general */
.stApp {
    background-color: #0B1120;
    font-family: 'Inter', sans-serif;
    color: #E2E8F0;
}

/* Título de zona (NORTE / SUR) - ahora sin contenedor padre */
.zona-titulo {
    color: #38BDF8 !important;
    font-weight: 800;
    font-size: 1.8rem;
    letter-spacing: -0.02em;
    border-bottom: 2px solid #38BDF8;
    padding-bottom: 0.5rem;
    margin: 1rem 0 1.5rem 0;  /* separación superior e inferior */
    text-shadow: 0 2px 4px rgba(56,189,248,0.2);
}

/* Bloque individual de baño */
.bano-block {
    background: #0F172A;
    border-radius: 18px;
    padding: 1.2rem;
    border: 1px solid #334155;
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.6);
    margin-bottom: 1rem;
    transition: all 0.2s;
}
.bano-block:hover {
    border-color: #38BDF8;
    box-shadow: 0 0 0 2px rgba(56,189,248,0.3);
}

/* Título del baño (Chicos/Chicas) */
.bano-block h4 {
    color: #F1F5F9 !important;
    font-weight: 700;
    font-size: 1.4rem;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/* Alerta de tiempo >10 minutos (pulso suave) */
@keyframes gentle-pulse {
    0% { box-shadow: 0 0 0 0 rgba(239,68,68,0.5); background-color: rgba(239,68,68,0.15); }
    50% { box-shadow: 0 0 0 8px rgba(239,68,68,0); background-color: rgba(239,68,68,0.05); }
    100% { box-shadow: 0 0 0 0 rgba(239,68,68,0); background-color: rgba(239,68,68,0.15); }
}
.alerta-bano {
    animation: gentle-pulse 2s infinite;
    border-left: 4px solid #EF4444;
    border-radius: 12px;
    padding: 0.5rem;
}

/* Botones más atractivos */
.stButton > button {
    background: linear-gradient(to right, #1E293B, #0F172A);
    border: 1px solid #38BDF8;
    border-radius: 40px;
    color: #F8FAFC;
    font-weight: 600;
    padding: 0.5rem 1rem;
    transition: all 0.2s;
}
.stButton > button:hover {
    background: linear-gradient(to right, #2D3B4F, #1A2535);
    border-color: #7DD3FC;
    transform: scale(1.02);
    box-shadow: 0 10px 15px -3px rgba(56,189,248,0.3);
}

/* Selects y inputs */
.stSelectbox > div > div {
    background-color: #1E293B;
    border: 1px solid #334155;
    border-radius: 40px;
    color: white;
}

/* Sidebar */
.css-1d391kg, .css-1wrcr25 {
    background-color: #0F172A;
    border-right: 1px solid #334155;
}

/* Barra de progreso */
.stProgress > div > div > div {
    background-color: #38BDF8;
}

/* Divisor */
hr {
    border-color: #334155;
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
            df = pd.read_csv(ruta, sep=',', encoding='utf-8-sig', engine='python')
        except:
            df = pd.read_csv(ruta, sep=',', encoding='latin-1', engine='python')
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
with st.sidebar:
    st.markdown("## 🚾 SCA")
    st.markdown("---")
    if st.session_state.planta is None:
        st.info("👈 Selecciona una planta para comenzar")
    else:
        st.markdown(f"### 📍 Planta {st.session_state.planta}")
        if st.button("🔄 Cambiar planta", use_container_width=True):
            st.session_state.planta = None
            st.rerun()
    st.markdown("---")
    st.caption("IES Vía de la Plata · Control de aseos")

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
    tab_mapa, tab_stats = st.tabs(["🎮 Panel de Control", "📊 Histórico"])

    with tab_mapa:
        for nombre_zona, lista_banos in zonas_fisicas.items():
            # Título de la zona (sin contenedor adicional)
            st.markdown(f'<div class="zona-titulo">📍 {nombre_zona}</div>', unsafe_allow_html=True)
            
            # Dos columnas para los baños
            col_izq, col_der = st.columns(2)
            for idx_b, bano in enumerate(lista_banos):
                with col_izq if idx_b == 0 else col_der:
                    # Tarjeta del baño
                    st.markdown('<div class="bano-block">', unsafe_allow_html=True)
                    
                    icono = "🚹" if "Chicos" in bano else "🚺"
                    st.markdown(f"#### {icono} {bano}")
                    
                    ocupados = st.session_state.ocupacion[bano]
                    num_ocupados = len(ocupados)
                    st.progress(num_ocupados / 2, text=f"{num_ocupados}/2 ocupados")
                    
                    # Lista de alumnos dentro
                    for p_idx, p in enumerate(ocupados):
                        h_ent = datetime.strptime(p['h_entrada'], "%H:%M")
                        ahora = datetime.now()
                        h_ent_completa = ahora.replace(hour=h_ent.hour, minute=h_ent.minute, second=0, microsecond=0)
                        minutos = int((ahora - h_ent_completa).total_seconds() // 60)
                        
                        with st.container():
                            if minutos >= 10:
                                st.markdown('<div class="alerta-bano">', unsafe_allow_html=True)
                            
                            cols = st.columns([2, 1.5, 1, 0.8, 1.2])
                            cols[0].markdown(f"**{p['alumno']}**")
                            cols[1].markdown(f"*{p['curso']}*")
                            cols[2].markdown(f"⏱️ {minutos}'")
                            
                            ok_key = f"ok_{bano}_{p_idx}"
                            ok_val = cols[3].checkbox("✔️", value=True, key=ok_key, label_visibility="collapsed")
                            
                            if cols[4].button("🏁", key=f"fin_{bano}_{p_idx}"):
                                conn = init_db()
                                conn.execute("""INSERT INTO visitas 
                                    (planta, bano, alumno, curso, profesor, h_entrada, h_salida, estado_bano, observaciones) 
                                    VALUES (?,?,?,?,?,?,?,?,?)""",
                                    (st.session_state.planta, bano, p['alumno'], p['curso'], p['profesor'], 
                                     p['h_entrada'], datetime.now().strftime("%H:%M"), 
                                     "OK" if ok_val else "Problema", ""))
                                conn.commit()
                                conn.close()
                                st.session_state.ocupacion[bano].remove(p)
                                st.rerun()
                            
                            if minutos >= 10:
                                st.markdown('</div>', unsafe_allow_html=True)
                            else:
                                st.markdown("<hr style='margin:8px 0; opacity:0.3;'>", unsafe_allow_html=True)
                    
                    # Botón para añadir nueva entrada
                    if num_ocupados < 2:
                        with st.popover("➕ Registrar Entrada", use_container_width=True):
                            cursos_disponibles = sorted(df_alumnos['Curso'].unique())
                            curs_sel = st.selectbox("Curso", cursos_disponibles, key=f"sel_c_{bano}")
                            nombres_f = df_alumnos[df_alumnos['Curso'] == curs_sel]['Nombre']
                            alum_sel = st.selectbox("Alumno/a", sorted(nombres_f), key=f"sel_a_{bano}")
                            prof_sel = st.selectbox("Autoriza", sorted(lista_profesores), key=f"sel_p_{bano}")
                            if st.button("Confirmar entrada", key=f"conf_{bano}", use_container_width=True):
                                st.session_state.ocupacion[bano].append({
                                    "alumno": alum_sel, "curso": curs_sel, "profesor": prof_sel,
                                    "h_entrada": datetime.now().strftime("%H:%M")
                                })
                                st.rerun()
                    else:
                        st.warning("⚠️ Aforo completo (2/2)")
                    
                    st.markdown('</div>', unsafe_allow_html=True)  # cierre bano-block

    with tab_stats:
        st.markdown("### 📊 Registro de Visitas")
        conn = init_db()
        df_hist = pd.read_sql_query("SELECT * FROM visitas ORDER BY id DESC", conn)
        conn.close()
        
        if not df_hist.empty:
            df_hist['h_entrada_dt'] = pd.to_datetime(df_hist['h_entrada'], format='%H:%M')
            df_hist['hora'] = df_hist['h_entrada_dt'].dt.hour
            
            with st.expander("🔍 Filtros", expanded=True):
                col_f1, col_f2, col_f3 = st.columns(3)
                planta_filtro = col_f1.multiselect("Planta", options=df_hist['planta'].unique(), default=df_hist['planta'].unique())
                bano_filtro = col_f2.multiselect("Baño", options=df_hist['bano'].unique(), default=df_hist['bano'].unique())
                estado_filtro = col_f3.multiselect("Estado", options=df_hist['estado_bano'].unique(), default=df_hist['estado_bano'].unique())
            
            mask = (df_hist['planta'].isin(planta_filtro)) & (df_hist['bano'].isin(bano_filtro)) & (df_hist['estado_bano'].isin(estado_filtro))
            df_filtrado = df_hist[mask]
            
            st.subheader("Resumen")
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            col_m1.metric("Total visitas", len(df_filtrado))
            col_m2.metric("OK", (df_filtrado['estado_bano'] == 'OK').sum())
            col_m3.metric("Problema", (df_filtrado['estado_bano'] == 'Problema').sum())
            col_m4.metric("Alumnos distintos", df_filtrado['alumno'].nunique())
            
            st.subheader("Visitas por hora (últimos registros)")
            if not df_filtrado.empty:
                visitas_hora = df_filtrado.groupby('hora').size().reset_index(name='count')
                st.bar_chart(visitas_hora.set_index('hora'))
            else:
                st.info("No hay datos con los filtros actuales.")
            
            st.subheader("Detalle de visitas")
            st.dataframe(df_filtrado.drop(columns=['h_entrada_dt', 'hora']), use_container_width=True)
            
            csv_data = df_filtrado.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 Descargar histórico filtrado (CSV)",
                csv_data,
                "historico_aseos.csv",
                "text/csv",
                use_container_width=True
            )
        else:
            st.info("No hay registros en la base de datos local.")