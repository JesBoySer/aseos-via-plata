import streamlit as st
import pandas as pd
import sqlite3
import os
import re
from datetime import datetime
import requests
import base64
from io import StringIO
# from streamlit_autorefresh import st_autorefresh  # desactivado para evitar rerun

# ----------------------------
# CONFIGURACIÓN BÁSICA
# ----------------------------
st.set_page_config(
    page_title="SCA - IES Vía de la Plata",
    layout="wide",
    page_icon="🚾"
)

# st_autorefresh(interval=120000, key="refresh")  # si quieres refresco suave (120 s)

MAX_MINUTOS = 10

# Secrets de GitHub (si usas cierre diario / histórico)
GITHUB_TOKEN = st.secrets.get("GITHUB_TOKEN", "")
REPO = st.secrets.get("GITHUB_REPO", "")
FILE_PATH = st.secrets.get("GITHUB_FILE", "")

# ----------------------------
# ESTILOS (MODO OSCURO + SELECT + PILLS + BOTÓN 🟢)
# ----------------------------
st.markdown("""
<style>

/* --- Base oscura --- */
.stApp{ background:#0B1120; color:#E2E8F0; }

/* Botón genérico */
.stButton>button{
  border:none; border-radius:8px;
  background:#1E293B; color:#F8FAFC; font-weight:600;
}
.stButton>button:hover{ background:#2563EB; color:#fff; }

/* Cabeceras */
.cabecera-bano{ border-bottom:1px solid #38BDF8; padding:4px; font-weight:bold; }
.minutos-alerta{ color:#ef4444; font-weight:bold; }
.ok-verde{ color:#22c55e; font-weight:bold; }

/* Checkbox */
.stCheckbox>label>div{ transform:scale(0.85); }
.stCheckbox{ display:flex; justify-content:center; }

/* Centrado columnas */
[data-testid="column"]{ text-align:center; }

/* --- SELECTBOX / MULTISELECT en oscuro --- */
.stSelectbox div[data-baseweb="select"] > div,
.stMultiSelect div[data-baseweb="select"] > div {
  background:#000 !important; color:#fff !important;
  border-color:#334155 !important; border-radius:8px !important;
}
.stSelectbox div[data-baseweb="select"] input,
.stMultiSelect div[data-baseweb="select"] input,
.stSelectbox div[data-baseweb="select"] div[aria-hidden="true"],
.stMultiSelect div[data-baseweb="select"] div[aria-hidden="true"] {
  color:#fff !important;
}
.stSelectbox div[data-baseweb="select"] div[aria-hidden="true"],
.stMultiSelect div[data-baseweb="select"] div[aria-hidden="true"] {
  opacity:0.7 !important;
}
.stSelectbox svg, .stMultiSelect svg { fill:#fff !important; color:#fff !important; }
.stSelectbox div[data-baseweb="select"] div[role="listbox"],
.stMultiSelect div[data-baseweb="select"] div[role="listbox"] {
  background:#0a0a0a !important; color:#fff !important;
  border:1px solid #334155 !important;
}
.stSelectbox div[role="option"], .stMultiSelect div[role="option"] {
  background:#0a0a0a !important; color:#fff !important;
}
.stSelectbox div[role="option"]:hover, .stMultiSelect div[role="option"]:hover {
  background:#1f2937 !important;
}
.stSelectbox div[aria-selected="true"], .stMultiSelect div[aria-selected="true"] {
  background:#111827 !important; color:#fff !important;
}
.stSelectbox div[data-baseweb="select"], .stMultiSelect div[data-baseweb="select"] { text-align:center; }
.stSelectbox div[data-baseweb="select"] > div:focus-within,
.stMultiSelect div[data-baseweb="select"] > div:focus-within {
  outline:2px solid #2563EB !important; outline-offset:1px !important;
}

/* --- Pastillas NORTE/SUR --- */
.zona-pill {
  display:inline-flex; align-items:center; gap:8px;
  padding:6px 14px; border-radius:9999px; font-weight:700; letter-spacing:0.5px;
  margin:10px 0 6px 0; user-select:none;
  color:#E5E7EB; background:rgba(30,41,59,0.45);
  border:1px solid rgba(148,163,184,0.35); backdrop-filter: blur(2px);
}
.zona-norte { border-color:rgba(56,189,248,0.6); box-shadow:inset 0 0 0 1px rgba(56,189,248,0.25); }
.zona-norte .punto { width:8px;height:8px;border-radius:9999px;background:#22D3EE; }
.zona-sur   { border-color:rgba(167,139,250,0.6); box-shadow:inset 0 0 0 1px rgba(167,139,250,0.25); }
.zona-sur .punto { width:8px;height:8px;border-radius:9999px;background:#A78BFA; }
.zona-wrap { display:flex; justify-content:center; margin-top:6px; margin-bottom:4px; }

/* --- Botón 🟢: alineado, sin borde --- */
.btn-alta-wrap { margin-top:28px; display:flex; justify-content:center; }
.btn-alta-wrap > button{
  border:none !important; background:none !important; padding:0 !important;
  font-size:26px !important; cursor:pointer !important; color:#22c55e !important;
}
.btn-alta-wrap > button:hover{ transform:scale(1.12); }

/* Alinear botones con selects sin label (seguridad extra) */
div[data-testid="column"] > div > div > div > div > .stButton { margin-top:28px; }

</style>
""", unsafe_allow_html=True)

