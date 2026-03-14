import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime

# --- CONFIGURACIÓN Y ESTILOS ---
st.set_page_config(page_title="SCA - IES Vía de la Plata", layout="wide", page_icon="🚾")

# Asegurar que existe la carpeta data
if not os.path.exists('data'):
    os.makedirs('data')

# --- INICIALIZACIÓN DE BASE DE DATOS ---
def init_db():
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

# --- CARGA DE DATOS (MAESTROS) ---
@st.cache_data
def cargar_maestros():
    # Intentar cargar desde CSV, si no existen, crear datos de ejemplo
    try:
        df_alumnos = pd.read_csv('data/alumnos.csv')
    except:
        df_alumnos = pd.DataFrame({
            'Nombre': ['Juan Pérez', 'María García', 'Luis Vaca', 'Ana Sanz', 'Pedro Soto', 'Lucía Fe'],
            'Curso': ['1º ESO A', '1º ESO A', '2º SMR', '2º SMR', '1º ESO B', '1º ESO B']
        })
    
    try:
        df_profesores = pd.read_csv('data/profesores.csv')['Nombre'].tolist()
    except:
        df_profesores = ['Prof. García (Informática)', 'Prof. Vaca (Sistemas)', 'Prof. Jiménez (FOL)']
    
    return df_alumnos, df_profesores

df_alumnos, lista_profesores = cargar_maestros()

# --- LÓGICA DE ESTADO ---
if 'planta' not in st.session_state:
    st.session_state.planta = None

# Inicialización de ocupación en memoria (2 personas por baño)
# Usamos nombres únicos para los 4 baños
tipos_bano = ["Chicos 1", "Chicos 2", "Chicas 1", "Chicas 2"]
if 'ocupacion' not in st.session_state:
    st.session_state.ocupacion = {t: [] for t in tipos_bano}

# --- INTERFAZ: SELECCIÓN DE PLANTA ---
if st.session_state.planta is None:
    st.title("🏛️ Control de Accesos - IES Vía de la Plata")
    st.subheader("Seleccione la planta donde se encuentra la guardia:")
    
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        if st.button("🏢 PLANTA BAJA", use_container_width=True, key="btn_planta_baja"):
            st.session_state.planta = "Baja"
            st.rerun()
    with col_p2:
        if st.button("🏢 PLANTA PRIMERA", use_container_width=True, key="btn_planta_primera"):
            st.session_state.planta = "Primera"
            st.rerun()
