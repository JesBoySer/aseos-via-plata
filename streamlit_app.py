import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- Auto-refresh cada 30s ---
st_autorefresh(interval=30000, key="refresh")

# --- Configuración página ---
st.set_page_config(
    page_title="SCA - IES Vía de la Plata",
    layout="wide",
    page_icon="🚾"
)

# --- CSS ---
st.markdown("""
<style>
.stApp {background:#0B1120;color:#E2E8F0;font-family:'Inter',sans-serif;}
.zona-titulo{font-size:1.6rem;font-weight:800;color:#38BDF8;border-bottom:2px solid #38BDF8;margin-top:10px;margin-bottom:20px;}
.stButton>button {color:#F8FAFC;font-weight:700; background: #1E293B; border: 2px solid #38BDF8; border-radius:12px; padding:0.5rem 1rem; transition:0.2s;}
.stButton>button:hover {background:#2563EB; color:white; border-color:#7DD3FC; transform:scale(1.02);}
input[type="checkbox"]:checked{accent-color:#22C55E;}
textarea{border-radius:8px;background:#1E293B;color:white;width:100%;height:80px;padding:5px;}
</style>
""", unsafe_allow_html=True)

# --- Base de datos ---
def init_db():
    if not os.path.exists('data'):
        os.makedirs('data')
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

# --- Carga CSV ---
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
for b in [b for z in zonas_fisicas.values() for b in z]:
    if b not in st.session_state.ocupacion: st.session_state.ocupacion[b]=[]

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
    
    # --- Panel de control ---
    with tab_mapa:
        for zona,banos in zonas_fisicas.items():
            st.markdown(f'<div class="zona-titulo">{zona}</div>',unsafe_allow_html=True)
            col1,col2 = st.columns(2)
            for idx,bano in enumerate(banos):
                cont = col1 if idx==0 else col2
                with cont:
                    icono = "🚹" if "Chicos" in bano else "🚺"
                    st.markdown(f"### {icono} {bano}")
                    ocupados = st.session_state.ocupacion[bano]
                    num = len(ocupados)

                    # Tabla encabezado
                    cols_tab = st.columns([1.2,3,2,2,1,1])
                    for c,h in zip(cols_tab,["Estado","Alumno","Curso","Tiempo","OK","Salida"]):
                        c.markdown(f"**{h}**")
                    
                    # Dos filas por baño
                    for i in range(2):
                        fila = st.columns([1.2,3,2,2,1,1])
                        key_fila=f"{bano}_{i}"
                        if i<num:
                            p=ocupados[i]
                            h_ent=datetime.strptime(p['h_entrada'],"%H:%M")
                            ahora=datetime.now()
                            h_real=ahora.replace(hour=h_ent.hour,minute=h_ent.minute)
                            minutos=int((ahora-h_real).total_seconds()/60)
                            # botón rojo si alumno está dentro
                            estado_emoji = "🔴"
                            if fila[0].button(estado_emoji,key=f"info_{key_fila}"):
                                st.info(f"Alumno: {p['alumno']}\nCurso: {p['curso']}\nProfesor: {p['profesor']}\nEntrada: {p['h_entrada']}")
                            fila[1].markdown(f"**{p['alumno']}**")
                            fila[2].markdown(p['curso'])
                            fila[3].markdown(f"{minutos} min")
                            ok_val=fila[4].checkbox("",True,key=f"ok_{key_fila}")
                            obs=""
                            if not ok_val:
                                obs=fila[4].text_area("Observaciones",key=f"obs_{key_fila}",height=80)
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
                                st.session_state.ocupacion[bano].remove(p)
                                st.rerun()
                        else:
                            if key_fila not in st.session_state.editar: st.session_state.editar[key_fila]=False
                            if fila[0].button("🟢",key=f"libre_{key_fila}"): st.session_state.editar[key_fila]=True
                            fila[1].markdown("-"); fila[2].markdown("-"); fila[3].markdown("-")
                            fila[4].checkbox("",True,key=f"ok_{key_fila}_vacio",disabled=True); fila[5].markdown("-")
                            if st.session_state.editar[key_fila]:
                                curso_sel = st.selectbox("Curso",[""]+sorted(df_alumnos['Curso'].unique()),key=f"curso_{key_fila}",format_func=lambda x:"Curso" if x=="" else x)
                                alumno_sel=st.selectbox("Alumno",[""]+sorted(df_alumnos[df_alumnos['Curso']==curso_sel]['Nombre']) if curso_sel else [""],key=f"alumno_{key_fila}",format_func=lambda x:"Alumno" if x=="" else x)
                                prof_sel=st.selectbox("Profesor",[""]+lista_profesores,key=f"prof_{key_fila}",format_func=lambda x:"Profesor" if x=="" else x)
                                ok_val_new=st.checkbox("OK",value=True,key=f"ok_new_{key_fila}")
                                obs_new = st.text_area("Observaciones", key=f"obs_new_{key_fila}", height=80)
                                if st.button("Registrar Entrada",key=f"entrada_new_{key_fila}"):
                                    if alumno_sel and curso_sel and prof_sel:
                                        st.session_state.ocupacion[bano].append({
                                            "alumno":alumno_sel,
                                            "curso":curso_sel,
                                            "profesor":prof_sel,
                                            "h_entrada":datetime.now().strftime("%H:%M")
                                        })
                                        st.session_state.editar[key_fila]=False
                                        st.rerun()

    # --- Estadísticas e histórico ---
    with tab_stats:
        conn=init_db()
        df=pd.read_sql_query("SELECT * FROM visitas ORDER BY id DESC",conn)
        conn.close()
        if not df.empty:
            # Calcular tiempo de estancia
            def calc_tiempo(row):
                try:
                    h_ent=datetime.strptime(row['h_entrada'],'%H:%M')
                    h_sal=datetime.strptime(row['h_salida'],'%H:%M')
                    minutos=int((h_sal-h_ent).total_seconds()/60)
                    return max(minutos,0)
                except:
                    return None
            df['Tiempo min'] = df.apply(calc_tiempo,axis=1)

            st.subheader("📊 Resumen General")
            col1,col2,col3,col4,col5=st.columns(5)
            col1.metric("Total visitas",len(df))
            col2.metric("OK",(df['estado_bano']=='OK').sum())
            col3.metric("Problema",(df['estado_bano']=='Problema').sum())
            col4.metric("Alumnos distintos",df['alumno'].nunique())
            col5.metric("Tiempo medio (min)",round(df['Tiempo min'].mean(),1))
            
            st.subheader("Distribución de visitas por hora")
            df['h_entrada_dt']=pd.to_datetime(df['h_entrada'],format='%H:%M',errors='coerce')
            df['hora']=df['h_entrada_dt'].dt.hour
            visitas_hora=df.groupby('hora').size().reset_index(name='count')
            st.bar_chart(visitas_hora.set_index('hora'))

            st.subheader("Histórico detallado")
            st.dataframe(df,use_container_width=True)
            csv=df.to_csv(index=False).encode('utf-8')
            st.download_button("Descargar CSV",csv,"historico.csv","text/csv")
        else:
            st.info("No hay registros aún")