# ----------------------------
# UTILIDADES
# ----------------------------
def make_key(*parts):
    """
    Clave segura para widgets:
    - Une con '_', sustituye no alfanumérico por '_', comprime '_' y recorta bordes.
    """
    raw = "_".join(str(p) for p in parts)
    safe = re.sub(r'[^a-zA-Z0-9_-]+', '_', raw)
    safe = re.sub(r'_+', '_', safe).strip('_')
    return safe

def db_path_for(planta: str) -> str:
    """Ruta de BD por planta (dos archivos locales)."""
    if not os.path.exists("data"):
        os.makedirs("data")
    return "data/primera.sqlite" if planta == "Primera" else "data/segunda.sqlite"

def init_db(planta: str):
    """Abre la BD y asegura esquema."""
    db_file = db_path_for(planta)
    conn = sqlite3.connect(db_file, check_same_thread=False)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS visitas(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT,
        planta TEXT,
        bano TEXT,
        alumno TEXT,
        curso TEXT,
        profesor TEXT,
        h_entrada TEXT,
        h_salida TEXT,
        estado TEXT,
        observaciones TEXT,
        exportado INTEGER DEFAULT 0
    )
    """)
    conn.commit()
    # Migraciones por si faltan columnas
    cols = [r[1] for r in conn.execute("PRAGMA table_info(visitas)").fetchall()]
    if "fecha" not in cols:
        conn.execute("ALTER TABLE visitas ADD COLUMN fecha TEXT")
    if "exportado" not in cols:
        conn.execute("ALTER TABLE visitas ADD COLUMN exportado INTEGER DEFAULT 0")
    conn.commit()
    return conn

def subir_a_github(df_nuevo: pd.DataFrame):
    """Sube y fusiona con CSV remoto en GitHub (histórico)."""
    if not (GITHUB_TOKEN and REPO and FILE_PATH):
        st.warning("No hay credenciales de GitHub configuradas en secrets.")
        return 400

    url = f"https://api.github.com/repos/{REPO}/contents/{FILE_PATH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}

    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        contenido = r.json()
        sha = contenido["sha"]
        csv_actual = base64.b64decode(contenido["content"]).decode()
        df_actual = pd.read_csv(StringIO(csv_actual)) if csv_actual.strip() else pd.DataFrame()
    else:
        sha = None
        df_actual = pd.DataFrame()

    df_total = pd.concat([df_actual, df_nuevo], ignore_index=True) if not df_actual.empty else df_nuevo.copy()

    dedup_cols = ["fecha","planta","bano","curso","alumno","profesor","h_entrada","h_salida","estado","observaciones"]
    df_total = df_total.drop_duplicates(subset=dedup_cols)

    data = {
        "message": f"Actualizar histórico aseos - {datetime.now().isoformat(timespec='seconds')}",
        "content": base64.b64encode(df_total.to_csv(index=False).encode()).decode(),
        "sha": sha
    }
    put_r = requests.put(url, headers=headers, json=data)
    if put_r.status_code not in (200, 201):
        st.error(f"Error al subir histórico a GitHub: {put_r.status_code} - {put_r.text}")
    return put_r.status_code

def cierre_diario(fecha_str: str):
    """Exporta a GitHub visitas de HOY (de ambas plantas) con exportado=0 y marca como exportadas."""
    df_export = []
    for planta in ["Primera", "Segunda"]:
        conn = init_db(planta)
        df = pd.read_sql_query(
            """
            SELECT id, fecha, planta, bano, curso, alumno, profesor, h_entrada, h_salida, estado, observaciones
            FROM visitas
            WHERE fecha = ? AND IFNULL(exportado,0) = 0
            ORDER BY id ASC
            """,
            conn,
            params=(fecha_str,)
        )
        if not df.empty:
            df_export.append(df.copy())
            ids = df["id"].tolist()
            conn.executemany("UPDATE visitas SET exportado=1 WHERE id=?", [(i,) for i in ids])
            conn.commit()
        conn.close()

    if df_export:
        df_concat = pd.concat(df_export, ignore_index=True)
        status = subir_a_github(df_concat)
        if status in (200, 201):
            st.success(f"Exportadas {len(df_concat)} visitas de {fecha_str} al histórico de GitHub.")
        else:
            st.warning("Se marcaron como exportadas en BD, pero falló la subida a GitHub. Puedes reintentar.")
    else:
        st.info("No hay visitas pendientes de exportar para hoy.")

@st.cache_data
def cargar_datos():
    alumnos = pd.read_csv("data/alumnos.csv")
    profesores = pd.read_csv("data/profesores.csv")
    return alumnos, profesores

# ----------------------------
# DATOS INICIALES
# ----------------------------
df_alumnos, df_profesores = cargar_datos()
lista_profesores = df_profesores["Nombre"].tolist()

if "planta" not in st.session_state:
    st.session_state.planta = None

if "ocupacion" not in st.session_state:
    st.session_state.ocupacion = {
        "Primera": {
            "Chicos Norte":[],
            "Chicas Norte":[],
            "Chicos Sur":[],
            "Chicas Sur":[]
        },
        "Segunda": {
            "Chicos Norte":[],
            "Chicas Norte":[],
            "Chicos Sur":[],
            "Chicas Sur":[]
        }
    }

if "editar" not in st.session_state:
    st.session_state.editar = {}

# ----------------------------
# SIDEBAR
# ----------------------------
with st.sidebar:
    st.title("🚾 SCA")
    if st.button("📤 Cierre diario (exportar a histórico)", use_container_width=True):
        hoy = datetime.now().strftime("%Y-%m-%d")
        cierre_diario(hoy)

    if st.session_state.planta:
        st.success(f"Planta {st.session_state.planta}")
        if st.button("Cambiar planta", use_container_width=True):
            st.session_state.planta = None
            st.rerun()

# ----------------------------
# SELECCIÓN DE PLANTA
# ----------------------------
if st.session_state.planta is None:
    st.title("Sistema Control de Aseos")
    c1, c2 = st.columns(2)
    if c1.button("Planta Primera", use_container_width=True):
        st.session_state.planta = "Primera"
        st.rerun()
    if c2.button("Planta Segunda", use_container_width=True):
        st.session_state.planta = "Segunda"
        st.rerun()
    st.stop()

# ----------------------------
# AUXILIAR
# ----------------------------
def alumno_en_bano(nombre):
    for planta in st.session_state.ocupacion.values():
        for bano in planta.values():
            for p in bano:
                if p["alumno"] == nombre:
                    return True
    return False

# ----------------------------
# TABS
# ----------------------------
tab_panel, tab_hist = st.tabs(["Panel", "Histórico"])

zonas = {
    "NORTE": ["Chicos Norte", "Chicas Norte"],
    "SUR": ["Chicos Sur", "Chicas Sur"]
}

# ----------------------------
# PANEL
# ----------------------------
with tab_panel:

    for zona, banos in zonas.items():

        # Pastilla NORTE/SUR (con estilo)
        css_variante = "norte" if zona.upper() == "NORTE" else "sur"
        st.markdown(
            f'''
            <div class="zona-wrap">
                <div class="zona-pill zona-{css_variante}">
                    <span class="punto"></span>
                    <span>{zona}</span>
                </div>
            </div>
            ''',
            unsafe_allow_html=True
        )

        col1, col2 = st.columns(2)

        for i, bano in enumerate(banos):
            cont = col1 if i == 0 else col2
            with cont:
                icono = "🚹" if "Chicos" in bano else "🚺"
                st.markdown(f"### {icono} {bano}")

                cab = st.columns([2,3,3,1,1,1])
                cab[0].markdown('<div class="cabecera-bano">Curso</div>', unsafe_allow_html=True)
                cab[1].markdown('<div class="cabecera-bano">Alumno</div>', unsafe_allow_html=True)
                cab[2].markdown('<div class="cabecera-bano">Profesor</div>', unsafe_allow_html=True)
                cab[3].markdown('<div class="cabecera-bano">Min</div>', unsafe_allow_html=True)
                cab[4].markdown('<div class="cabecera-bano">OK</div>', unsafe_allow_html=True)
                cab[5].markdown('<div class="cabecera-bano">➡</div>', unsafe_allow_html=True)

                ocupados = st.session_state.ocupacion[st.session_state.planta][bano]

                for fila in range(2):
                    cols = st.columns([2,3,3,1,1,1])
                    key_base = make_key("zona", zona, "planta", st.session_state.planta, "bano", bano, "fila", fila)

                    if fila < len(ocupados):
                        # --- Fila OCUPADA ---
                        p = ocupados[fila]

                        # Minutos en vivo (para la tarjeta)
                        h_ent = datetime.strptime(p["h_entrada"], "%H:%M")
                        ahora = datetime.now()
                        minutos = int((ahora - h_ent.replace(
                            year=ahora.year,
                            month=ahora.month,
                            day=ahora.day)).total_seconds()/60)

                        cols[0].write(p["curso"])
                        cols[1].write(p["alumno"])
                        cols[2].write(p["profesor"])

                        if minutos > MAX_MINUTOS:
                            cols[3].markdown(f'<span class="minutos-alerta">{minutos}</span>', unsafe_allow_html=True)
                        else:
                            cols[3].write(minutos)

                        ok = cols[4].checkbox("", value=True, key=make_key("ok", key_base))

                        obs = ""
                        if not ok:
                            obs = st.text_input("", key=make_key("obs", key_base), placeholder="Observaciones")

                        if cols[5].button("➡", key=make_key("fin", key_base)):
                            estado_final = "OK" if ok else "INCIDENCIA"

                            conn = init_db(st.session_state.planta)
                            conn.execute("""
                                INSERT INTO visitas
                                (fecha, planta, bano, alumno, curso, profesor, h_entrada, h_salida, estado, observaciones, exportado)
                                VALUES (?,?,?,?,?,?,?,?,?,?,?)
                            """, (
                                datetime.now().strftime("%Y-%m-%d"),
                                st.session_state.planta,
                                bano,
                                p["alumno"],
                                p["curso"],
                                p["profesor"],
                                p["h_entrada"],
                                datetime.now().strftime("%H:%M"),
                                estado_final,
                                obs,
                                0
                            ))
                            conn.commit()

                            st.session_state.ocupacion[st.session_state.planta][bano].remove(p)
                            st.rerun()

                    else:
                        # --- Fila VACÍA ---
                        cursos = ["Seleccionar"] + sorted(df_alumnos["Curso"].unique())
                        curso = cols[0].selectbox("", cursos, key=make_key("curso", key_base))

                        alumnos_disp = []
                        if curso != "Seleccionar":
                            alumnos_disp = df_alumnos[df_alumnos["Curso"] == curso]["Nombre"].tolist()
                        alumnos_disp = ["Seleccionar"] + alumnos_disp
                        alumno = cols[1].selectbox("", alumnos_disp, key=make_key("alumno", key_base))

                        profesores = ["Seleccionar"] + lista_profesores
                        profesor = cols[2].selectbox("", profesores, key=make_key("prof", key_base))

                        cols[3].write("")
                        cols[4].write("")

                        if alumno_en_bano(alumno):
                            cols[5].warning("Este alumno ya está en otro baño")
                        else:
                            with cols[5]:
                                st.markdown('<div class="btn-alta-wrap">', unsafe_allow_html=True)
                                clicked = st.button("🟢", key=make_key("entrada", key_base))
                                st.markdown('</div>', unsafe_allow_html=True)

                                if clicked:
                                    if curso == "Seleccionar" or alumno == "Seleccionar" or profesor == "Seleccionar":
                                        st.warning("Debes seleccionar curso, alumno y profesor")
                                    else:
                                        st.session_state.ocupacion[st.session_state.planta][bano].append({
                                            "alumno": alumno,
                                            "curso": curso,
                                            "profesor": profesor,
                                            "h_entrada": datetime.now().strftime("%H:%M")
                                        })
                                        st.rerun()

# ----------------------------
# HISTÓRICO (DE LA PLANTA ACTUAL)
# ----------------------------
with tab_hist:
    st.subheader("Histórico de visitas (planta actual)")

    conn = init_db(st.session_state.planta)
    # minutos = diferencia en minutos con fecha+hora vía julianday (robusto)
    df = pd.read_sql_query("""
        SELECT
            id,
            fecha,
            planta,
            bano,
            curso,
            alumno,
            profesor,
            h_entrada,
            h_salida,
            CAST(
              (julianday(fecha || ' ' || h_salida) - julianday(fecha || ' ' || h_entrada)) * 24 * 60
              AS INTEGER
            ) AS minutos,
            estado,
            observaciones,
            exportado
        FROM visitas
        ORDER BY id DESC
    """, conn)
    conn.close()

    st.dataframe(df, use_container_width=True)