else:
    # --- INTERFAZ PRINCIPAL ---
    st.sidebar.title(f"📍 Planta {st.session_state.planta}")
    if st.sidebar.button("🔄 Cambiar de Planta", key="btn_change_floor"):
        st.session_state.planta = None
        st.rerun()

    st.title(f"🚾 Gestión de Baños - Planta {st.session_state.planta}")
    
    tab_control, tab_stats = st.tabs(["🎮 Panel de Control", "📊 Estadísticas y Registro"])

    # --- TAB 1: PANEL DE CONTROL ---
    with tab_control:
        st.write("### Estado de los Baños (Aforo máx. 2 personas)")
        cols = st.columns(4)
        
        for idx, nombre_bano in enumerate(tipos_bano):
            with cols[idx]:
                ocupados = st.session_state.ocupacion[nombre_bano]
                n_ocupados = len(ocupados)
                
                # Encabezado del baño
                st.markdown(f"#### {nombre_bano}")
                color_aforo = "green" if n_ocupados < 2 else "red"
                st.markdown(f"Aforo: :{color_aforo}[{n_ocupados} / 2]")
                
                # Lista de personas actualmente en el baño
                for p_idx, persona in enumerate(ocupados):
                    with st.expander(f"👤 {persona['alumno']}", expanded=True):
                        st.caption(f"Entrada: {persona['h_entrada']}")
                        st.caption(f"Prof: {persona['profesor']}")
                        
                        # Formulario de salida
                        ok = st.checkbox("Baño OK", value=True, key=f"chk_ok_{nombre_bano}_{p_idx}")
                        obs = st.text_input("Observaciones", key=f"obs_{nombre_bano}_{p_idx}")
                        
                        if st.button("Finalizar Visita", key=f"btn_fin_{nombre_bano}_{p_idx}", use_container_width=True):
                            # Guardar en base de datos
                            conn = init_db()
                            c = conn.cursor()
                            c.execute("""INSERT INTO visitas 
                                        (planta, bano, alumno, curso, profesor, h_entrada, h_salida, estado_bano, observaciones) 
                                        VALUES (?,?,?,?,?,?,?,?,?)""",
                                     (st.session_state.planta, nombre_bano, persona['alumno'], persona['curso'], 
                                      persona['profesor'], persona['h_entrada'], datetime.now().strftime("%H:%M"), 
                                      "Correcto" if ok else "Incorrecto", obs))
                            conn.commit()
                            conn.close()
                            
                            # Eliminar de la lista de ocupación
                            st.session_state.ocupacion[nombre_bano].remove(persona)
                            st.success("Registro guardado")
                            st.rerun()

                # Botón para añadir nueva persona si hay hueco
                if n_ocupados < 2:
                    st.write("---")
                    with st.popover(f"➕ Registrar en {nombre_bano}", use_container_width=True):
                        curso_sel = st.selectbox("Curso", sorted(df_alumnos['Curso'].unique()), key=f"sel_curso_{nombre_bano}")
                        
                        alumnos_filtrados = df_alumnos[df_alumnos['Curso'] == curso_sel]['Nombre']
                        alumno_sel = st.selectbox("Alumno/a", sorted(alumnos_filtrados), key=f"sel_alumno_{nombre_bano}")
                        
                        profe_sel = st.selectbox("Autoriza Profesor/a", sorted(lista_profesores), key=f"sel_profe_{nombre_bano}")
                        
                        if st.button("Confirmar Entrada", key=f"btn_reg_{nombre_bano}", type="primary"):
                            nueva_persona = {
                                "alumno": alumno_sel,
                                "curso": curso_sel,
                                "profesor": profe_sel,
                                "h_entrada": datetime.now().strftime("%H:%M")
                            }
                            st.session_state.ocupacion[nombre_bano].append(nueva_persona)
                            st.rerun()
                else:
                    st.error("⚠️ BAÑO COMPLETO")

    # --- TAB 2: ESTADÍSTICAS ---
    with tab_stats:
        st.header("📊 Historial y Estadísticas")
        conn = init_db()
        df_hist = pd.read_sql_query("SELECT * FROM visitas ORDER BY id DESC", conn)
        conn.close()
        
        if not df_hist.empty:
            # Métricas rápidas
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Visitas", len(df_hist))
            m2.metric("Alumno/a más frecuente", df_hist['alumno'].mode()[0])
            m3.metric("Profesor autorizante top", df_hist['profesor'].mode()[0])
            
            # Gráficos
            c1, c2 = st.columns(2)
            with c1:
                st.write("### Visitas por Curso")
                st.bar_chart(df_hist['curso'].value_counts())
            with c2:
                st.write("### Estado de Limpieza")
                st.bar_chart(df_hist['estado_bano'].value_counts())
            
            # Tabla completa
            st.write("### Registro Detallado")
            st.dataframe(df_hist, use_container_width=True)
            
            # Botón de descarga
            csv = df_hist.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Descargar histórico completo (CSV)", csv, "historico_banos.csv", "text/csv", key='download-csv')
        else:
            st.info("Todavía no hay registros en la base de datos.")

# Pie de página
st.sidebar.markdown("---")
st.sidebar.caption("SCA - IES Vía de la Plata (Guijuelo)")
st.sidebar.caption("Desarrollado para control de guardias.")
