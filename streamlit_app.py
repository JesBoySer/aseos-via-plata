import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- CONFIGURACIÓN Y ESTILOS ---
st.set_page_config(page_title="SCA - IES Vía de la Plata", layout="wide")

# Conexión a Base de Datos SQLite para persistencia real
def init_db():
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
    # Simulamos carga de CSVs. En tu caso: pd.read_csv('data/alumnos.csv')
    df_alumnos = pd.DataFrame({
        'Nombre': ['Juan Pérez', 'María García', 'Luis Vaca', 'Ana Sanz'],
        'Curso': ['1º ESO A', '1º ESO A', '2º SMR', '2º SMR']
    })
    df_profesores = ['Prof. García', 'Prof. Vaca', 'Prof. Jiménez']
    return df_alumnos, df_profesores

df_alumnos, lista_profesores = cargar_maestros()

# --- LÓGICA DE ESTADO ---
if 'planta' not in st.session_state:
    st.session_state.planta = None

# --- INTERFAZ: SELECCIÓN DE PLANTA ---
if st.session_state.planta is None:
    st.title("🏛️ Control de Accesos - IES Vía de la Plata")
    st.subheader("Seleccione la planta de guardia:")
    col_p1, col_p2 = st.columns(2)
    if col_p1.button("🏢 PLANTA BAJA", use_container_width=True):
        st.session_state.planta = "Baja"
        st.rerun()
    if col_p2.button("🏢 PLANTA PRIMERA", use_container_width=True):
        st.session_state.planta = "Primera"
        st.rerun()
else:
    # --- INTERFAZ: GESTIÓN DE BAÑOS ---
    st.sidebar.title(f"📍 Planta {st.session_state.planta}")
    if st.sidebar.button("🔄 Cambiar de Planta"):
        st.session_state.planta = None
        st.rerun()

    # Definición de baños por planta (2 chicos, 2 chicas)
    tipos_bano = ["Chicos 1", "Chicos 2", "Chicas 1", "Chicas 2"]
    
    # Manejo de ocupación en memoria (hasta 2 personas por baño)
    if 'ocupacion' not in st.session_state:
        st.session_state.ocupacion = {t: [] for t in tipos_bano}

    st.title(f"🚾 Gestión de Baños - Planta {st.session_state.planta}")
    
    tabs = st.tabs(["🎮 Panel de Control", "📊 Estadísticas"])

    with tabs[0]:
        cols = st.columns(4)
        for idx, nombre_bano in enumerate(tipos_bano):
            with cols[idx]:
                ocupados = st.session_state.ocupacion[nombre_bano]
                n_ocupados = len(ocupados)
                
                st.subheader(f"{nombre_bano}")
                st.progress(n_ocupados / 2) # Visualización de aforo
                
                # Mostrar quién está dentro
                for persona in ocupados:
                    with st.expander(f"🔴 {persona['alumno']}"):
                        st.write(f"Desde: {persona['h_entrada']}")
                        ok = st.checkbox("Baño OK", value=True, key=f"ok_{persona['alumno']}")
                        obs = st.text_input("Obs.", key=f"obs_{persona['alumno']}")
                        if st.button("Finalizar", key=f"fin_{persona['alumno']}"):
                            # GUARDAR EN SQLITE
                            conn = init_db()
                            c = conn.cursor()
                            c.execute("INSERT INTO visitas (planta, bano, alumno, curso, profesor, h_entrada, h_salida, estado_bano, observaciones) VALUES (?,?,?,?,?,?,?,?,?)",
                                     (st.session_state.planta, nombre_bano, persona['alumno'], persona['curso'], persona['profesor'], persona['h_entrada'], datetime.now().strftime("%H:%M"), "Correcto" if ok else "Incorrecto", obs))
                            conn.commit()
                            # Eliminar de ocupación
                            st.session_state.ocupacion[nombre_bano].remove(persona)
                            st.rerun()

                # Botón para añadir si hay aforo
                if n_ocupados < 2:
                    with st.popover("➕ Nueva Entrada"):
                        curso = st.selectbox("Curso", df_alumnos['Curso'].unique(), key=f"c_{nombre_bano}")
                        alumnos_curso = df_alumnos[df_alumnos['Curso'] == curso]['Nombre']
                        alumno = st.selectbox("Alumno", alumnos_curso, key=f"a_{nombre_bano}")
                        profe = st.selectbox("Profesor", lista_profesores, key=f"p_{nombre_bano}")
                        if st.button("Registrar"):
                            st.session_state.ocupacion[nombre_bano].append({
                                "alumno": alumno, "curso": curso, "profesor": profe,
                                "h_entrada": datetime.now().strftime("%H:%M")
                            })
                            st.rerun()
                else:
                    st.warning("Aforo completo")

    with tabs[1]:
        st.header("Análisis de Datos")
        conn = init_db()
        df_hist = pd.read_sql_query("SELECT * FROM visitas", conn)
        
        if not df_hist.empty:
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Visitas", len(df_hist))
            c2.metric("Alumno más frecuente", df_hist['alumno'].mode()[0])
            c3.metric("Profesor autorizante top", df_hist['profesor'].mode()[0])
            
            st.write("### Visitas por Curso")
            st.bar_chart(df_hist['curso'].value_counts())
            
            st.dataframe(df_hist)
        else:
            st.info("Aún no hay datos históricos.")
