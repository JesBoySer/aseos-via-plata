import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="SCA - IES Vía de la Plata", layout="wide", page_icon="🚾")

# --- FUNCIONES DE PERSISTENCIA ---
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

# --- CARGA DE DATOS REALES ---
@st.cache_data
def cargar_maestros():
    # Carga de Alumnos
    if os.path.exists('data/alumnos.csv'):
        df_alumnos = pd.read_csv('data/alumnos.csv', encoding='utf-8')
    else:
        st.error("⚠️ No se encuentra 'data/alumnos.csv'. Usando datos de prueba.")
        df_alumnos = pd.DataFrame({'Nombre': ['Ejemplo Alumno'], 'Curso': ['PRUEBA']})
    
    # Carga de Profesores
    if os.path.exists('data/profesores.csv'):
        df_profesores = pd.read_csv('data/profesores.csv', encoding='utf-8')['Nombre'].tolist()
    else:
        st.error("⚠️ No se encuentra 'data/profesores.csv'. Usando datos de prueba.")
        df_profesores = ['Profesor de Prueba']
    
    return df_alumnos, df_profesores

df_alumnos, lista_profesores = cargar_maestros()

# --- LÓGICA DE ESTADO ---
if 'planta' not in st.session_state:
    st.session_state.planta = None

tipos_bano = ["Chicos 1", "Chicos 2", "Chicas 1", "Chicas 2"]
if 'ocupacion' not in st.session_state:
    st.session_state.ocupacion = {t: [] for t in tipos_bano}

# --- INTERFAZ: SELECCIÓN DE PLANTA ---
if st.session_state.planta is None:
    st.title("🏛️ Control de Accesos - IES Vía de la Plata")
    st.info("Bienvenido. Por favor, seleccione su ubicación de guardia.")
    col_p1, col_p2 = st.columns(2)
    if col_p1.button("🏢 PLANTA BAJA", use_container_width=True, key="p_baja"):
        st.session_state.planta = "Baja"
        st.rerun()
    if col_p2.button("🏢 PLANTA PRIMERA", use_container_width=True, key="p_alta"):
        st.session_state.planta = "Primera"
        st.rerun()
else:
    # Barra lateral de navegación
    st.sidebar.title(f"📍 Planta {st.session_state.planta}")
    if st.sidebar.button("🔄 Cambiar Planta"):
        st.session_state.planta = None
        st.rerun()

    tab_ctrl, tab_hist = st.tabs(["🎮 Panel de Control", "📊 Estadísticas"])

    # --- PANEL DE CONTROL ---
    with tab_ctrl:
        cols = st.columns(4)
        for idx, nombre_bano in enumerate(tipos_bano):
            with cols[idx]:
                ocupados = st.session_state.ocupacion[nombre_bano]
                n = len(ocupados)
                
                st.subheader(nombre_bano)
                color = "green" if n < 2 else "red"
                st.markdown(f"Ocupación: :{color}[{n} / 2]")

                # Mostrar ocupantes
                for p_idx, p in enumerate(ocupados):
                    with st.expander(f"👤 {p['alumno']}", expanded=True):
                        st.write(f"Curso: {p['curso']}")
                        st.caption(f"Entrada: {p['h_entrada']}")
                        ok = st.checkbox("OK", value=True, key=f"ok_{nombre_bano}_{p_idx}")
                        obs = st.text_input("Notas", key=f"obs_{nombre_bano}_{p_idx}")
                        if st.button("Liberar", key=f"lib_{nombre_bano}_{p_idx}", use_container_width=True):
                            conn = init_db()
                            conn.execute("INSERT INTO visitas (planta, bano, alumno, curso, profesor, h_entrada, h_salida, estado_bano, observaciones) VALUES (?,?,?,?,?,?,?,?,?)",
                                        (st.session_state.planta, nombre_bano, p['alumno'], p['curso'], p['profesor'], p['h_entrada'], datetime.now().strftime("%H:%M"), "OK" if ok else "Problema", obs))
                            conn.commit()
                            conn.close()
                            st.session_state.ocupacion[nombre_bano].remove(p)
                            st.rerun()

                # Añadir nuevo si hay aforo
                if n < 2:
                    st.write("---")
                    with st.popover(f"➕ Registrar", use_container_width=True):
                        curso = st.selectbox("Curso", sorted(df_alumnos['Curso'].unique()), key=f"c_{nombre_bano}")
                        alumnos = df_alumnos[df_alumnos['Curso'] == curso]['Nombre']
                        alumno = st.selectbox("Alumno/a", sorted(alumnos), key=f"a_{nombre_bano}")
                        profe = st.selectbox("Autoriza", sorted(lista_profesores), key=f"p_{nombre_bano}")
                        if st.button("Confirmar", key=f"conf_{nombre_bano}", type="primary"):
                            st.session_state.ocupacion[nombre_bano].append({
                                "alumno": alumno, "curso": curso, "profesor": profe,
                                "h_entrada": datetime.now().strftime("%H:%M")
                            })
                            st.rerun()

    # --- ESTADÍSTICAS ---
    with tab_hist:
        conn = init_db()
        df = pd.read_sql_query("SELECT * FROM visitas", conn)
        conn.close()
        if not df.empty:
            st.metric("Total Visitas Hoy", len(df))
            st.write("### Histórico Reciente")
            st.dataframe(df.tail(10), use_container_width=True)
            st.write("### Alumnos más frecuentes")
            st.bar_chart(df['alumno'].value_counts().head(10))
        else:
            st.info("Sin registros históricos.")