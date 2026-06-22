import os
import re
import math
import calendar
import datetime
import base64
from datetime import date
from pathlib import Path
from io import BytesIO
from collections import defaultdict

import pandas as pd
import pulp
import streamlit as st
import altair as alt

# =========================================================
# CONFIGURACIÓN GENERAL DE LA APP
# =========================================================
st.set_page_config(
    page_title="Sistema de Asignación de Personal",
    layout="wide",
    initial_sidebar_state="expanded"
)

APP_DATA_DIR = Path(__file__).resolve().parent / "data_turnos_app"
AJ_CUENTA_COMO_TRABAJO = True
MARGEN_D1 = 1
MARGEN_INICIO = 3
EPS = 1e-6

# Límites de resolución del modelo mensual rápido.
# Evitan que CBC se quede demasiado tiempo intentando demostrar optimalidad exacta
# en las etapas secundarias; acepta soluciones enteras factibles dentro del gap.
TIEMPO_MAX_ETAPA_2 = 180
TIEMPO_MAX_ETAPA_3 = 120
GAP_REL_ETAPA_2 = 0.08
GAP_REL_ETAPA_3 = 0.08

# =========================================================
# ESTILO VISUAL
# =========================================================
st.markdown("""
<style>

/* =========================
   TIPOGRAFÍA GENERAL
========================= */
html, body, [class*="css"] {
    font-family: Georgia, "Times New Roman", serif !important;
}

/* =========================
   FONDO GENERAL
========================= */
.stApp {
    background: linear-gradient(180deg, #f4f8fb 0%, #eaf3f8 100%) !important;
}

/* =========================
   CONTENEDOR PRINCIPAL
========================= */
.block-container {
    padding-top: 0.8rem !important;
    padding-left: 2.4rem !important;
    padding-right: 2.4rem !important;
    padding-bottom: 2rem !important;
    max-width: 1450px !important;
}
/* =========================
   SIDEBAR
========================= */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #031b2e 0%, #073b5c 55%, #0b5f8f 100%) !important;
    border-right: none !important;
}

section[data-testid="stSidebar"] * {
    color: white !important;
}

section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] label {
    color: white !important;
}

/* Logo */
section[data-testid="stSidebar"] img {
    margin-bottom: 1rem;
}

/* Inputs del sidebar */
section[data-testid="stSidebar"] input {
    color: #082f49 !important;
    background-color: white !important;
    border-radius: 10px !important;
}

/* Selectbox del sidebar: caja cerrada */
section[data-testid="stSidebar"] div[data-baseweb="select"] {
    background-color: white !important;
    border-radius: 10px !important;
}

section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
    background-color: white !important;
    color: #082f49 !important;
    border-radius: 10px !important;
}

/* Texto seleccionado del mes */
section[data-testid="stSidebar"] div[data-baseweb="select"] span,
section[data-testid="stSidebar"] div[data-baseweb="select"] div {
    color: #082f49 !important;
}

/* Flecha del selectbox */
section[data-testid="stSidebar"] div[data-baseweb="select"] svg {
    fill: #0B5F8F !important;
}

/* Flechas del number input */
section[data-testid="stSidebar"] button {
    color: #0B5F8F !important;
}

section[data-testid="stSidebar"] button svg {
    fill: #0B5F8F !important;
}

/* Separadores del sidebar */
section[data-testid="stSidebar"] hr {
    background: rgba(255,255,255,0.25) !important;
}

/* =========================
   TÍTULOS GENERALES
========================= */
h1, h2, h3, h4, h5, h6 {
    font-family: Georgia, "Times New Roman", serif !important;
    color: #20384a !important;
    font-weight: 700 !important;
}

h1 {
    font-size: 2rem !important;
}

h2 {
    font-size: 1.45rem !important;
}

h3 {
    font-size: 1.15rem !important;
}

h4, h5, h6 {
    font-size: 1.05rem !important;
}

/* =========================
   ENCABEZADO PRINCIPAL
========================= */
.app-header {
    background: linear-gradient(90deg, #082f49 0%, #0b5f8f 60%, #0C7BA1 100%);
    padding: 1.65rem 1.9rem;
    border-radius: 20px;
    margin-top: 0rem !important;
    margin-bottom: 1.5rem;
    box-shadow: 0 8px 22px rgba(8, 47, 73, 0.18);
}
.app-title {
    font-family: Georgia, "Times New Roman", serif !important;
    color: #ffffff !important;
    font-size: 2.05rem !important;
    font-weight: 700 !important;
    line-height: 1.2 !important;
    margin-bottom: 0.45rem !important;
}

.app-subtitle {
    color: #eaf8ff !important;
    font-size: 1rem !important;
    line-height: 1.5 !important;
    margin-bottom: 0 !important;
}

/* =========================
   CAJAS BLANCAS
========================= */
.app-box {
    background: white;
    border: 1px solid #d9e8f0;
    border-radius: 18px;
    padding: 1.25rem 1.35rem;
    margin-bottom: 1.2rem;
    box-shadow: 0 5px 16px rgba(8, 47, 73, 0.07);
}

.app-box h3 {
    color: #20384a !important;
    margin-bottom: 0.55rem !important;
}

.app-box p {
    color: #334e5c !important;
    font-size: 0.98rem;
    line-height: 1.55;
    margin-bottom: 0 !important;
}

/* Texto general */
p, span, div, label {
    color: #1f3340;
}

/* Pero dentro del encabezado se mantiene blanco */
.app-header div,
.app-header p,
.app-header span {
    color: #ffffff !important;
}

/* =========================
   PESTAÑAS
========================= */
button[data-baseweb="tab"] {
    background: white !important;
    color: #274457 !important;
    border-radius: 12px !important;
    border: 1px solid #d9e8f0 !important;
    padding: 0.65rem 1rem !important;
    font-weight: 700 !important;
    margin-right: 0.25rem !important;
}

button[data-baseweb="tab"] p {
    color: #274457 !important;
}

button[data-baseweb="tab"][aria-selected="true"] {
    background: #8edbfd !important;
    color: #083344 !important;
    border: 1px solid #8edbfd !important;
}

button[data-baseweb="tab"][aria-selected="true"] p {
    color: #083344 !important;
}

div[data-baseweb="tab-highlight"] {
    background-color: #0C7BA1 !important;
}

/* =========================
   BOTONES
========================= */
.stButton > button {
    background: linear-gradient(90deg, #0b5f8f 0%, #0C7BA1 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.65rem 1.15rem !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 12px rgba(11, 95, 143, 0.20);
}

.stButton > button * {
    color: white !important;
}

.stButton > button:hover {
    background: linear-gradient(90deg, #084c73 0%, #0c7ba1 100%) !important;
    color: white !important;
}

/* Botones de descarga */
.stDownloadButton > button {
    background: linear-gradient(90deg, #0b5f8f 0%, #1597bb 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.65rem 1.15rem !important;
    font-weight: 700 !important;
}

.stDownloadButton > button * {
    color: white !important;
}

/* =========================
   FILE UPLOADER
========================= */
[data-testid="stFileUploader"] {
    background: white !important;
    border: 1px solid #d9e8f0 !important;
    border-radius: 16px !important;
    padding: 1rem !important;
}

/* =========================
   INPUTS
========================= */
input, textarea {
    border-radius: 10px !important;
}

/* =========================
   TABLAS
========================= */
[data-testid="stDataFrame"] {
    border-radius: 16px !important;
    overflow: hidden !important;
    border: 1px solid #d9e8f0 !important;
    box-shadow: 0 5px 16px rgba(8, 47, 73, 0.07);
}

/* =========================
   MENSAJES
========================= */
[data-testid="stSuccessMessage"],
[data-testid="stInfoMessage"],
[data-testid="stErrorMessage"],
[data-testid="stWarningMessage"] {
    border-radius: 14px !important;
}

/* =========================
   SEPARADORES
========================= */
hr {
    border: none;
    height: 1px;
    background: #d9e8f0;
    margin: 1.2rem 0;
}

div[data-baseweb="tab-border"] {
    background-color: #d9e8f0 !important;
}

</style>
""", unsafe_allow_html=True)
# =========================================================
# OCULTAR BARRA SUPERIOR DE STREAMLIT
# =========================================================
st.markdown("""
<style>

/* Dejar visible el header porque ahí está el botón izquierdo del menú lateral */
header[data-testid="stHeader"] {
    display: block !important;
    visibility: visible !important;
    height: 3rem !important;
    background: transparent !important;
}

/* Dejar visible el botón izquierdo del sidebar */
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapseButton"] {
    display: flex !important;
    visibility: visible !important;
    opacity: 1 !important;
    z-index: 999999 !important;
}

/* Dejar visible el sidebar */
section[data-testid="stSidebar"] {
    display: block !important;
    visibility: visible !important;
}

/* Ocultar solamente Deploy, menú de tres puntos y footer */
[data-testid="stDeployButton"],
#MainMenu,
footer {
    display: none !important;
    visibility: hidden !important;
}

/* NO ocultar stToolbar porque puede esconder el botón izquierdo */

.block-container {
    padding-top: 0.8rem !important;
}

</style>
""", unsafe_allow_html=True)

# =========================================================
# ESTILO VISUAL DEL DASHBOARD
# =========================================================
st.markdown("""
<style>
.dashboard-card {
    background: #ffffff;
    border: 1px solid #d9e8f0;
    border-radius: 18px;
    padding: 1.05rem 1.15rem;
    min-height: 118px;
    box-shadow: 0 5px 16px rgba(8, 47, 73, 0.08);
}
.dashboard-card-title {
    font-family: Georgia, "Times New Roman", serif !important;
    font-size: 0.88rem;
    color: #476173 !important;
    font-weight: 700;
    margin-bottom: 0.45rem;
}
.dashboard-card-value {
    font-family: Georgia, "Times New Roman", serif !important;
    font-size: 2rem;
    color: #082f49 !important;
    font-weight: 800;
    line-height: 1.1;
}
.dashboard-card-note {
    font-size: 0.82rem;
    color: #5b7280 !important;
    margin-top: 0.45rem;
}
.dashboard-card-value-pct {
    font-family: Georgia, "Times New Roman", serif !important;
    font-size: 1.75rem;
    color: #0b5f8f !important;
    font-weight: 800;
    line-height: 1.1;
}
.dashboard-section {
    background: white;
    border: 1px solid #d9e8f0;
    border-radius: 18px;
    padding: 1.15rem 1.25rem;
    margin-top: 1rem;
    margin-bottom: 1rem;
    box-shadow: 0 5px 16px rgba(8, 47, 73, 0.06);
}
.dashboard-section h3 {
    color: #20384a !important;
    margin-bottom: 0.7rem !important;
}
.dashboard-inline-title {
    font-family: Georgia, "Times New Roman", serif !important;
    color: #20384a !important;
    font-size: 1.05rem !important;
    font-weight: 700 !important;
    margin-top: 0.85rem !important;
    margin-bottom: 0.55rem !important;
}
.dashboard-chip {
    display: inline-block;
    background: #eaf8ff;
    color: #083344 !important;
    border: 1px solid #bdeafd;
    padding: 0.25rem 0.55rem;
    border-radius: 999px;
    font-size: 0.82rem;
    font-weight: 700;
    margin-right: 0.35rem;
    margin-bottom: 0.35rem;
}
.alerta-ok {
    background: #eafaf1;
    border-left: 5px solid #3DCC6C;
    padding: 0.8rem 1rem;
    border-radius: 12px;
    color: #14532d !important;
    margin-bottom: 0.5rem;
}
.alerta-revisar {
    background: #fff7ed;
    border-left: 5px solid #F5B041;
    padding: 0.8rem 1rem;
    border-radius: 12px;
    color: #7c2d12 !important;
    margin-bottom: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# RUTAS Y UTILIDADES DE ARCHIVOS
# =========================================================
def carpeta_year(year: int) -> Path:
    ruta = APP_DATA_DIR / str(year)
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def ruta_base(year: int) -> Path:
    return carpeta_year(year) / "BaseDatos.xlsx"


def ruta_anual(year: int) -> Path:
    return carpeta_year(year) / "solucion_final_revisada.xlsx"


def nombre_archivo_mensual(year: int, month: int) -> str:
    return f"mensual_{year}_{month:02d}.xlsx"


def ruta_mensual(year: int, month: int) -> Path:
    return carpeta_year(year) / nombre_archivo_mensual(year, month)


def guardar_archivo_subido(archivo, destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(archivo.getbuffer())


def archivo_a_bytes(ruta: Path) -> bytes:
    return ruta.read_bytes()


def dataframes_a_excel_bytes(hojas: dict) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for nombre_hoja, df in hojas.items():
            df.to_excel(writer, sheet_name=nombre_hoja, index=False)
    return output.getvalue()


def crear_base_plantilla(destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    df_asistentes = pd.DataFrame(columns=[
        "Persona",
        "Rol",
        "Género",
        "Semanas de Vacaciones",
        "Esteriliza",
        "F1",
        "F2",
        "F3",
        "F4",
        "F5",
        "F6",
        "F7",
        "F8",
        "F9",
        "F10",
        "F11",
        "F12",
    ])
    df_saldo = pd.DataFrame(columns=[
        "Persona",
        "Saldo acumulado",
        "LB inicial",
        "Libres acumulados disponibles",
    ])
    with pd.ExcelWriter(destino, engine="openpyxl") as writer:
        df_asistentes.to_excel(writer, sheet_name="Asistentes", index=False)
        df_saldo.to_excel(writer, sheet_name="Saldo", index=False)


def leer_hojas_excel(ruta: Path) -> list:
    if not ruta.exists():
        return []
    return pd.ExcelFile(ruta, engine="openpyxl").sheet_names


def guardar_hoja_excel(ruta: Path, hoja: str, df: pd.DataFrame) -> None:
    with pd.ExcelWriter(
        ruta,
        engine="openpyxl",
        mode="a",
        if_sheet_exists="replace"
    ) as writer:
        df.to_excel(writer, sheet_name=hoja, index=False)


def validar_archivo_existe(ruta: Path, nombre: str):
    if not ruta.exists():
        raise FileNotFoundError(f"No existe el archivo {nombre}:\n{ruta}")


# =========================================================
# FUNCIONES AUXILIARES DEL MODELO MENSUAL
# =========================================================
def normalizar_texto(x):
    return str(x).strip().lower().replace("_", " ").replace("  ", " ")


def limpiar_texto(x):
    if pd.isna(x):
        return ""
    return str(x).strip().upper()


def buscar_columna(df, candidatos, obligatoria=True):
    mapa = {normalizar_texto(c): c for c in df.columns}
    for cand in candidatos:
        clave = normalizar_texto(cand)
        if clave in mapa:
            return mapa[clave]
    if obligatoria:
        raise ValueError(f"No se encontró ninguna de estas columnas: {candidatos}")
    return None


def leer_excel_seguro(ruta, hoja):
    try:
        return pd.read_excel(ruta, sheet_name=hoja, engine="openpyxl")
    except PermissionError:
        raise PermissionError(
            f"No se puede abrir el archivo:\n{ruta}\n"
            f"Cierra Excel y vuelve a intentar."
        )


def obtener_mes_anterior(year, month):
    if month == 1:
        return year - 1, 12
    return year, month - 1


def obtener_columnas_dias(df):
    cols = []
    for c in df.columns:
        s = str(c).strip()
        if s.startswith("D") and s[1:].isdigit():
            cols.append(s)
    return sorted(cols, key=lambda x: int(x[1:]))


def es_uno(v):
    try:
        return int(float(v)) == 1
    except Exception:
        return str(v).strip().upper() in ["1", "SI", "SÍ", "S", "X", "TRUE", "VERDADERO"]


def obtener_estado_modelo(model):
    estado = pulp.LpStatus.get(model.status, str(model.status))
    sol_status = getattr(model, "sol_status", None)
    estado_solucion = pulp.LpSolution.get(sol_status, str(sol_status))
    return estado, estado_solucion


def solucion_aceptable(model):
    """
    Acepta una solución óptima o una solución entera factible encontrada
    dentro del límite de tiempo. Esto evita descartar una solución válida
    solo porque CBC no terminó de probar optimalidad exacta.
    """
    sol_status = getattr(model, "sol_status", None)
    return (
        model.status == pulp.LpStatusOptimal
        or sol_status == pulp.LpSolutionOptimal
        or sol_status == pulp.LpSolutionIntegerFeasible
    )

# =========================================================
# MODELO ANUAL - MISMA LÓGICA MATEMÁTICA DEL PRIMER CÓDIGO
# =========================================================
def _convertir_esteriliza(valor):
    """Convierte valores de la columna Esteriliza/F6 a 1/0."""
    if pd.isna(valor):
        return 0
    if isinstance(valor, str):
        return 1 if valor.strip().lower() in {"1", "si", "sí", "s", "x", "true", "verdadero"} else 0
    try:
        return 1 if int(valor) == 1 else 0
    except Exception:
        return 0


def ejecutar_modelo_anual(
    ruta_base_excel: Path,
    year: int,
    vacaciones_fijas: dict,
    dotacion_turnos: dict = None,
    dotacion_turnos_min: dict = None,
    dotacion_turnos_max: dict = None,
    min_esteriliza_noche: int = 2,
):
    """Ejecuta el modelo anual usando la lógica del archivo 'Ultimo Modelo Anual.py'."""
    columnas_requeridas = ["Persona", "Rol", "Semanas de Vacaciones"]
    xls_base_anual = pd.ExcelFile(ruta_base_excel, engine="openpyxl")
    df = None

    for hoja in ["Asistentes", "Hoja1", "Hoja3", *xls_base_anual.sheet_names]:
        if hoja not in xls_base_anual.sheet_names:
            continue
        df_temp = pd.read_excel(ruta_base_excel, sheet_name=hoja, engine="openpyxl")
        df_temp.columns = [str(col).strip() for col in df_temp.columns]
        if all(col in df_temp.columns for col in columnas_requeridas):
            df = df_temp
            break

    if df is None:
        df = pd.read_excel(ruta_base_excel, engine="openpyxl")
        df.columns = [str(col).strip() for col in df.columns]

    columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
    if columnas_faltantes:
        raise KeyError(
            "La base de datos no tiene estas columnas básicas: "
            f"{columnas_faltantes}. Columnas encontradas: {list(df.columns)}"
        )

    if "Esteriliza" in df.columns:
        columna_esteriliza = "Esteriliza"
    elif "F6" in df.columns:
        columna_esteriliza = "F6"
    else:
        raise KeyError(
            "Falta la columna 'Esteriliza' o la columna alternativa 'F6' "
            "para identificar quién puede esterilizar."
        )

    df["Esteriliza"] = df[columna_esteriliza].apply(_convertir_esteriliza)
    df = df[df["Rol"] != 4].copy()
    df = df[df["Persona"].notna()].copy()
    df["Persona"] = df["Persona"].astype(str).str.strip()
    df = df[df["Persona"] != ""].copy()
    df = df.set_index("Persona")

    P = list(df.index)
    T = ["Mañana", "Tarde", "Noche"]
    num_semanas = datetime.date(year, 12, 31).isocalendar()[1]
    S = range(1, num_semanas + 1)

    i = df["Rol"].astype(int).to_dict()
    W = df["Semanas de Vacaciones"].astype(int).to_dict()
    genero = df["Género"].to_dict() if "Género" in df.columns else {p: "" for p in P}
    E = df["Esteriliza"].astype(int).to_dict()
    P_esteriliza = [p for p in P if E[p] == 1]

    if not P_esteriliza:
        raise ValueError("No hay ninguna persona marcada como capaz de esterilizar en 'Esteriliza' o 'F6'.")

    # Vacaciones fijas recibidas desde la interfaz.
    # Importante: se normaliza el nombre de la persona porque Excel puede traer
    # espacios invisibles; si no se hace esto, las semanas seleccionadas en la
    # interfaz no coinciden con el índice del modelo y el solver las ignora.
    vacaciones_fijas_norm = {}
    for persona_key, semanas_sel in (vacaciones_fijas or {}).items():
        persona_norm = str(persona_key).strip()
        semanas_limpias = []
        for s in semanas_sel or []:
            try:
                s_int = int(s)
            except Exception:
                continue
            if 1 <= s_int <= num_semanas and s_int not in semanas_limpias:
                semanas_limpias.append(s_int)
        vacaciones_fijas_norm[persona_norm] = semanas_limpias

    V = {p: list(vacaciones_fijas_norm.get(str(p).strip(), [])) for p in P}

    for p in P:
        if len(V[p]) > int(W[p]):
            raise ValueError(
                f"La persona {p} tiene {len(V[p])} semanas fijas seleccionadas, "
                f"pero solo tiene {int(W[p])} semanas de vacaciones disponibles."
            )

    if dotacion_turnos_min is None or dotacion_turnos_max is None:
        # Compatibilidad con versiones anteriores de la interfaz.
        if dotacion_turnos is not None:
            dotacion_turnos_min = {t: int(dotacion_turnos.get(t, 0)) for t in T}
            dotacion_turnos_max = {t: int(dotacion_turnos.get(t, 0)) for t in T}
        else:
            dotacion_turnos_min = {"Mañana": 11, "Tarde": 10, "Noche": 3}
            dotacion_turnos_max = {"Mañana": 20, "Tarde": 20, "Noche": 4}

    r_min = {t: int(dotacion_turnos_min.get(t, 0)) for t in T}
    r_max = {t: int(dotacion_turnos_max.get(t, len(P))) for t in T}
    min_esteriliza_noche = int(min_esteriliza_noche)

    for t in T:
        if r_max[t] < r_min[t]:
            raise ValueError(f"En {t}, el máximo ({r_max[t]}) no puede ser menor que el mínimo ({r_min[t]}).")

    model = pulp.LpProblem("Modelo_TFG_Final", pulp.LpMinimize)

    X = pulp.LpVariable.dicts("X", (P, S, T), 0, 1, cat="Binary")
    Z = pulp.LpVariable.dicts("Z", (P, S), 0, 1, cat="Binary")
    H_vac = pulp.LpVariable.dicts("H_vac", S, lowBound=0, cat="Integer")
    N = pulp.LpVariable.dicts("N", (P, T), lowBound=0, cat="Integer")
    C = pulp.LpVariable.dicts("C", (P, P, T), lowBound=0, cat="Continuous")
    D = pulp.LpVariable("D", lowBound=0, cat="Continuous")

    # A. Una actividad exacta por persona-semana.
    for p in P:
        for s in S:
            model += pulp.lpSum(X[p][s][t] for t in T) + Z[p][s] == 1

    # B. Vacaciones fijas y totales.
    for p in P:
        for s in V[p]:
            model += Z[p][s] == 1
        model += pulp.lpSum(Z[p][s] for s in S) == W[p]

    # C. Cobertura de turnos con mínimos y máximos.
    for t in T:
        for s in S:
            total_turno = pulp.lpSum(X[p][s][t] for p in P)
            model += total_turno >= r_min[t]
            model += total_turno <= r_max[t]

    # D. Asistente 2: máximo 1 por turno y sin noche.
    for s in S:
        for t in T:
            model += pulp.lpSum(X[p][s][t] for p in P if i[p] == 2) <= 1
            if t == "Noche":
                for p in P:
                    if i[p] == 2:
                        model += X[p][s][t] == 0

    # E. Mínimo 2 personas en vacaciones, con holgura penalizada si no se logra.
    for s in S:
        model += pulp.lpSum(Z[p][s] for p in P) + H_vac[s] >= 2

    # F. Mínimo configurable de personas que puedan esterilizar en noche.
    for s in S:
        model += pulp.lpSum(X[p][s]["Noche"] for p in P_esteriliza) >= min_esteriliza_noche

    # G. Máximo 6 semanas consecutivas en el mismo turno.
    for p in P:
        for t in T:
            for s in range(1, num_semanas - 6):
                model += pulp.lpSum(X[p][s + k][t] for k in range(7)) <= 6

    for p in P:
        for t in T:
            model += N[p][t] == pulp.lpSum(X[p][s][t] for s in S)

    for p in P:
        for p2 in P:
            if p >= p2:
                continue
            if i[p] == i[p2]:
                for t in T:
                    model += C[p][p2][t] >= N[p][t] - N[p2][t]
                    model += C[p][p2][t] >= N[p2][t] - N[p][t]
                    model += D >= C[p][p2][t]

    model += D + (pulp.lpSum(H_vac[s] for s in S) * 1000)
    model.solve(pulp.PULP_CBC_CMD(msg=0))

    estado = pulp.LpStatus[model.status]
    if estado != "Optimal":
        raise RuntimeError(f"No se encontró solución óptima para el modelo anual. Estado: {estado}.")

    data_final = []
    for p in P:
        fila = {"Género": genero[p], "Persona": p, "Rol": i[p]}
        for s in S:
            if pulp.value(Z[p][s]) > 0.5:
                fila[f"S{s}"] = "V"
            else:
                turno = "O"
                for t in T:
                    if pulp.value(X[p][s][t]) > 0.5:
                        turno = t[0]
                fila[f"S{s}"] = turno
        data_final.append(fila)

    df_res = pd.DataFrame(data_final)

    if "Género" in df_res.columns:
        df_res["orden_genero"] = df_res["Género"].map({
            "F": 0, "M": 1,
            "f": 0, "m": 1,
            "Femenino": 0, "Masculino": 1,
            "femenino": 0, "masculino": 1,
        }).fillna(99)
        df_res = df_res.sort_values(by=["orden_genero", "Persona"]).drop(columns=["orden_genero"])

    conteo_data = []
    for s in S:
        conteo_data.append({
            "Semana": f"S{s}",
            "V": int(sum(1 for p in P if pulp.value(Z[p][s]) > 0.5)),
            "M": int(sum(1 for p in P if pulp.value(X[p][s]["Mañana"]) > 0.5)),
            "T": int(sum(1 for p in P if pulp.value(X[p][s]["Tarde"]) > 0.5)),
            "N": int(sum(1 for p in P if pulp.value(X[p][s]["Noche"]) > 0.5)),
            "Min_M": r_min["Mañana"],
            "Max_M": r_max["Mañana"],
            "Min_T": r_min["Tarde"],
            "Max_T": r_max["Tarde"],
            "Min_N": r_min["Noche"],
            "Max_N": r_max["Noche"],
        })
    df_c = pd.DataFrame(conteo_data)

    return df_res, df_c


# =========================================================
# MODELO MENSUAL - MISMA LÓGICA MATEMÁTICA DEL SEGUNDO CÓDIGO (CON LOS CAMBIOS)
# =========================================================
def programar_mes(year, month, ruta_base_excel: Path, ruta_anual_excel: Path, carpeta_salida: Path):
    num_dias = calendar.monthrange(year, month)[1]
    D = list(range(1, num_dias + 1))
    domingos = [d for d in D if date(year, month, d).weekday() == 6]
    cant_domingos = len(domingos)

    print(f"\nMes: {month:02d}/{year}")
    print(f"Días del mes: {num_dias}")
    print(f"Domingos del mes: {cant_domingos}")

    validar_archivo_existe(ruta_base_excel, "base")
    validar_archivo_existe(ruta_anual_excel, "anual")

    # ---------------------------------------------
    # Detectar hojas del archivo base
    # ---------------------------------------------
    xls_base = pd.ExcelFile(ruta_base_excel, engine="openpyxl")
    hojas_base = xls_base.sheet_names

    if "Hoja3" in hojas_base:
        hoja_personas = "Hoja3"
    elif "Asistentes" in hojas_base:
        hoja_personas = "Asistentes"
    elif "Hoja1" in hojas_base:
        hoja_personas = "Hoja1"
    else:
        raise ValueError("No se encontró Hoja3, Asistentes ni Hoja1 en BaseDatos.xlsx")

    if "Hoja1" in hojas_base:
        hoja_info = "Hoja1"
    elif "Asistentes" in hojas_base:
        hoja_info = "Asistentes"
    else:
        hoja_info = hoja_personas

    # ---------------------------------------------
    # Leer archivos
    # ---------------------------------------------
    df_p = leer_excel_seguro(ruta_base_excel, hoja_personas)   # saldos/arrastres
    df_info = leer_excel_seguro(ruta_base_excel, hoja_info)      # capacidades funcionales
    df_anual = leer_excel_seguro(ruta_anual_excel, "Calendario")

    df_p.columns = df_p.columns.str.strip()
    df_info.columns = df_info.columns.str.strip()
    df_anual.columns = df_anual.columns.str.strip()

    col_persona_p = buscar_columna(df_p, ["Persona"])
    col_persona_info = buscar_columna(df_info, ["Persona"])
    col_persona_anual = buscar_columna(df_anual, ["Persona"])

    # Si la base nueva separa los saldos en una hoja llamada "Saldo", se anexan
    # aquí sin cambiar la estructura visual ni el flujo de la interfaz.
    if "Saldo" in hojas_base:
        try:
            df_saldo_base = leer_excel_seguro(ruta_base_excel, "Saldo")
            df_saldo_base.columns = df_saldo_base.columns.str.strip()
            col_persona_saldo = buscar_columna(df_saldo_base, ["Persona"], obligatoria=False)
            if col_persona_saldo is not None:
                df_p[col_persona_p] = df_p[col_persona_p].astype(str).str.strip()
                df_saldo_base[col_persona_saldo] = df_saldo_base[col_persona_saldo].astype(str).str.strip()
                columnas_para_unir = [col_persona_saldo] + [
                    c for c in df_saldo_base.columns
                    if c != col_persona_saldo and c not in df_p.columns
                ]
                if len(columnas_para_unir) > 1:
                    df_p = df_p.merge(
                        df_saldo_base[columnas_para_unir],
                        how="left",
                        left_on=col_persona_p,
                        right_on=col_persona_saldo,
                    )
                    if col_persona_saldo != col_persona_p and col_persona_saldo in df_p.columns:
                        df_p = df_p.drop(columns=[col_persona_saldo])
        except Exception:
            pass

    col_saldo = buscar_columna(
        df_p,
        ["Saldo acumulado", "Saldo_Acumulado_Inicial", "Saldo acumulado inicial"],
        obligatoria=False
    )

    col_lb_inicial = buscar_columna(
        df_p,
        ["LB inicial", "Libre biológico inicial", "Libre biologico inicial"],
        obligatoria=False
    )

    col_libres_disp = buscar_columna(
        df_p,
        ["Libres acumulados disponibles", "Libre acumulado disponible", "Libres disponibles", "Libre disponible"],
        obligatoria=False
    )

    col_esteriliza = buscar_columna(
        df_info,
        ["Esteriliza", "F6"],
        obligatoria=True
    )

    if col_saldo is None:
        df_p["Saldo acumulado"] = 0
        col_saldo = "Saldo acumulado"

    if col_lb_inicial is None:
        df_p["LB inicial"] = 0
        col_lb_inicial = "LB inicial"

    if col_libres_disp is None:
        df_p["Libres acumulados disponibles"] = 0
        col_libres_disp = "Libres acumulados disponibles"

    # ---------------------------------------------
    # Limpieza de datos
    # ---------------------------------------------
    df_p = df_p[df_p[col_persona_p].notna()].copy()
    df_info = df_info[df_info[col_persona_info].notna()].copy()
    df_anual = df_anual[df_anual[col_persona_anual].notna()].copy()

    df_p[col_persona_p] = df_p[col_persona_p].astype(str).str.strip()
    df_info[col_persona_info] = df_info[col_persona_info].astype(str).str.strip()
    df_anual[col_persona_anual] = df_anual[col_persona_anual].astype(str).str.strip()

    df_p = df_p[df_p[col_persona_p] != ""].copy()
    df_info = df_info[df_info[col_persona_info] != ""].copy()
    df_anual = df_anual[df_anual[col_persona_anual] != ""].copy()

    df_p[col_saldo] = pd.to_numeric(df_p[col_saldo], errors="coerce").fillna(0).astype(int)
    df_p[col_lb_inicial] = pd.to_numeric(df_p[col_lb_inicial], errors="coerce").fillna(0).astype(int)
    df_p[col_libres_disp] = pd.to_numeric(df_p[col_libres_disp], errors="coerce").fillna(0).astype(int)

    P = df_p[col_persona_p].tolist()

    saldo_inicial = dict(zip(df_p[col_persona_p], df_p[col_saldo]))
    lb_inicial = dict(zip(df_p[col_persona_p], df_p[col_lb_inicial]))
    libres_disp = dict(zip(df_p[col_persona_p], df_p[col_libres_disp]))
    
    # Inicializar estructuras para el historial de consecutividad (últimos 7 días)
    historial_trabajado = {p: [0] * 7 for p in P}
    historial_noche = {p: [0] * 7 for p in P}

    # Personas que pueden esterilizar (esto ya resume la condición relevante)
    personas_esteriliza_base = set(
        str(row[col_persona_info]).strip()
        for _, row in df_info.iterrows()
        if es_uno(row[col_esteriliza])
    )
    PERSONAS_ESTERILIZA = [p for p in P if p in personas_esteriliza_base]

    if len(PERSONAS_ESTERILIZA) == 0:
        raise ValueError("No se encontró ninguna persona con Esteriliza = 1 en Hoja1.")

    # total de L requeridos del mes
    total_req_l_mes = sum(cant_domingos + libres_disp[p] for p in P)

    # ---------------------------------------------
    # Leer arrastre del mes anterior
    # ---------------------------------------------
    year_prev, month_prev = obtener_mes_anterior(year, month)
    ruta_mes_anterior = APP_DATA_DIR / str(year_prev) / nombre_archivo_mensual(year_prev, month_prev)

    if os.path.exists(ruta_mes_anterior):
        try:
            xls_prev = pd.ExcelFile(ruta_mes_anterior, engine="openpyxl")

            if "Arrastre_Real_Siguiente_Mes" in xls_prev.sheet_names:
                hoja_arrastre = "Arrastre_Real_Siguiente_Mes"
            elif "Arrastre_Siguiente_Mes" in xls_prev.sheet_names:
                hoja_arrastre = "Arrastre_Siguiente_Mes"
            else:
                raise ValueError(
                    f"El archivo {ruta_mes_anterior} no tiene ni "
                    f"'Arrastre_Real_Siguiente_Mes' ni 'Arrastre_Siguiente_Mes'."
                )

            df_arrastre_prev = pd.read_excel(
                ruta_mes_anterior,
                sheet_name=hoja_arrastre,
                engine="openpyxl"
            )
            df_arrastre_prev.columns = df_arrastre_prev.columns.str.strip()

            col_persona_prev = buscar_columna(df_arrastre_prev, ["Persona"])
            col_saldo_prev = buscar_columna(df_arrastre_prev, ["Saldo acumulado siguiente mes"])
            col_lb_prev = buscar_columna(df_arrastre_prev, ["LB inicial siguiente mes"])
            col_libres_prev = buscar_columna(df_arrastre_prev, ["Libres acumulados disponibles siguiente mes"])

            df_arrastre_prev = df_arrastre_prev[df_arrastre_prev[col_persona_prev].notna()].copy()
            df_arrastre_prev[col_persona_prev] = df_arrastre_prev[col_persona_prev].astype(str).str.strip()
            df_arrastre_prev = df_arrastre_prev[df_arrastre_prev[col_persona_prev] != ""].copy()

            saldo_prev = dict(zip(
                df_arrastre_prev[col_persona_prev],
                pd.to_numeric(df_arrastre_prev[col_saldo_prev], errors="coerce").fillna(0).astype(int)
            ))
            lb_prev = dict(zip(
                df_arrastre_prev[col_persona_prev],
                pd.to_numeric(df_arrastre_prev[col_lb_prev], errors="coerce").fillna(0).astype(int)
            ))
            libres_prev = dict(zip(
                df_arrastre_prev[col_persona_prev],
                pd.to_numeric(df_arrastre_prev[col_libres_prev], errors="coerce").fillna(0).astype(int)
            ))

            for p in P:
                if p in saldo_prev:
                    saldo_inicial[p] = int(saldo_prev[p])
                if p in lb_prev:
                    lb_inicial[p] = int(lb_prev[p])
                if p in libres_prev:
                    libres_disp[p] = int(libres_prev[p])
            if "Calendario_Mensual" in xls_prev.sheet_names:
                df_cal_prev = pd.read_excel(xls_prev, sheet_name="Calendario_Mensual", engine="openpyxl")
                df_cal_prev.columns = df_cal_prev.columns.str.strip()
                col_p_cal = buscar_columna(df_cal_prev, ["Persona"])
                df_cal_prev[col_p_cal] = df_cal_prev[col_p_cal].astype(str).str.strip()
                
                cols_dias_prev = obtener_columnas_dias(df_cal_prev)
                ultimas_cols = cols_dias_prev[-7:]  # Guardar los últimos 7 días evaluados
                
                for _, row_c in df_cal_prev.iterrows():
                    p_name = str(row_c[col_p_cal]).strip()
                    if p_name in P:
                        valores = [str(row_c[c]).strip().upper() for c in ultimas_cols]
                        while len(valores) < 7:
                            valores.insert(0, "")
                        
                        # Si el estado es M, T o N, significa que trabajó de forma efectiva ese día
                        historial_trabajado[p_name] = [1 if v in ["M", "T", "N"] else 0 for v in valores]
                        historial_noche[p_name] = [1 if v == "N" else 0 for v in valores]
            # =========================================================================

            total_req_l_mes = sum(cant_domingos + libres_disp[p] for p in P)

            print(f"\nSe encontró arrastre del mes anterior: {ruta_mes_anterior}")
            print(f"Hoja utilizada: {hoja_arrastre}")
            print("Se aplicó correctamente el arrastre y el historial de consecutividad.")

        except Exception as e:
            print(f"\nNo se pudo leer el arrastre o el calendario anterior. Se usará la base original sin historial.")
            print("Detalle:", e)

            total_req_l_mes = sum(cant_domingos + libres_disp[p] for p in P)

            print(f"\nSe encontró arrastre del mes anterior: {ruta_mes_anterior}")
            print(f"Hoja utilizada: {hoja_arrastre}")
            print("Se aplicó correctamente el arrastre del mes anterior.")

        except Exception as e:
            print(f"\nNo se pudo leer el arrastre del mes anterior. Se usará la base original.")
            print("Detalle:", e)
    else:
        print(f"\nNo existe archivo del mes anterior ({ruta_mes_anterior}). Se usará la base original.")

    for p in P:
        if saldo_inicial[p] < 0 or saldo_inicial[p] > 11:
            raise ValueError(f"La persona {p} tiene saldo acumulado fuera de rango (0 a 11).")

    # ---------------------------------------------
    # Expandir anual a días del mes
    # ---------------------------------------------
    base_turn = {p: {d: "" for d in D} for p in P}

    mapa_cols_anual = {str(c).strip().upper(): c for c in df_anual.columns}
    row_anual_por_persona = {row[col_persona_anual]: row for _, row in df_anual.iterrows()}

    faltantes_persona = [p for p in P if p not in row_anual_por_persona]
    if faltantes_persona:
        raise ValueError(
            "Estas personas del mensual no aparecen en el anual:\n" +
            "\n".join(map(str, faltantes_persona))
        )

    for p in P:
        row = row_anual_por_persona[p]

        for d in D:
            semana_iso = date(year, month, d).isocalendar()[1]
            clave_semana = f"S{semana_iso}"

            if clave_semana not in mapa_cols_anual:
                raise ValueError(f"No existe la columna {clave_semana} en el archivo anual.")

            col_real = mapa_cols_anual[clave_semana]
            valor = "" if pd.isna(row[col_real]) else str(row[col_real]).strip().upper()

            if valor not in ["M", "T", "N", "V", "O"]:
                raise ValueError(
                    f"Valor inválido o vacío para {p}, día {d}, semana {clave_semana}: '{valor}'.\n"
                    f"Corrige primero el anual."
                )

            base_turn[p][d] = valor

    for p in P:
        for d in D:
            if base_turn[p][d] == "":
                raise ValueError(f"Quedó vacío el turno base de {p} en el día {d}.")

    # Validación de factibilidad para noche con esteriliza
    dias_imposibles_noche = []
    for d in D:
        candidatos_noche = [p for p in PERSONAS_ESTERILIZA if base_turn[p][d] == "N"]
        if len(candidatos_noche) == 0:
            dias_imposibles_noche.append(d)

    if dias_imposibles_noche:
        raise ValueError(
            "El anual deja días de noche sin ninguna persona con Esteriliza = 1. "
            f"Días problemáticos: {dias_imposibles_noche}"
        )

    # ---------------------------------------------
    # Indicadores base
    # ---------------------------------------------
    es_trabajable = {(p, d): 1 if base_turn[p][d] in ["M", "T", "N"] else 0 for p in P for d in D}
    es_N = {(p, d): 1 if base_turn[p][d] == "N" else 0 for p in P for d in D}
    total_trabajables = {p: sum(es_trabajable[p, d] for d in D) for p in P}

    # ---------------------------------------------
    # DOMINGOS EFECTIVOS POR PERSONA (solo si en esa semana tiene al menos un día trabajable)
    # ---------------------------------------------
    domingos_efectivos = {}
    for p in P:
        count = 0
        for d in domingos:
            semana_domingo = date(year, month, d).isocalendar()[1]
            # Ver si en esa semana la persona tiene al menos un día trabajable
            tiene_trabajo = any(
                base_turn[p][d2] in ["M", "T", "N"]
                for d2 in D
                if date(year, month, d2).isocalendar()[1] == semana_domingo
            )
            if tiene_trabajo:
                count += 1
        domingos_efectivos[p] = count

    # ---------------------------------------------
    # Total de LB fijos del mes
    # ---------------------------------------------
    total_lb_fijo_mes = 0

    for p in P:
        if base_turn[p][1] in ["M", "T"] and lb_inicial[p] == 1:
            total_lb_fijo_mes += 1

        for d in range(1, num_dias):
            if base_turn[p][d] == "N" and base_turn[p][d + 1] in ["M", "T"]:
                total_lb_fijo_mes += 1

    total_req_l_mes = sum(domingos_efectivos[p] + libres_disp[p] for p in P)
    META_LIBRES_DIA = (total_req_l_mes + total_lb_fijo_mes) / num_dias

    # ---------------------------------------------
    # Modelo
    # ---------------------------------------------
    model = pulp.LpProblem("Modelo_Mensual_CEYE", pulp.LpMinimize)

    L = pulp.LpVariable.dicts("L", (P, D), 0, 1, cat="Binary")
    LB = pulp.LpVariable.dicts("LB", (P, D), 0, 1, cat="Binary")

    G = {p: pulp.LpVariable(f"G_{p}", lowBound=0, cat="Integer") for p in P}
    R = {p: pulp.LpVariable(f"R_{p}", lowBound=0, upBound=11, cat="Integer") for p in P}
    W = {p: pulp.LpVariable(f"W_{p}", lowBound=0, cat="Integer") for p in P}

    Y = {(p, d): pulp.LpVariable(f"Y_{p}_{d}", 0, 1, cat="Binary") for p in P for d in D}
    A = {(p, d): pulp.LpVariable(f"A_{p}_{d}", 0, 1, cat="Binary") for p in P for d in D}
    O_var = {(p, d): pulp.LpVariable(f"O_{p}_{d}", 0, 1, cat="Binary") for p in P for d in D}
    I = {(p, d): pulp.LpVariable(f"I_{p}_{d}", lowBound=0, cat="Continuous") for p in P for d in D}
    F_var = {(p, d): pulp.LpVariable(f"F_{p}_{d}", lowBound=0, cat="Continuous") for p in P for d in D}
    C = {p: pulp.LpVariable(f"C_{p}", lowBound=0, cat="Continuous") for p in P}
    Dmax = pulp.LpVariable("Dmax", lowBound=0, cat="Continuous")

    # Variables para nivelación diaria de libres
    Hdia = pulp.LpVariable.dicts("Hdia", D, lowBound=0, cat="Continuous")
    DevPos = pulp.LpVariable.dicts("DevPos", D, lowBound=0, cat="Continuous")
    DevNeg = pulp.LpVariable.dicts("DevNeg", D, lowBound=0, cat="Continuous")
    PicoLibres = pulp.LpVariable("PicoLibres", lowBound=0, cat="Continuous")
    ValleLibres = pulp.LpVariable("ValleLibres", lowBound=0, cat="Continuous")

    # ---------------------------------------------
    # ETAPA 1: minimizar Dmax
    # ---------------------------------------------
    model += Dmax

    for p in P:
        for d in D:
            if es_trabajable[p, d] == 0:
                model += L[p][d] == 0
                model += LB[p][d] == 0

        for d in D:
            model += L[p][d] + LB[p][d] <= 1

        # LB inicial por arrastre
        if base_turn[p][1] in ["M", "T"] and lb_inicial[p] == 1:
            model += LB[p][1] == 1
        else:
            model += LB[p][1] == 0

        # LB por transición N -> M/T
        for d in range(1, num_dias):
            if base_turn[p][d] == "N" and base_turn[p][d + 1] in ["M", "T"]:
                model += LB[p][d + 1] == 1
            else:
                model += LB[p][d + 1] == 0

        trabajables_mes = sum(es_trabajable[p, d] for d in D)
        model += W[p] == trabajables_mes - pulp.lpSum(L[p][d] + LB[p][d] for d in D)

        # Conteo de saldo con días con actividad (se mantiene usando total_trabajables)
        model += saldo_inicial[p] + total_trabajables[p] == 12 * G[p] + R[p]

        # ---------------------------------------------
        # CAMBIO IMPORTANTE: desigualdad para permitir no tomar todos los libres si no hay días
        # ---------------------------------------------
        req_libres = domingos_efectivos[p] + libres_disp[p]
        dias_elegibles = [d for d in D if es_trabajable[p, d] == 1]
        model += pulp.lpSum(L[p][d] for d in dias_elegibles) <= req_libres

        # Variables de racha
        for d in D:
            model += Y[p, d] == es_trabajable[p, d] - L[p][d] - LB[p][d]

            if d == 1:
                model += A[p, d] >= Y[p, d]
            else:
                model += A[p, d] >= Y[p, d] - Y[p, d - 1]

            if d == num_dias:
                model += O_var[p, d] >= Y[p, d]
            else:
                model += O_var[p, d] >= Y[p, d] - Y[p, d + 1]

            for dp in range(1, d + 1):
                model += I[p, d] >= dp * A[p, dp]
                model += F_var[p, d] >= dp * O_var[p, dp]

        for d in D:
            model += C[p] >= F_var[p, d] - I[p, d] + Y[p, d]

        model += Dmax >= C[p]

    # Máximo 7 trabajados en ventana de 8
    for p in P:
        # Máximo 7 días consecutivos trabajados en cualquier ventana móvil de 8 días
        for d in D:
            dias_mes_actual = list(range(max(1, d - 7), d + 1))
            cant_mes_anterior = 8 - len(dias_mes_actual)
            
            hist_prev = historial_trabajado[p][-cant_mes_anterior:] if cant_mes_anterior > 0 else []
            model += sum(hist_prev) + pulp.lpSum(Y[p, k] for k in dias_mes_actual) <= 7

        # Máximo 6 noches trabajadas en cualquier ventana móvil de 7 días
        for d in D:
            dias_mes_actual = list(range(max(1, d - 6), d + 1))
            cant_mes_anterior = 7 - len(dias_mes_actual)
            
            hist_prev_n = historial_noche[p][-cant_mes_anterior:] if cant_mes_anterior > 0 else []
            model += sum(hist_prev_n) + pulp.lpSum(Y[p, k] for k in dias_mes_actual if es_N[p, k]) <= 6

    # ---------------------------------------------
    # Libres diarios y nivelación
    # ---------------------------------------------
    for d in D:
        model += Hdia[d] == pulp.lpSum(L[p][d] + LB[p][d] for p in P)

        # mínimo de libres diarios
        model += Hdia[d] >= 3

        # desviación respecto a meta promedio
        model += Hdia[d] - META_LIBRES_DIA == DevPos[d] - DevNeg[d]

        # pico y valle
        model += PicoLibres >= Hdia[d]
        model += ValleLibres <= Hdia[d]

    # ---------------------------------------------
    # Mínimo de personal trabajando por turno por día
    # ---------------------------------------------
    for d in D:
        model += pulp.lpSum(Y[p, d] for p in P if base_turn[p][d] == "M") >= 5
        model += pulp.lpSum(Y[p, d] for p in P if base_turn[p][d] == "T") >= 5
        model += pulp.lpSum(Y[p, d] for p in P if base_turn[p][d] == "N") >= 2

        # En noche debe quedar al menos una persona activa que pueda esterilizar
        # (comentado originalmente en la interfaz, lo dejamos igual)
        # model += pulp.lpSum(
        #     Y[p, d]
        #     for p in PERSONAS_ESTERILIZA
        #     if base_turn[p][d] == "N"
        # ) >= 1

    # ---------------------------------------------

    print("\nResolviendo modelo - etapa 1 (minimizar Dmax)...")
    model.solve(pulp.PULP_CBC_CMD(msg=0))

    estado1, sol1 = obtener_estado_modelo(model)
    print("Estado del modelo etapa 1:", estado1, "| Solución:", sol1)

    if not solucion_aceptable(model):
        raise RuntimeError("No se encontró solución válida en etapa 1 del modelo mensual.")

    best_dmax = pulp.value(Dmax)

    # ---------------------------------------------
    # ETAPA 2: nivelar libres por día
    # ---------------------------------------------
    dev_total_expr = pulp.lpSum(DevPos[d] + DevNeg[d] for d in D)

    model += Dmax <= best_dmax + EPS, "Fijar_Dmax_Optimo"
    model.setObjective(dev_total_expr)

    print("Resolviendo modelo - etapa 2 (nivelar libres por día)...")
    model.solve(pulp.PULP_CBC_CMD(
        msg=0,
        timeLimit=TIEMPO_MAX_ETAPA_2,
        gapRel=GAP_REL_ETAPA_2
    ))

    estado2, sol2 = obtener_estado_modelo(model)
    print("Estado del modelo etapa 2:", estado2, "| Solución:", sol2)

    if not solucion_aceptable(model):
        raise RuntimeError("No se encontró solución válida en etapa 2 del modelo mensual.")

    if estado2 != "Optimal":
        print(
            "Etapa 2 terminada con la mejor solución factible encontrada "
            "dentro del límite de tiempo."
        )

    best_dev_total = pulp.value(dev_total_expr)

    # ---------------------------------------------
    # ETAPA 3: reducir brecha pico-valle (con holgura 1.0)
    # ---------------------------------------------
    model += dev_total_expr <= best_dev_total + 1.0, "Fijar_Desviacion_Optima"
    model.setObjective(PicoLibres - ValleLibres)

    print("Resolviendo modelo - etapa 3 (reducir brecha entre días)...")
    model.solve(pulp.PULP_CBC_CMD(
        msg=0,
        timeLimit=TIEMPO_MAX_ETAPA_3,
        gapRel=GAP_REL_ETAPA_3
    ))

    estado3, sol3 = obtener_estado_modelo(model)
    print("Estado del modelo etapa 3:", estado3, "| Solución:", sol3)

    if not solucion_aceptable(model):
        raise RuntimeError("No se encontró solución válida en etapa 3 del modelo mensual.")

    if estado3 != "Optimal":
        print(
            "Etapa 3 terminada con la mejor solución factible encontrada "
            "dentro del límite de tiempo."
        )

    # ---------------------------------------------
    # Calendario final
    # ---------------------------------------------
    data = []

    for p in P:
        fila = {
            "Persona": p,
            "Tipo": "Regular",
            "Saldo inicial": int(saldo_inicial[p]),
            "LB inicial": int(lb_inicial[p]),
            "Libres acumulados disponibles": int(libres_disp[p]),
            "Libres generados este mes": int(round(pulp.value(G[p]))),
            "Residuo final": int(round(pulp.value(R[p]))),
            "Días con actividad": int(total_trabajables[p]),
        }

        for d in D:
            if base_turn[p][d] in ["V", "O"]:
                fila[f"D{d}"] = base_turn[p][d]
            elif pulp.value(LB[p][d]) > 0.5:
                fila[f"D{d}"] = "LB"
            elif pulp.value(L[p][d]) > 0.5:
                fila[f"D{d}"] = "L"
            else:
                fila[f"D{d}"] = base_turn[p][d]

        data.append(fila)

    df_final = pd.DataFrame(data)

    # ---------------------------------------------
    # Resumen
    # ---------------------------------------------
    resumen = []

    for p in P:
        libres_ord = sum(1 for d in D if pulp.value(L[p][d]) > 0.5)
        libres_bio = sum(1 for d in D if pulp.value(LB[p][d]) > 0.5)
        vac = sum(1 for d in D if base_turn[p][d] == "V")
        otras = sum(1 for d in D if base_turn[p][d] == "O")

        resumen.append({
            "Persona": p,
            "Saldo inicial": int(saldo_inicial[p]),
            "Libres acumulados disponibles": int(libres_disp[p]),
            "Libres ordinarios": libres_ord,
            "Libres biológicos": libres_bio,
            "Vacaciones": vac,
            "Otras ausencias": otras,
            "Libres generados este mes": int(round(pulp.value(G[p]))),
            "Residuo final": int(round(pulp.value(R[p]))),
            "Días con actividad": int(total_trabajables[p]),
        })

    df_resumen = pd.DataFrame(resumen)

    # ---------------------------------------------
    # Resumen diario de libres
    # ---------------------------------------------
    resumen_dias = []

    for d in D:
        h = pulp.value(Hdia[d])
        dev = abs(h - META_LIBRES_DIA)

        resumen_dias.append({
            "Dia": d,
            "Libres totales": round(h, 4),
            "Meta promedio": round(META_LIBRES_DIA, 4),
            "Desviacion absoluta": round(dev, 4)
        })

    df_resumen_dias = pd.DataFrame(resumen_dias)

    # ---------------------------------------------
    # Arrastre al siguiente mes (con acumulación de libres no tomados)
    # ---------------------------------------------
    arrastre = []

    for p in P:
        lb_sig = 0
        if base_turn[p][num_dias] == "N" and pulp.value(L[p][num_dias]) < 0.5:
            lb_sig = 1

        # Calcular cuántos libres debió tomar y cuántos realmente tomó
        libres_tomados = sum(1 for d in D if pulp.value(L[p][d]) > 0.5)
        req_libres = domingos_efectivos[p] + libres_disp[p]
        libres_no_tomados = max(0, req_libres - libres_tomados)

        arrastre.append({
            "Persona": p,
            "Saldo acumulado siguiente mes": int(round(pulp.value(R[p]))),
            "LB inicial siguiente mes": lb_sig,
            "Libres acumulados disponibles siguiente mes": int(round(pulp.value(G[p]))) + libres_no_tomados
        })

    df_arrastre = pd.DataFrame(arrastre)

    # ---------------------------------------------
    # Guardar
    # ---------------------------------------------
    carpeta_salida.mkdir(parents=True, exist_ok=True)
    nombre_archivo_salida = nombre_archivo_mensual(year, month)
    ruta_salida = carpeta_salida / nombre_archivo_salida

    with pd.ExcelWriter(ruta_salida, engine="openpyxl") as writer:
        df_final.to_excel(writer, sheet_name="Calendario_Mensual", index=False)
        df_resumen.to_excel(writer, sheet_name="Resumen", index=False)
        df_arrastre.to_excel(writer, sheet_name="Arrastre_Siguiente_Mes", index=False)
        df_resumen_dias.to_excel(writer, sheet_name="Resumen_Diario_Libres", index=False)

    print(f"\nArchivo generado en:\n{ruta_salida}")
    print(f"Dmax final: {pulp.value(Dmax):.4f}")
    print(f"Desviación total de libres: {pulp.value(dev_total_expr):.4f}")
    print(f"Brecha pico-valle de libres: {pulp.value(PicoLibres - ValleLibres):.4f}")
    print(f"Meta promedio de libres por día: {META_LIBRES_DIA:.4f}")

    return {
        "ruta_salida": ruta_salida,
        "df_final": df_final,
        "df_resumen": df_resumen,
        "df_arrastre": df_arrastre,
        "df_resumen_dias": df_resumen_dias,
        "dmax": pulp.value(Dmax),
        "desviacion_total": pulp.value(dev_total_expr),
        "brecha_pico_valle": pulp.value(PicoLibres - ValleLibres),
        "meta_libres_dia": META_LIBRES_DIA,
        "hoja_arrastre_utilizada": hoja_arrastre if 'hoja_arrastre' in locals() else "Base original",
    }




# =========================================================
# CIERRE REAL - MISMA LÓGICA DEL SEGUNDO CÓDIGO
# =========================================================
def cerrar_mes_real(year, month, carpeta_salida: Path):
    ruta_archivo = carpeta_salida / nombre_archivo_mensual(year, month)
    validar_archivo_existe(ruta_archivo, "mensual")

    df = pd.read_excel(ruta_archivo, sheet_name="Calendario_Mensual", engine="openpyxl")
    df.columns = df.columns.str.strip()

    if "Persona" not in df.columns:
        raise ValueError("No existe la columna 'Persona' en Calendario_Mensual.")

    if "Tipo" not in df.columns:
        raise ValueError("No existe la columna 'Tipo' en Calendario_Mensual.")

    if "Saldo inicial" not in df.columns:
        raise ValueError("No existe la columna 'Saldo inicial' en Calendario_Mensual.")

    columnas_dias = obtener_columnas_dias(df)
    if not columnas_dias:
        raise ValueError("No se encontraron columnas tipo D1, D2, D3... en Calendario_Mensual.")

    df_reg = df[df["Tipo"].astype(str).str.strip().str.lower() == "regular"].copy()

    cierres = []

    for _, row in df_reg.iterrows():
        persona = str(row["Persona"]).strip()
        saldo_inicial = int(pd.to_numeric(row["Saldo inicial"], errors="coerce"))
        contador = saldo_inicial

        dias_con_actividad_reales = 0
        libres_generados_reales = 0
        a_mes = 0
        incap_mes = 0
        ssg_mes = 0
        h_mes = 0
        mc_mes = 0
        le_mes = 0
        lm_mes = 0
        lp_mes = 0
        pcg_mes = 0
        psg_mes = 0
        reinicios_a_0 = 0
        reinicios_a_6 = 0
        ultimo_estado = ""

        for col in columnas_dias:
            estado = limpiar_texto(row[col])
            if estado != "":
                ultimo_estado = estado

            if estado in ["M", "T", "N", "L", "LB"]:
                contador += 1
                dias_con_actividad_reales += 1

            elif estado in ["INCAP", "SSG", "H", "MC", "LE", "LM", "LP", "PCG", "PSG"]:
                if estado == "INCAP": incap_mes += 1
                elif estado == "SSG": ssg_mes += 1
                elif estado == "H": h_mes += 1
                elif estado == "MC": mc_mes += 1
                elif estado == "LE": le_mes += 1
                elif estado == "LM": lm_mes += 1
                elif estado == "LP": lp_mes += 1
                elif estado == "PCG": pcg_mes += 1
                elif estado == "PSG": psg_mes += 1

                if AJ_CUENTA_COMO_TRABAJO:
                    contador += 1
                    dias_con_actividad_reales += 1

            elif estado == "A":
                a_mes += 1
                if contador < 6:
                    contador = 0
                    reinicios_a_0 += 1
                else:
                    contador = 6
                    reinicios_a_6 += 1

            elif estado in ["V", "O", ""]:
                pass

            else:
                raise ValueError(
                    f"Estado no reconocido para {persona} en {col}: '{estado}'. "
                    f"Solo se permiten M, T, N, L, LB, V, O, A, INCAP, SSG, H, MC, LE, LM, LP, PCG, PSG."
                )

            if contador >= 12:
                nuevos = contador // 12
                libres_generados_reales += nuevos
                contador = contador % 12

        lb_inicial_sig = 1 if ultimo_estado == "N" else 0

        cierres.append({
            "Persona": persona,
            "Días con actividad reales": dias_con_actividad_reales,
            "A del mes": a_mes,
            "INCAP del mes": incap_mes,
            "SSG del mes": ssg_mes,
            "H del mes": h_mes,
            "MC del mes": mc_mes,
            "LE del mes": le_mes,
            "LM del mes": lm_mes,
            "LP del mes": lp_mes,
            "PCG del mes": pcg_mes,
            "PSG del mes": psg_mes,
            "Reinicios a 0": reinicios_a_0,
            "Reinicios a 6": reinicios_a_6,
            "Libres generados reales": libres_generados_reales,
            "Residuo final real": contador,
            "LB inicial siguiente mes": lb_inicial_sig,
            "Libres acumulados disponibles siguiente mes": libres_generados_reales
        })

    df_cierre_real = pd.DataFrame(cierres)

    df_arrastre_real = df_cierre_real[[
        "Persona",
        "Residuo final real",
        "LB inicial siguiente mes",
        "Libres acumulados disponibles siguiente mes"
    ]].rename(columns={
        "Residuo final real": "Saldo acumulado siguiente mes"
    })

    with pd.ExcelWriter(
        ruta_archivo,
        engine="openpyxl",
        mode="a",
        if_sheet_exists="replace"
    ) as writer:
        df_cierre_real.to_excel(writer, sheet_name="Cierre_Real_Mes", index=False)
        df_arrastre_real.to_excel(writer, sheet_name="Arrastre_Real_Siguiente_Mes", index=False)

    print(f"\nCierre real guardado en:\n{ruta_archivo}")
    print("Se actualizaron las hojas:")
    print("- Cierre_Real_Mes")
    print("- Arrastre_Real_Siguiente_Mes")

    return {
        "ruta_archivo": ruta_archivo,
        "df_cierre_real": df_cierre_real,
        "df_arrastre_real": df_arrastre_real,
    }




# =========================================================
# MODELO DE FUNCIONES - LÓGICA NUEVA INTEGRADA
# =========================================================
RUTA_HISTORIAL = None
CARPETA_SALIDA = None

# =========================================================
# 2. PARÁMETROS GLOBALES
# =========================================================
TURNOS = ["M", "T", "N"]

FUNCION_REEMPLAZA = "Reemplaza"
FUNCION_CRITICA_REEMPLAZA = "Esteriliza"

FUNCIONES_VARIABLES = {FUNCION_REEMPLAZA}

FUNCIONES = [
    "I_Piso",
    "II_Piso",
    "III_Piso",
    "IV_Piso",
    "Jeringas",
    "Esteriliza",
    "Recoger_1_2",
    "Recoger_3_4",
    "Equipos",
    "Coordina",
    "Especialidades",
    FUNCION_REEMPLAZA,
]

ALIAS_FUNCIONES = {
    "F1": "I_Piso",
    "F2": "II_Piso",
    "F3": "III_Piso",
    "F4": "IV_Piso",
    "F5": "Jeringas",
    "F6": "Esteriliza",
    "F7": "Recoger_1_2",
    "F8": "Recoger_3_4",
    "F9": "Equipos",
    "F10": "Coordina",
    "F11": "Especialidades",
    "F12": FUNCION_REEMPLAZA,
}

# Dotación diaria fija por turno y función.
# Reemplaza queda en 0 porque no tiene mínimo ni máximo general.
W_DEFECTO = {
    "M": {
        "I_Piso": 1,
        "II_Piso": 1,
        "III_Piso": 1,
        "IV_Piso": 1,
        "Jeringas": 1,
        "Esteriliza": 1,
        "Recoger_1_2": 1,
        "Recoger_3_4": 1,
        "Equipos": 1,
        "Coordina": 1,
        "Especialidades": 1,
        FUNCION_REEMPLAZA: 0,
    },
    "T": {
        "I_Piso": 0,
        "II_Piso": 1,
        "III_Piso": 1,
        "IV_Piso": 1,
        "Jeringas": 0,
        "Esteriliza": 1,
        "Recoger_1_2": 1,
        "Recoger_3_4": 1,
        "Equipos": 1,
        "Coordina": 1,
        "Especialidades": 0,
        FUNCION_REEMPLAZA: 0,
    },
    "N": {
        "I_Piso": 0,
        "II_Piso": 0,
        "III_Piso": 0,
        "IV_Piso": 0,
        "Jeringas": 0,
        "Esteriliza": 1,
        "Recoger_1_2": 1,
        "Recoger_3_4": 0,
        "Equipos": 1,
        "Coordina": 0,
        "Especialidades": 0,
        FUNCION_REEMPLAZA: 0,
    },
}

# Mínimo blando de reserva crítica:
# Se intenta dejar al menos una persona en Reemplaza que también pueda hacer Esteriliza.
MIN_REEMPLAZA_CRITICO = {
    "M": 1,
    "T": 1,
    "N": 1,
}

HORIZONTE_EQUIDAD = 10


# =========================================================
# 3. FUNCIONES AUXILIARES
# =========================================================
def nombre_seguro(valor):
    texto = str(valor)
    texto = re.sub(r"[^A-Za-z0-9_]+", "_", texto)
    texto = texto.strip("_")

    if texto == "":
        texto = "sin_nombre"

    return texto[:80]


def obtener_mapa_semana_por_dia(year, month):
    num_dias = calendar.monthrange(year, month)[1]

    return {
        d: date(year, month, d).isocalendar()[1]
        for d in range(1, num_dias + 1)
    }


def obtener_monday_iso(iso_year, iso_week):
    return datetime.datetime.fromisocalendar(int(iso_year), int(iso_week), 1)


def obtener_horizonte_ultimas_10_semanas(year, month):
    num_dias = calendar.monthrange(year, month)[1]
    semanas_actuales = []

    for d in range(1, num_dias + 1):
        fecha = date(year, month, d)
        iso_year, semana_iso, _ = fecha.isocalendar()
        lunes_iso = obtener_monday_iso(iso_year, semana_iso)

        if lunes_iso.year == year and lunes_iso.month == month:
            key = (iso_year, semana_iso)
            if key not in semanas_actuales:
                semanas_actuales.append(key)

    semanas_actuales = sorted(
        semanas_actuales,
        key=lambda k: obtener_monday_iso(k[0], k[1])
    )

    if not semanas_actuales:
        return [], [], []

    semanas_horizonte = list(semanas_actuales)

    primer_iso_year, primera_semana = semanas_actuales[0]
    fecha_cursor = obtener_monday_iso(primer_iso_year, primera_semana) - datetime.timedelta(weeks=1)

    while len(semanas_horizonte) < HORIZONTE_EQUIDAD:
        iso_year, semana_iso, _ = fecha_cursor.isocalendar()
        key = (iso_year, semana_iso)

        if key not in semanas_horizonte:
            semanas_horizonte.append(key)

        fecha_cursor -= datetime.timedelta(weeks=1)

    semanas_horizonte = sorted(
        semanas_horizonte,
        key=lambda k: obtener_monday_iso(k[0], k[1])
    )

    semanas_actuales_set = set(semanas_actuales)
    semanas_previas = [
        k for k in semanas_horizonte
        if k not in semanas_actuales_set
    ]

    return semanas_horizonte, semanas_actuales, semanas_previas


def persona_semana_pertenece_al_mes(p, s, dias_por_semana_reg, year, month):
    dias = dias_por_semana_reg.get((p, s), [])

    if not dias:
        return False

    dia_ejemplo = min(dias)
    fecha = date(year, month, dia_ejemplo)
    iso_year, semana_iso, _ = fecha.isocalendar()
    lunes_iso = obtener_monday_iso(iso_year, semana_iso)

    return lunes_iso.year == year and lunes_iso.month == month


def preparar_columnas_iso_historial(df):
    df = df.copy()

    if "ISO_Year" not in df.columns:
        df["ISO_Year"] = df["Año"] if "Año" in df.columns else None

    if "Mes" not in df.columns:
        df["Mes"] = None

    for col in ["SemanaISO", "ISO_Year", "Año", "Mes"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def filtrar_por_semanas_iso(df, semanas_iso):
    if df.empty or not semanas_iso:
        return df.iloc[0:0].copy()

    df = preparar_columnas_iso_historial(df)
    semanas_set = set((int(y), int(s)) for y, s in semanas_iso)

    mask = df.apply(
        lambda row: (
            pd.notna(row.get("ISO_Year"))
            and pd.notna(row.get("SemanaISO"))
            and (int(row["ISO_Year"]), int(row["SemanaISO"])) in semanas_set
        ),
        axis=1
    )

    return df[mask].copy()


def cargar_conjunto_A_pf(ruta_base):
    """
    Lee la matriz de compatibilidad persona-función desde BaseDatos.xlsx.
    Además, agrega Reemplaza para todas las personas encontradas en la base.
    """
    A_pf = set()
    personas = set()

    for hoja in ["Hoja1", "Hoja2", "Hoja3", "Asistentes", "Saldo"]:
        try:
            df = pd.read_excel(ruta_base, sheet_name=hoja, engine="openpyxl")
        except Exception:
            continue

        if df.empty:
            continue

        df.columns = df.columns.str.strip()
        col_persona = df.columns[0]

        for _, row in df.iterrows():
            persona = str(row[col_persona]).strip()

            if pd.isna(row[col_persona]) or persona == "" or persona == "nan":
                continue

            personas.add(persona)

            for f in FUNCIONES:
                columnas_posibles = [f]
                columnas_posibles += [
                    alias for alias, real in ALIAS_FUNCIONES.items()
                    if real == f
                ]

                for col_funcion in columnas_posibles:
                    if col_funcion not in df.columns or pd.isna(row[col_funcion]):
                        continue

                    valor = row[col_funcion]

                    try:
                        habilitada = int(float(valor)) == 1
                    except Exception:
                        habilitada = str(valor).strip().upper() in [
                            "1",
                            "SI",
                            "SÍ",
                            "S",
                            "X",
                            "TRUE",
                            "VERDADERO",
                        ]

                    if habilitada:
                        A_pf.add((persona, f))
                        break

    for persona in personas:
        A_pf.add((persona, FUNCION_REEMPLAZA))

    return A_pf


def cargar_asistentes_2(ruta_base):
    """Devuelve conjunto de personas con rol 2, buscando una hoja con Persona y Rol."""
    xls = pd.ExcelFile(ruta_base, engine="openpyxl")
    asistentes_2 = set()

    for hoja in ["Hoja1", "Asistentes", "Hoja3", *xls.sheet_names]:
        if hoja not in xls.sheet_names:
            continue

        df = pd.read_excel(ruta_base, sheet_name=hoja, engine="openpyxl", header=0)
        if df.empty:
            continue

        df.columns = df.columns.str.strip()
        col_persona = buscar_columna(df, ["Persona"], obligatoria=False)
        col_rol = buscar_columna(df, ["Rol"], obligatoria=False)

        if col_persona is None or col_rol is None:
            if len(df.columns) >= 2:
                col_persona = df.columns[0]
                col_rol = df.columns[1]
            else:
                continue

        for _, row in df.iterrows():
            persona = str(row[col_persona]).strip()

            if pd.isna(row[col_persona]) or persona == "" or persona == "nan":
                continue

            if row[col_rol] == 2 or str(row[col_rol]).strip() == "2":
                asistentes_2.add(persona)

        if asistentes_2:
            break

    return asistentes_2


def cargar_roles_personas(ruta_base):
    roles = {}

    for hoja in ["Hoja1", "Hoja2", "Hoja3", "Asistentes", "Saldo"]:
        try:
            df = pd.read_excel(ruta_base, sheet_name=hoja, engine="openpyxl", header=0)
        except Exception:
            continue

        if df.empty:
            continue

        df.columns = df.columns.str.strip()

        if len(df.columns) < 2:
            continue

        col_persona = df.columns[0]
        col_rol = df.columns[1]

        for _, row in df.iterrows():
            persona = str(row[col_persona]).strip()

            if pd.isna(row[col_persona]) or persona == "" or persona == "nan":
                continue

            try:
                roles[persona] = int(float(row[col_rol]))
            except Exception:
                roles[persona] = str(row[col_rol]).strip()

    return roles


def cargar_disponibilidad(year, month, ruta_mensual, num_dias):
    """
    Carga personas regulares desde Calendario_Mensual.
    Permite semanas ISO con turnos mixtos, por ejemplo N y M en la misma semana.
    """
    df = pd.read_excel(ruta_mensual, sheet_name="Calendario_Mensual", engine="openpyxl")
    df.columns = df.columns.str.strip()

    dias_cols = [
        c for c in df.columns
        if str(c).startswith("D")
        and str(c)[1:].isdigit()
        and int(str(c)[1:]) <= num_dias
    ]

    dias_cols.sort(key=lambda x: int(str(x)[1:]))

    mapa_semana = obtener_mapa_semana_por_dia(year, month)

    T_pst_reg = set()
    dias_por_semana_reg = defaultdict(list)
    turno_por_dia_reg = {}

    for _, row in df.iterrows():
        persona = str(row["Persona"]).strip()

        if pd.isna(row["Persona"]) or persona == "" or persona == "nan":
            continue

        tipo = str(row.get("Tipo", "Regular")).strip().lower()

        if tipo != "regular":
            continue

        for col in dias_cols:
            dia = int(str(col)[1:])
            valor = str(row[col]).strip().upper()
            turno = valor if valor in TURNOS else None

            if turno is None:
                continue

            semana = mapa_semana[dia]
            T_pst_reg.add((persona, semana))
            dias_por_semana_reg[(persona, semana)].append(dia)
            turno_por_dia_reg[(persona, dia)] = turno

    return T_pst_reg, dias_por_semana_reg, turno_por_dia_reg


def obtener_parametro_w_usuario():
    print("\n--- Dotación diaria requerida w_{tf} ---")
    print("Reemplaza no tiene mínimo ni máximo general; queda como función variable.")
    print("La reserva crítica de Esteriliza se controla aparte como condición blanda.")
    resp = input("¿Usar valores por defecto? (S/N): ").strip().upper()

    if resp in ["S", "SI", "SÍ", ""]:
        return W_DEFECTO

    w = {t: {f: 0 for f in FUNCIONES} for t in TURNOS}

    print("Ingrese (Turno Función Cantidad), vacío termina:")
    print("Ejemplo: M I_Piso 1")
    print("No ingrese Reemplaza; queda variable sin mínimo ni máximo general.")

    while True:
        linea = input("> ").strip()

        if not linea:
            break

        partes = linea.split()

        if len(partes) != 3:
            print("Formato incorrecto")
            continue

        t = partes[0].upper()
        f = partes[1]
        c = partes[2]

        if f in ALIAS_FUNCIONES:
            f = ALIAS_FUNCIONES[f]

        if t not in TURNOS or f not in FUNCIONES:
            print("Turno o función inválidos")
            continue

        if f in FUNCIONES_VARIABLES:
            print("Reemplaza es variable; no se le asigna dotación fija.")
            continue

        try:
            w[t][f] = int(c)
        except Exception:
            print("Cantidad debe ser entero")

    for t in TURNOS:
        w[t][FUNCION_REEMPLAZA] = 0

    return w


# =========================================================
# 4. HISTORIAL
# =========================================================
def leer_historial_detalle():
    columnas = ["Persona", "Funcion", "Año", "ISO_Year", "SemanaISO", "Mes"]

    if not os.path.exists(RUTA_HISTORIAL):
        return pd.DataFrame(columns=columnas)

    excel = pd.ExcelFile(RUTA_HISTORIAL, engine="openpyxl")

    if "Historial_Detalle" in excel.sheet_names:
        df = pd.read_excel(RUTA_HISTORIAL, sheet_name="Historial_Detalle", engine="openpyxl")
    else:
        df = pd.read_excel(RUTA_HISTORIAL, sheet_name=excel.sheet_names[0], engine="openpyxl")

    for col in columnas:
        if col not in df.columns:
            df[col] = None

    if "ISO_Year" not in df.columns or df["ISO_Year"].isna().all():
        df["ISO_Year"] = df["Año"]

    return df


def construir_resumen_equidad_historial(df_historial):
    columnas_resumen = [
        "Persona",
        *FUNCIONES,
        "Total_asignaciones",
        "Funciones_visitadas",
        "Cantidad_funciones_visitadas",
        "Funcion_mas_asignada",
        "Cantidad_maxima",
    ]

    if (
        df_historial.empty
        or "Persona" not in df_historial.columns
        or "Funcion" not in df_historial.columns
    ):
        return pd.DataFrame(columns=columnas_resumen)

    df = df_historial[
        df_historial["Persona"].notna()
        & df_historial["Funcion"].notna()
        & df_historial["Funcion"].isin(FUNCIONES)
    ].copy()

    if df.empty:
        return pd.DataFrame(columns=columnas_resumen)

    resumen = pd.crosstab(df["Persona"], df["Funcion"])

    for f in FUNCIONES:
        if f not in resumen.columns:
            resumen[f] = 0

    resumen = resumen[FUNCIONES].astype(int)
    resumen["Total_asignaciones"] = resumen[FUNCIONES].sum(axis=1)
    resumen["Cantidad_maxima"] = resumen[FUNCIONES].max(axis=1)

    resumen["Funciones_visitadas"] = resumen.apply(
        lambda fila: ", ".join([f for f in FUNCIONES if fila[f] > 0]),
        axis=1
    )

    resumen["Cantidad_funciones_visitadas"] = resumen[FUNCIONES].gt(0).sum(axis=1)

    def funcion_mas_asignada(fila):
        if fila["Total_asignaciones"] == 0:
            return ""

        maximo = fila[FUNCIONES].max()
        return ", ".join([f for f in FUNCIONES if fila[f] == maximo])

    resumen["Funcion_mas_asignada"] = resumen.apply(funcion_mas_asignada, axis=1)
    resumen = resumen.reset_index()

    return resumen[columnas_resumen]


def construir_validacion_historial_10_semanas(df_historial_10, personas_reg=None):
    columnas = [
        "Persona",
        "Total_asignaciones_en_ventana",
        "Semanas_con_registro",
        "Semanas_sin_registro",
        "Estado_validacion",
    ]

    if personas_reg is None:
        if df_historial_10.empty or "Persona" not in df_historial_10.columns:
            return pd.DataFrame(columns=columnas)

        personas_reg = sorted(df_historial_10["Persona"].dropna().unique())

    filas = []

    for p in sorted(personas_reg):
        df_p = df_historial_10[df_historial_10["Persona"] == p].copy()
        total_asig = len(df_p)

        if df_p.empty:
            semanas_con_registro = 0
        else:
            semanas_con_registro = df_p[["ISO_Year", "SemanaISO"]].drop_duplicates().shape[0]

        semanas_sin_registro = HORIZONTE_EQUIDAD - semanas_con_registro

        if semanas_con_registro == HORIZONTE_EQUIDAD:
            estado = "OK: tiene registro en las 10 semanas"
        elif semanas_con_registro == 0:
            estado = "REVISAR: no tiene registros en la ventana"
        else:
            estado = "OK si tuvo vacaciones/ausencias; revisar si debía trabajar"

        filas.append({
            "Persona": p,
            "Total_asignaciones_en_ventana": total_asig,
            "Semanas_con_registro": semanas_con_registro,
            "Semanas_sin_registro": semanas_sin_registro,
            "Estado_validacion": estado,
        })

    return pd.DataFrame(filas)


def guardar_archivo_historial_con_resumen(df_final, anio, mes):
    columnas = ["Persona", "Funcion", "Año", "ISO_Year", "SemanaISO", "Mes"]

    for col in columnas:
        if col not in df_final.columns:
            df_final[col] = None

    df_final = df_final[columnas].copy()
    df_final = preparar_columnas_iso_historial(df_final)

    df_final = df_final.drop_duplicates(
        subset=["Persona", "ISO_Year", "SemanaISO"],
        keep="last"
    )

    semanas_horizonte, semanas_actuales, semanas_previas = obtener_horizonte_ultimas_10_semanas(
        anio,
        mes
    )

    df_ultimas_10 = filtrar_por_semanas_iso(df_final, semanas_horizonte)

    df_ultimas_10 = df_ultimas_10.drop_duplicates(
        subset=["Persona", "ISO_Year", "SemanaISO"],
        keep="last"
    )

    resumen_ultimas_10 = construir_resumen_equidad_historial(df_ultimas_10)
    validacion_ultimas_10 = construir_validacion_historial_10_semanas(df_ultimas_10)
    resumen_total = construir_resumen_equidad_historial(df_final)

    info_horizonte = pd.DataFrame(
        [
            {
                "Tipo": "Semana histórica previa",
                "ISO_Year": y,
                "SemanaISO": s,
                "Lunes_ISO": obtener_monday_iso(y, s),
            }
            for y, s in semanas_previas
        ]
        + [
            {
                "Tipo": "Semana nueva del mes actual",
                "ISO_Year": y,
                "SemanaISO": s,
                "Lunes_ISO": obtener_monday_iso(y, s),
            }
            for y, s in semanas_actuales
        ]
    )

    os.makedirs(CARPETA_SALIDA, exist_ok=True)

    with pd.ExcelWriter(RUTA_HISTORIAL, engine="openpyxl") as writer:
        df_final.to_excel(writer, sheet_name="Historial_Detalle", index=False)
        resumen_ultimas_10.to_excel(writer, sheet_name="Resumen_Ultimas_10", index=False)
        validacion_ultimas_10.to_excel(writer, sheet_name="Validacion_Ultimas_10", index=False)
        resumen_total.to_excel(writer, sheet_name="Resumen_Historico_Total", index=False)
        info_horizonte.to_excel(writer, sheet_name="Info_Horizonte_10", index=False)


def cargar_historial(anio_actual, mes_actual):
    if not os.path.exists(RUTA_HISTORIAL):
        print("No existe historial previo. Se usará historial = 0.")
        return defaultdict(int)

    df = leer_historial_detalle()
    required = ["Persona", "Funcion", "Año", "SemanaISO"]

    if not all(c in df.columns for c in required):
        raise ValueError("El historial debe tener columnas: Persona, Funcion, Año, SemanaISO")

    df = preparar_columnas_iso_historial(df)

    df = df[
        ~(
            (df["Año"] == anio_actual)
            & (df["Mes"] == mes_actual)
        )
    ].copy()

    df = df.drop_duplicates(
        subset=["Persona", "ISO_Year", "SemanaISO"],
        keep="last"
    )

    semanas_horizonte, semanas_actuales, semanas_previas = obtener_horizonte_ultimas_10_semanas(
        anio_actual,
        mes_actual
    )

    df_filtrado = filtrar_por_semanas_iso(df, semanas_previas)

    historial = defaultdict(int)

    for _, row in df_filtrado.iterrows():
        p = row["Persona"]
        f = row["Funcion"]

        if f in FUNCIONES:
            historial[(p, f)] += 1

    print(
        "Horizonte rotación/equidad: "
        f"{len(semanas_previas)} semanas históricas + "
        f"{len(semanas_actuales)} semanas nuevas del mes actual = "
        f"{len(semanas_horizonte)} semanas ISO"
    )

    return historial


def guardar_asignaciones_historial(asignaciones_reg, anio, mes, dias_por_semana_reg):
    registros = []

    for (p, s), f in asignaciones_reg.items():
        dias = dias_por_semana_reg.get((p, s), [])

        if not dias:
            continue

        dia_ejemplo = min(dias)
        fecha = datetime.datetime(anio, mes, dia_ejemplo)
        iso_year = fecha.isocalendar()[0]
        semana_iso = fecha.isocalendar()[1]
        lunes_iso = obtener_monday_iso(iso_year, semana_iso)

        if lunes_iso.year != anio or lunes_iso.month != mes:
            continue

        registros.append({
            "Persona": p,
            "Funcion": f,
            "Año": anio,
            "ISO_Year": iso_year,
            "SemanaISO": semana_iso,
            "Mes": mes,
        })

    columnas = ["Persona", "Funcion", "Año", "ISO_Year", "SemanaISO", "Mes"]

    if os.path.exists(RUTA_HISTORIAL):
        df_hist = leer_historial_detalle()
        df_hist = preparar_columnas_iso_historial(df_hist)

        df_hist = df_hist[
            ~(
                (df_hist["Año"] == anio)
                & (df_hist["Mes"] == mes)
            )
        ].copy()
    else:
        df_hist = pd.DataFrame(columns=columnas)

    if registros:
        df_final = pd.concat([df_hist, pd.DataFrame(registros)], ignore_index=True)
    else:
        df_final = df_hist.copy()

    for col in columnas:
        if col not in df_final.columns:
            df_final[col] = None

    df_final = df_final.drop_duplicates(
        subset=["Persona", "ISO_Year", "SemanaISO"],
        keep="last"
    )

    guardar_archivo_historial_con_resumen(df_final, anio, mes)

    print(f"Historial actualizado en: {RUTA_HISTORIAL}")
    print(f"Registros nuevos del mes: {len(registros)}")

    if len(registros) == 0:
        print("Advertencia: no se guardaron asignaciones nuevas.")


# =========================================================
# 5. MODELO DE OPTIMIZACIÓN
# =========================================================
def resolver_modelo(
    year,
    month,
    T_pst_reg,
    dias_por_semana_reg,
    turno_por_dia_reg,
    A_pf,
    w,
    asistentes_2,
    roles,
):
    num_dias = calendar.monthrange(year, month)[1]
    semanas_iso = obtener_mapa_semana_por_dia(year, month)

    personas_reg = sorted(set(p for (p, _) in T_pst_reg))
    semanas = sorted(set(sem for (_, sem) in T_pst_reg))
    dias = range(1, num_dias + 1)

    for p in personas_reg:
        A_pf.add((p, FUNCION_REEMPLAZA))

    prob = pulp.LpProblem("Asignacion_Funciones_Rotacion_Visitadas", pulp.LpMinimize)

    # -----------------------------------------------------
    # Variables de asignación persona-semana-función
    # -----------------------------------------------------
    x = {}

    for (p, s) in T_pst_reg:
        turnos_semana = sorted({
            turno_por_dia_reg.get((p, d))
            for d in dias_por_semana_reg.get((p, s), [])
        })

        turnos_semana = [t for t in turnos_semana if t in TURNOS]

        for f in FUNCIONES:
            if (p, f) not in A_pf:
                continue

            es_variable = f in FUNCIONES_VARIABLES
            requerida_en_algun_turno = any(w[t].get(f, 0) > 0 for t in turnos_semana)

            if es_variable or requerida_en_algun_turno:
                x[(p, s, f)] = pulp.LpVariable(
                    f"x_{nombre_seguro(p)}_{s}_{nombre_seguro(f)}",
                    cat="Binary"
                )

    # -----------------------------------------------------
    # Variables de faltante para cobertura fija
    # No se exportan a Excel, solo se usan internamente.
    # -----------------------------------------------------
    shortage = {}

    for t in TURNOS:
        for f in FUNCIONES:
            if f in FUNCIONES_VARIABLES:
                continue

            if w[t].get(f, 0) > 0:
                for d in dias:
                    shortage[(t, f, d)] = pulp.LpVariable(
                        f"shortage_{t}_{nombre_seguro(f)}_{d}",
                        lowBound=0,
                        cat="Integer"
                    )

    # -----------------------------------------------------
    # Variables de faltante para reserva crítica de Esteriliza
    # No se exportan a Excel, solo se usan internamente.
    # -----------------------------------------------------
    shortage_reserva = {}

    for t in TURNOS:
        minimo = MIN_REEMPLAZA_CRITICO.get(t, 0)

        if minimo > 0 and w[t].get(FUNCION_CRITICA_REEMPLAZA, 0) > 0:
            for d in dias:
                shortage_reserva[(t, d)] = pulp.LpVariable(
                    f"shortage_reserva_{t}_D{d}",
                    lowBound=0,
                    cat="Integer"
                )

    historial = cargar_historial(year, month)

    N_pf = {}
    U_pf = {}

    for p in personas_reg:
        for f in FUNCIONES:
            if (p, f) in A_pf:
                N_pf[(p, f)] = pulp.LpVariable(
                    f"N_{nombre_seguro(p)}_{nombre_seguro(f)}",
                    lowBound=0,
                    cat="Integer"
                )

                U_pf[(p, f)] = pulp.LpVariable(
                    f"U_{nombre_seguro(p)}_{nombre_seguro(f)}",
                    cat="Binary"
                )

    # -----------------------------------------------------
    # Cobertura diaria para funciones con dotación fija
    # -----------------------------------------------------
    for d in dias:
        sem_actual = semanas_iso[d]

        for t in TURNOS:
            for f in FUNCIONES:
                if f in FUNCIONES_VARIABLES:
                    continue

                demanda = w[t].get(f, 0)

                if demanda == 0:
                    continue

                aporte_reg = pulp.lpSum(
                    x[(p, sem_actual, f)]
                    for (p, s) in T_pst_reg
                    if s == sem_actual
                    and turno_por_dia_reg.get((p, d)) == t
                    and d in dias_por_semana_reg.get((p, sem_actual), [])
                    and (p, sem_actual, f) in x
                )

                prob += (
                    aporte_reg + shortage[(t, f, d)] >= demanda
                ), f"Cobertura_{t}_{nombre_seguro(f)}_D{d}"

                prob += (
                    aporte_reg <= demanda
                ), f"No_sobrecubrir_{t}_{nombre_seguro(f)}_D{d}"

    # -----------------------------------------------------
    # Reserva crítica:
    # Debe procurarse al menos una persona en Reemplaza capaz de cubrir Esteriliza.
    # -----------------------------------------------------
    for d in dias:
        sem_actual = semanas_iso[d]

        for t in TURNOS:
            minimo = MIN_REEMPLAZA_CRITICO.get(t, 0)

            if minimo <= 0:
                continue

            if w[t].get(FUNCION_CRITICA_REEMPLAZA, 0) <= 0:
                continue

            if (t, d) not in shortage_reserva:
                continue

            reemplazos_capaces_esteriliza = pulp.lpSum(
                x[(p, sem_actual, FUNCION_REEMPLAZA)]
                for (p, s) in T_pst_reg
                if s == sem_actual
                and turno_por_dia_reg.get((p, d)) == t
                and d in dias_por_semana_reg.get((p, sem_actual), [])
                and (p, FUNCION_CRITICA_REEMPLAZA) in A_pf
                and (p, sem_actual, FUNCION_REEMPLAZA) in x
            )

            prob += (
                reemplazos_capaces_esteriliza + shortage_reserva[(t, d)] >= minimo
            ), f"Reserva_Esteriliza_{t}_D{d}"

    # -----------------------------------------------------
    # Cada persona-semana disponible recibe exactamente una función.
    # Si no cubre una función fija, puede quedar en Reemplaza.
    # -----------------------------------------------------
    for (p, s) in T_pst_reg:
        prob += (
            pulp.lpSum(x.get((p, s, f), 0) for f in FUNCIONES) == 1
        ), f"Una_funcion_semana_{nombre_seguro(p)}_{s}"

    # -----------------------------------------------------
    # No repetir función en semanas consecutivas, excepto asistentes tipo 2.
    # -----------------------------------------------------
    semanas_por_persona = defaultdict(list)

    for (p, s) in T_pst_reg:
        semanas_por_persona[p].append(s)

    for p, lista_s in semanas_por_persona.items():
        if p in asistentes_2:
            continue

        lista_s = sorted(set(lista_s))

        for idx in range(len(lista_s) - 1):
            s_act = lista_s[idx]
            s_sig = lista_s[idx + 1]

            if s_sig - s_act != 1:
                continue

            for f in FUNCIONES:
                if (p, s_act, f) in x and (p, s_sig, f) in x:
                    prob += (
                        x[(p, s_act, f)] + x[(p, s_sig, f)] <= 1
                    ), f"NoRepetir_{nombre_seguro(p)}_{s_act}_{s_sig}_{nombre_seguro(f)}"

    # -----------------------------------------------------
    # Definición de N_pf
    # -----------------------------------------------------
    for p in personas_reg:
        for f in FUNCIONES:
            if (p, f) not in A_pf:
                continue

            hist_val = historial.get((p, f), 0)

            suma_x = pulp.lpSum(
                x.get((p, s, f), 0)
                for s in semanas
                if persona_semana_pertenece_al_mes(
                    p,
                    s,
                    dias_por_semana_reg,
                    year,
                    month
                )
            )

            prob += (
                N_pf[(p, f)] == hist_val + suma_x
            ), f"Def_N_{nombre_seguro(p)}_{nombre_seguro(f)}"

    # -----------------------------------------------------
    # Definición de U_pf
    # -----------------------------------------------------
    for (p, f), var_u in U_pf.items():
        prob += (
            var_u <= N_pf[(p, f)]
        ), f"U_menor_N_{nombre_seguro(p)}_{nombre_seguro(f)}"

        prob += (
            N_pf[(p, f)] <= HORIZONTE_EQUIDAD * var_u
        ), f"N_menor_MU_{nombre_seguro(p)}_{nombre_seguro(f)}"

    total_faltantes = pulp.lpSum(shortage.values()) if shortage else pulp.LpAffineExpression()
    total_reserva = pulp.lpSum(shortage_reserva.values()) if shortage_reserva else pulp.LpAffineExpression()
    total_no_visitadas = pulp.lpSum(1 - U_pf[(p, f)] for (p, f) in U_pf) if U_pf else pulp.LpAffineExpression()

    # -----------------------------------------------------
    # Etapa 1: minimizar faltantes de cobertura fija
    # -----------------------------------------------------
    print("Resolviendo modelo - etapa 1: minimizar faltantes de cobertura fija...")
    prob += total_faltantes, "Etapa_1_Min_Faltantes_Cobertura"
    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    estado1 = pulp.LpStatus[prob.status]
    print(f"Estado etapa 1: {estado1}")

    if estado1 not in ["Optimal", "Feasible"]:
        raise RuntimeError("No se encontró una solución factible en etapa 1.")

    best_faltantes = pulp.value(total_faltantes) or 0
    print(f"Faltantes mínimos de cobertura fija: {best_faltantes}")

    prob += (
        total_faltantes <= best_faltantes + 1e-6
    ), "Fijar_faltantes_cobertura_minimos"

    # -----------------------------------------------------
    # Etapa 2: minimizar faltantes de reserva crítica
    # -----------------------------------------------------
    print("Resolviendo modelo - etapa 2: minimizar faltantes de reserva crítica para Esteriliza...")
    prob.setObjective(total_reserva)
    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    estado2 = pulp.LpStatus[prob.status]
    print(f"Estado etapa 2: {estado2}")

    if estado2 not in ["Optimal", "Feasible"]:
        raise RuntimeError("No se encontró una solución factible en etapa 2.")

    best_reserva = pulp.value(total_reserva) or 0
    print(f"Faltantes mínimos de reserva crítica: {best_reserva}")

    prob += (
        total_reserva <= best_reserva + 1e-6
    ), "Fijar_faltantes_reserva_minimos"

    # -----------------------------------------------------
    # Etapa 3: maximizar funciones visitadas
    # -----------------------------------------------------
    print("Resolviendo modelo - etapa 3: maximizar funciones visitadas...")
    prob.setObjective(total_no_visitadas)
    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    estado3 = pulp.LpStatus[prob.status]
    print(f"Estado etapa 3: {estado3}")

    if estado3 not in ["Optimal", "Feasible"]:
        raise RuntimeError("No se encontró una solución factible en etapa 3.")

    print(f"Funciones permitidas no visitadas: {pulp.value(total_no_visitadas)}")

    asign_reg = {
        (p, s): f
        for (p, s, f), var in x.items()
        if pulp.value(var) is not None and pulp.value(var) > 0.5
    }

    faltantes_cobertura_total = sum(
        int(round(pulp.value(var)))
        for var in shortage.values()
        if pulp.value(var) is not None and pulp.value(var) > 0
    )

    faltantes_reserva_total = sum(
        int(round(pulp.value(var)))
        for var in shortage_reserva.values()
        if pulp.value(var) is not None and pulp.value(var) > 0
    )

    sin_asignar = []

    for (p, s) in T_pst_reg:
        if (p, s) not in asign_reg:
            dias_trab = dias_por_semana_reg.get((p, s), [])

            if dias_trab:
                dia_repr = min(dias_trab)
                turno_repr = turno_por_dia_reg.get((p, dia_repr), "")

                sin_asignar.append((p, dia_repr, turno_repr, "regular"))

    resumen_rotacion = []

    for p in sorted(personas_reg):
        fila = {"Persona": p, "Rol": roles.get(p, "")}
        total_visitadas = 0
        total_elegibles = 0

        for f in FUNCIONES:
            if (p, f) in A_pf:
                total_elegibles += 1

                n_val = pulp.value(N_pf[(p, f)])
                u_val = pulp.value(U_pf[(p, f)])

                n_int = int(round(n_val)) if n_val is not None else 0
                u_int = int(round(u_val)) if u_val is not None else 0

                fila[f] = n_int

                if u_int == 1:
                    total_visitadas += 1
            else:
                fila[f] = ""

        fila["Funciones_elegibles"] = total_elegibles
        fila["Funciones_visitadas"] = total_visitadas
        fila["Funciones_no_visitadas"] = total_elegibles - total_visitadas
        fila["Porcentaje_visitadas"] = (
            round(total_visitadas / total_elegibles, 4)
            if total_elegibles > 0
            else ""
        )

        resumen_rotacion.append(fila)

    df_resumen_rotacion = pd.DataFrame(resumen_rotacion)

    return (
        asign_reg,
        sin_asignar,
        dias_por_semana_reg,
        turno_por_dia_reg,
        df_resumen_rotacion,
        faltantes_cobertura_total,
        faltantes_reserva_total,
    )


# =========================================================
# 6. SALIDAS
# =========================================================
def construir_tablas(asign_reg, dias_por_semana_reg, turno_por_dia_reg, w, num_dias):
    cobertura = defaultdict(list)

    for (p, s), f in asign_reg.items():
        for d in dias_por_semana_reg.get((p, s), []):
            if d > num_dias:
                continue

            t = turno_por_dia_reg.get((p, d))

            if t not in TURNOS:
                continue

            if f in FUNCIONES_VARIABLES or w[t].get(f, 0) > 0:
                cobertura[(d, f, t)].append(p)

    tablas = {}

    for t in TURNOS:
        df = pd.DataFrame(
            index=FUNCIONES,
            columns=[f"D{d}" for d in range(1, num_dias + 1)]
        )
    
        df.fillna("", inplace=True)

        for d in range(1, num_dias + 1):
            for f in FUNCIONES:
                nombres = cobertura.get((d, f, t), [])
                texto_nombres = ", ".join(nombres)

                if f in FUNCIONES_VARIABLES:
                    df.loc[f, f"D{d}"] = texto_nombres
                elif w[t].get(f, 0) > 0:
                    df.loc[f, f"D{d}"] = texto_nombres if texto_nombres else "LIBRE"
                else:
                    df.loc[f, f"D{d}"] = ""

        tablas[t] = df

    return tablas


def carpeta_funciones(year: int) -> Path:
    ruta = carpeta_year(year) / "Resultados_Funciones"
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def ruta_historial_funciones(year: int) -> Path:
    return carpeta_year(year) / "historial_asignaciones.xlsx"


def ruta_salida_funciones(year: int, month: int) -> Path:
    return carpeta_funciones(year) / f"asignacion_funciones_{year}_{month:02d}.xlsx"


def ejecutar_modelo_funciones(year: int, month: int, w=None, min_reemplaza_critico=None):
    """Ejecuta el modelo nuevo de funciones usando la base y el mensual ya guardados por la interfaz."""
    global RUTA_HISTORIAL, CARPETA_SALIDA, MIN_REEMPLAZA_CRITICO

    ruta_base_excel = ruta_base(year)
    ruta_mensual_excel = ruta_mensual(year, month)

    validar_archivo_existe(ruta_base_excel, "base")
    validar_archivo_existe(ruta_mensual_excel, "mensual")

    CARPETA_SALIDA = carpeta_funciones(year)
    RUTA_HISTORIAL = ruta_historial_funciones(year)

    if w is None:
        w = W_DEFECTO

    if min_reemplaza_critico is not None:
        MIN_REEMPLAZA_CRITICO = {t: int(min_reemplaza_critico.get(t, MIN_REEMPLAZA_CRITICO.get(t, 0))) for t in TURNOS}

    num_dias = calendar.monthrange(year, month)[1]

    asistentes_2 = cargar_asistentes_2(ruta_base_excel)
    roles = cargar_roles_personas(ruta_base_excel)

    T_pst_reg, dias_por_semana_reg, turno_por_dia_reg = cargar_disponibilidad(
        year,
        month,
        ruta_mensual_excel,
        num_dias,
    )

    if not T_pst_reg:
        raise RuntimeError("No hay personas regulares con turnos M/T/N en este mes.")

    A_pf = cargar_conjunto_A_pf(ruta_base_excel)

    (
        asign_reg,
        sin_asignar,
        dias_por_semana_reg_out,
        turno_por_dia_reg_out,
        df_resumen_rotacion,
        faltantes_cobertura_total,
        faltantes_reserva_total,
    ) = resolver_modelo(
        year,
        month,
        T_pst_reg,
        dias_por_semana_reg,
        turno_por_dia_reg,
        A_pf,
        w,
        asistentes_2,
        roles,
    )

    guardar_asignaciones_historial(
        asign_reg,
        year,
        month,
        dias_por_semana_reg_out,
    )

    tablas = construir_tablas(
        asign_reg,
        dias_por_semana_reg_out,
        turno_por_dia_reg_out,
        w,
        num_dias,
    )

    df_sin = pd.DataFrame(
        sin_asignar,
        columns=["Persona", "Día", "Turno", "Tipo"],
    )

    salida = ruta_salida_funciones(year, month)

    with pd.ExcelWriter(salida, engine="openpyxl") as writer:
        for turno, df in tablas.items():
            df.to_excel(writer, sheet_name=turno)

        df_sin.to_excel(writer, sheet_name="Personas_sin_asignar", index=False)
        df_resumen_rotacion.to_excel(writer, sheet_name="Rotacion_Modelo_Usada", index=False)

    return {
        "ruta_salida": salida,
        "ruta_historial": ruta_historial_funciones(year),
        "tablas": tablas,
        "df_sin": df_sin,
        "df_resumen_rotacion": df_resumen_rotacion,
        "faltantes_cobertura_total": int(faltantes_cobertura_total),
        "faltantes_reserva_total": int(faltantes_reserva_total),
        "personas_sin_asignar": len(sin_asignar),
        "asignaciones_regulares": len(asign_reg),
        "asistentes_2": len(asistentes_2),
        "roles": len(roles),
        "pares_elegibles": len(A_pf),
        "min_reemplaza_critico": MIN_REEMPLAZA_CRITICO,
    }

# =========================================================
# UTILIDADES DE VISUALIZACIÓN
# =========================================================
def style_horario(val):
    if pd.isna(val):
        return ""

    val = str(val).strip().upper()

    colores = {
        # Turnos principales obligatorios
        "M":     ("#66CFFF", "#083344"),  # mañana / diurno - celeste
        "T":     ("#3DCC6C", "#083344"),  # tarde - verde
        "N":     ("#B91C1C", "#FFFFFF"),  # noche - rojo

        # Estados generales
        "V":     ("#9B59B6", "#FFFFFF"),  # vacaciones
        "L":     ("#F5B041", "#083344"),  # libre
        "LB":    ("#2E4053", "#FFFFFF"),  # libre biológico
        "O":     ("#ECF0F1", "#4B5563"),  # otro / no asignado

        # Nuevas divisiones de ausencias / permisos
        "INCAP": ("#155E75", "#FFFFFF"),  # incapacidad
        "SSG":   ("#566573", "#FFFFFF"),
        "H":     ("#8B4513", "#FFFFFF"),
        "MC":    ("#BA4A00", "#FFFFFF"),
        "LE":    ("#BE185D", "#FFFFFF"),
        "LM":    ("#5DADE2", "#083344"),
        "LP":    ("#F4D03F", "#083344"),
        "PCG":   ("#1ABC9C", "#083344"),
        "PSG":   ("#117A65", "#FFFFFF"),
        "A":     ("#C0392B", "#FFFFFF"),
    }

    if val in colores:
        fondo, texto = colores[val]
        return (
            f"background-color: {fondo}; "
            f"color: {texto}; "
            f"font-weight: bold; "
            f"text-align: center"
        )

    return ""

def fijar_persona_como_indice(df):
    """
    Muestra Persona como índice para que quede fija al desplazarse horizontalmente
    en las tablas de Streamlit. No modifica el DataFrame original.
    """
    if isinstance(df, pd.DataFrame) and "Persona" in df.columns:
        df_vista = df.copy()
        df_vista["Persona"] = df_vista["Persona"].astype(str)
        df_vista = df_vista.set_index("Persona", drop=True)
        df_vista.index.name = "Persona"
        return df_vista
    return df


def mostrar_dataframe_persona_fija(df, height=None):
    df_vista = fijar_persona_como_indice(df)
    kwargs = {"use_container_width": True}
    if height is not None:
        kwargs["height"] = height
    st.dataframe(df_vista, **kwargs)


def mostrar_dataframe_estilado(df, height=500):
    df_vista = fijar_persona_como_indice(df)
    columnas_horario = [
        c for c in df_vista.columns
        if str(c).startswith("S") or str(c).startswith("D")
    ]

    try:
        st.dataframe(
            df_vista.style.map(style_horario, subset=columnas_horario),
            height=height,
            use_container_width=True
        )
    except Exception:
        st.dataframe(
            df_vista.style.applymap(style_horario, subset=columnas_horario),
            height=height,
            use_container_width=True
        )


def obtener_meses_semana_anual(year: int, semana: int) -> list[int]:
    """Devuelve los meses que tienen días dentro de una semana ISO del año."""
    meses_semana = []

    for mes in range(1, 13):
        for dia in range(1, calendar.monthrange(year, mes)[1] + 1):
            if date(year, mes, dia).isocalendar()[1] == int(semana):
                if mes not in meses_semana:
                    meses_semana.append(mes)

    return meses_semana or [1]


def obtener_mes_semana_anual(year: int, semana: int) -> int:
    """Devuelve el mes al que pertenece principalmente una semana ISO dentro del año."""
    conteo_meses = defaultdict(int)

    for mes in range(1, 13):
        for dia in range(1, calendar.monthrange(year, mes)[1] + 1):
            if date(year, mes, dia).isocalendar()[1] == int(semana):
                conteo_meses[mes] += 1

    if conteo_meses:
        return max(conteo_meses, key=lambda m: (conteo_meses[m], -m))

    return 1


def obtener_nombre_mes_semana_anual(year: int, semana: int, abreviado: bool = False) -> str:
    meses = obtener_meses_semana_anual(year, semana)
    nombres = [NOMBRES_MESES_DASHBOARD[mes - 1] for mes in meses]

    if abreviado:
        nombres = [nombre[:3] for nombre in nombres]

    return "/".join(nombres)


def mostrar_calendario_anual_con_meses(df, year: int, height=500):
    """Muestra el calendario anual con una fila superior de mes sobre las semanas."""
    df_vista = fijar_persona_como_indice(df)

    columnas_multi = []
    columnas_horario = []

    for col in df_vista.columns:
        semana = extraer_numero_semana_columna(col)

        if semana is not None:
            col_multi = (obtener_nombre_mes_semana_anual(year, semana), str(col))
            columnas_horario.append(col_multi)
        else:
            col_multi = ("", str(col))

        columnas_multi.append(col_multi)

    df_vista = df_vista.copy()
    df_vista.columns = pd.MultiIndex.from_tuples(columnas_multi)

    try:
        st.dataframe(
            df_vista.style.map(style_horario, subset=columnas_horario),
            height=height,
            use_container_width=True
        )
    except Exception:
        try:
            st.dataframe(
                df_vista.style.applymap(style_horario, subset=columnas_horario),
                height=height,
                use_container_width=True
            )
        except Exception:
            st.dataframe(df_vista, height=height, use_container_width=True)

# =========================================================
# UTILIDADES DEL DASHBOARD
# =========================================================
NOMBRES_MESES_DASHBOARD = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Setiembre", "Octubre", "Noviembre", "Diciembre"
]

COLORES_ESTADOS_DASHBOARD = {
    "M": "#66CFFF",
    "T": "#3DCC6C",
    "N": "#B91C1C",
    "V": "#9B59B6",
    "L": "#F5B041",
    "LB": "#2E4053",
    "A": "#C0392B",
    "INCAP": "#155E75",
    "SSG": "#566573",
    "H": "#8B4513",
    "MC": "#BA4A00",
    "LE": "#BE185D",
    "LM": "#5DADE2",
    "LP": "#F4D03F",
    "PCG": "#1ABC9C",
    "PSG": "#117A65",
}

ESTADOS_TURNOS = ["M", "T", "N"]
ESTADOS_LIBRES = ["L", "LB"]
ESTADOS_AUSENCIAS = ["A", "INCAP", "SSG", "H", "MC", "LE", "LM", "LP", "PCG", "PSG"]
ESTADOS_VACACIONES = ["V"]

NOMBRES_ESTADOS = {
    "M": "Mañana",
    "T": "Tarde",
    "N": "Noche",
    "L": "Libre",
    "LB": "Libre biológico",
    "V": "Vacaciones",
    "A": "Ausencia",
    "INCAP": "Incapacidad",
    "SSG": "Suspensión sin goce",
    "H": "Huelga",
    "MC": "Medida cautelar",
    "LE": "Licencia extraordinaria",
    "LM": "Licencia maternidad",
    "LP": "Licencia paternidad",
    "PCG": "Permiso con goce salarial",
    "PSG": "Permiso sin goce salarial",
}


def render_kpi(titulo, valor, nota=""):
    st.markdown(
        f"""
        <div class="dashboard-card">
            <div class="dashboard-card-title">{titulo}</div>
            <div class="dashboard-card-value">{valor}</div>
            <div class="dashboard-card-note">{nota}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_section_title(titulo, subtitulo=""):
    st.markdown(
        f"""
        <div class="dashboard-section">
            <h3>{titulo}</h3>
            <p style="color:#5b7280; margin-bottom:0;">{subtitulo}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def extraer_mes_desde_nombre(nombre_archivo, patron):
    match = re.search(patron, str(nombre_archivo))
    if not match:
        return None
    try:
        return int(match.group(1))
    except Exception:
        return None


def normalizar_clave_dashboard(valor):
    """Normaliza nombres de hojas/columnas para lectura flexible."""
    texto = str(valor).strip().lower()
    reemplazos = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u", "ñ": "n",
        "Á": "a", "É": "e", "Í": "i", "Ó": "o", "Ú": "u", "Ü": "u", "Ñ": "n",
    }
    for origen, destino in reemplazos.items():
        texto = texto.replace(origen, destino)
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    return " ".join(texto.split())


def resolver_hoja_excel_dashboard(xls, candidatos):
    """Devuelve el nombre real de una hoja aunque venga con espacios, guiones o variantes."""
    hojas = list(xls.sheet_names)
    mapa = {normalizar_clave_dashboard(h): h for h in hojas}

    for cand in candidatos:
        clave = normalizar_clave_dashboard(cand)
        if clave in mapa:
            return mapa[clave]

    for cand in candidatos:
        clave = normalizar_clave_dashboard(cand)
        tokens = clave.split()
        if not tokens:
            continue
        for hoja in hojas:
            hoja_norm = normalizar_clave_dashboard(hoja)
            if all(token in hoja_norm for token in tokens):
                return hoja
    return None


def buscar_columna_flexible_dashboard(df, candidatos):
    """Devuelve la columna real de un DataFrame usando coincidencia flexible."""
    columnas = list(df.columns)
    mapa = {normalizar_clave_dashboard(c): c for c in columnas}

    for cand in candidatos:
        clave = normalizar_clave_dashboard(cand)
        if clave in mapa:
            return mapa[clave]

    for cand in candidatos:
        clave = normalizar_clave_dashboard(cand)
        tokens = clave.split()
        if not tokens:
            continue
        for col in columnas:
            col_norm = normalizar_clave_dashboard(col)
            if all(token in col_norm for token in tokens):
                return col
    return None


def buscar_archivos_mensuales_dashboard(year: int, mes: int):
    """
    Devuelve únicamente el archivo mensual oficial guardado en data_turnos_app/año.

    Esto evita que el dashboard tome copias, archivos de funciones u otros respaldos
    que pueden tener calendario, pero no necesariamente la hoja Cierre_Real_Mes.
    """
    ruta = ruta_mensual(year, int(mes))
    if ruta.exists() and not ruta.name.startswith("~$"):
        return [ruta]
    return []


def meses_disponibles_dashboard(year: int):
    """Lista meses con archivo mensual oficial dentro de data_turnos_app/año."""
    meses_encontrados = []
    for mes in range(1, 13):
        ruta = ruta_mensual(year, mes)
        if ruta.exists() and not ruta.name.startswith("~$"):
            meses_encontrados.append(mes)
    return meses_encontrados


def cargar_calendarios_dashboard(year: int, meses_analisis: list):
    """
    Carga calendario mensual, resumen diario de libres y cierre real únicamente
    desde el archivo mensual oficial:

        data_turnos_app/año/mensual_YYYY_MM.xlsx

    El cierre real se busca como hoja dentro de ese mismo archivo mensual. Esto
    vuelve al comportamiento esperado del sistema y evita que el dashboard lea
    copias o archivos alternos que no tienen Cierre_Real_Mes.
    """
    registros = []
    cierres = []
    libres_diarios = []
    rutas_leidas = []
    errores = []
    rutas_registradas = set()

    def registrar_ruta(ruta):
        try:
            clave = str(Path(ruta).resolve()).lower()
        except Exception:
            clave = str(ruta).lower()
        if clave not in rutas_registradas:
            rutas_registradas.add(clave)
            rutas_leidas.append(str(ruta))

    for mes in meses_analisis:
        mes = int(mes)
        ruta = ruta_mensual(year, mes)

        if not ruta.exists():
            errores.append(
                f"Mes {mes:02d}: no existe el archivo mensual oficial en data_turnos_app: {ruta.name}"
            )
            continue

        try:
            xls = pd.ExcelFile(ruta, engine="openpyxl")
            hojas = list(xls.sheet_names)
            hojas_norm = {normalizar_clave_dashboard(h): h for h in hojas}
            errores.append(
                f"Mes {mes:02d}: archivo mensual oficial revisado: {ruta.name}. Hojas encontradas: {', '.join(map(str, hojas))}"
            )

            # Se priorizan los nombres exactos que genera el propio sistema.
            hoja_calendario = "Calendario_Mensual" if "Calendario_Mensual" in hojas else resolver_hoja_excel_dashboard(
                xls,
                ["Calendario_Mensual", "Calendario Mensual", "Calendario", "Programacion Mensual", "Programación Mensual"],
            )
            hoja_libres = "Resumen_Diario_Libres" if "Resumen_Diario_Libres" in hojas else resolver_hoja_excel_dashboard(
                xls,
                ["Resumen_Diario_Libres", "Resumen Diario Libres", "Libres diarios", "Resumen Libres"],
            )
            hoja_cierre = "Cierre_Real_Mes" if "Cierre_Real_Mes" in hojas else resolver_hoja_excel_dashboard(
                xls,
                [
                    "Cierre_Real_Mes",
                    "Cierre Real Mes",
                    "Cierre_Real",
                    "Cierre Real",
                    "Cierre Mes",
                    "Cierre",
                    "Resumen Cierre Real",
                    "Cierre Mensual Real",
                ],
            )

            if hoja_calendario:
                try:
                    df_cal = pd.read_excel(ruta, sheet_name=hoja_calendario, engine="openpyxl")
                    df_cal.columns = [str(c).strip() for c in df_cal.columns]
                    columnas_dias = obtener_columnas_dias(df_cal)

                    col_persona = buscar_columna_flexible_dashboard(df_cal, ["Persona", "Nombre", "Funcionario"]) or "Persona"
                    col_tipo = buscar_columna_flexible_dashboard(df_cal, ["Tipo", "Tipo persona", "Categoria", "Categoría"])

                    if col_persona in df_cal.columns and columnas_dias:
                        for _, row in df_cal.iterrows():
                            persona = str(row.get(col_persona, "")).strip()
                            tipo = str(row.get(col_tipo, "Regular")).strip() if col_tipo else "Regular"
                            if persona == "" or persona.lower() == "nan":
                                continue

                            for col in columnas_dias:
                                dia_txt = str(col).strip()
                                try:
                                    dia = int(re.sub(r"\D", "", dia_txt))
                                except Exception:
                                    continue
                                estado = limpiar_texto(row.get(col, ""))
                                if estado == "":
                                    continue
                                registros.append({
                                    "Año": year,
                                    "Mes": mes,
                                    "Mes nombre": NOMBRES_MESES_DASHBOARD[mes - 1],
                                    "Persona": persona,
                                    "Tipo": tipo,
                                    "Día": dia,
                                    "Estado": estado,
                                    "Estado nombre": NOMBRES_ESTADOS.get(estado, estado),
                                    "Archivo origen": str(ruta.name),
                                    "Hoja origen": str(hoja_calendario),
                                })
                        registrar_ruta(ruta)
                    else:
                        errores.append(
                            f"Mes {mes:02d}: la hoja {hoja_calendario} existe, pero no se reconocieron Persona y columnas de días."
                        )
                except Exception as e:
                    errores.append(f"Mes {mes:02d}: error leyendo Calendario_Mensual en {ruta.name}: {e}")
            else:
                errores.append(f"Mes {mes:02d}: no se encontró hoja Calendario_Mensual en {ruta.name}.")

            if hoja_libres:
                try:
                    df_libres = pd.read_excel(ruta, sheet_name=hoja_libres, engine="openpyxl")
                    df_libres.columns = [str(c).strip() for c in df_libres.columns]
                    if not df_libres.empty:
                        df_libres["Mes"] = mes
                        df_libres["Mes nombre"] = NOMBRES_MESES_DASHBOARD[mes - 1]
                        df_libres["Archivo origen"] = str(ruta.name)
                        df_libres["Hoja origen"] = str(hoja_libres)
                        libres_diarios.append(df_libres)
                        registrar_ruta(ruta)
                except Exception as e:
                    errores.append(f"Mes {mes:02d}: error leyendo Resumen_Diario_Libres en {ruta.name}: {e}")

            if hoja_cierre:
                try:
                    df_cierre = pd.read_excel(ruta, sheet_name=hoja_cierre, engine="openpyxl")
                    df_cierre.columns = [str(c).strip() for c in df_cierre.columns]
                    if not df_cierre.empty:
                        df_cierre["Mes"] = mes
                        df_cierre["Mes nombre"] = NOMBRES_MESES_DASHBOARD[mes - 1]
                        df_cierre["Archivo origen"] = str(ruta.name)
                        df_cierre["Hoja origen"] = str(hoja_cierre)
                        cierres.append(df_cierre)
                        registrar_ruta(ruta)
                        errores.append(
                            f"Mes {mes:02d}: Cierre_Real_Mes leído correctamente desde {ruta.name} ({len(df_cierre)} filas)."
                        )
                    else:
                        errores.append(
                            f"Mes {mes:02d}: la hoja {hoja_cierre} existe en {ruta.name}, pero está vacía."
                        )
                except Exception as e:
                    errores.append(f"Mes {mes:02d}: error leyendo Cierre_Real_Mes en {ruta.name}: {e}")
            else:
                # Mensaje diagnóstico explícito para confirmar si el mes realmente fue cerrado.
                esperado_norm = normalizar_clave_dashboard("Cierre_Real_Mes")
                coincidencias = [h for h_norm, h in hojas_norm.items() if "cierre" in h_norm]
                if coincidencias:
                    errores.append(
                        f"Mes {mes:02d}: se encontraron hojas relacionadas con cierre ({', '.join(coincidencias)}), "
                        f"pero no coinciden con Cierre_Real_Mes."
                    )
                else:
                    errores.append(
                        f"Mes {mes:02d}: el archivo mensual oficial {ruta.name} no tiene hoja Cierre_Real_Mes. "
                        "Esto indica que ese mes todavía no fue cerrado en ese archivo, o que el cierre se guardó en otra copia."
                    )

        except Exception as e:
            errores.append(f"Mes {mes:02d}: no se pudo abrir el archivo mensual oficial {ruta.name}: {e}")

    df_estados = pd.DataFrame(registros)
    df_cierres = pd.concat(cierres, ignore_index=True) if cierres else pd.DataFrame()
    df_libres_diarios = pd.concat(libres_diarios, ignore_index=True) if libres_diarios else pd.DataFrame()

    return df_estados, df_cierres, df_libres_diarios, rutas_leidas, errores


def construir_diagnostico_archivos_mensuales_dashboard(year: int, meses_analisis: list):
    """Resumen claro de los archivos mensuales revisados por el dashboard."""
    filas = []

    for mes in meses_analisis:
        mes = int(mes)
        ruta = ruta_mensual(year, mes)
        fila = {
            "Mes": f"{mes:02d} - {NOMBRES_MESES_DASHBOARD[mes - 1]}",
            "Archivo revisado": ruta.name,
            "Ruta": str(ruta),
            "Existe": "Sí" if ruta.exists() else "No",
            "Calendario mensual": "No",
            "Resumen de libres": "No",
            "Cierre real": "No",
            "Hoja de cierre": "No aplica",
            "Filas cierre": 0,
            "Estado": "Archivo no encontrado",
        }

        if not ruta.exists():
            filas.append(fila)
            continue

        try:
            xls = pd.ExcelFile(ruta, engine="openpyxl")
            hojas = list(xls.sheet_names)

            hoja_calendario = "Calendario_Mensual" if "Calendario_Mensual" in hojas else resolver_hoja_excel_dashboard(
                xls,
                ["Calendario_Mensual", "Calendario Mensual", "Calendario", "Programacion Mensual", "Programación Mensual"],
            )
            hoja_libres = "Resumen_Diario_Libres" if "Resumen_Diario_Libres" in hojas else resolver_hoja_excel_dashboard(
                xls,
                ["Resumen_Diario_Libres", "Resumen Diario Libres", "Libres diarios", "Resumen Libres"],
            )
            hoja_cierre = "Cierre_Real_Mes" if "Cierre_Real_Mes" in hojas else resolver_hoja_excel_dashboard(
                xls,
                [
                    "Cierre_Real_Mes",
                    "Cierre Real Mes",
                    "Cierre_Real",
                    "Cierre Real",
                    "Cierre Mes",
                    "Cierre",
                    "Resumen Cierre Real",
                    "Cierre Mensual Real",
                ],
            )

            fila["Calendario mensual"] = "Sí" if hoja_calendario else "No"
            fila["Resumen de libres"] = "Sí" if hoja_libres else "No"

            if hoja_cierre:
                fila["Hoja de cierre"] = str(hoja_cierre)
                try:
                    df_cierre_diag = pd.read_excel(ruta, sheet_name=hoja_cierre, engine="openpyxl")
                    filas_cierre = int(len(df_cierre_diag))
                    fila["Filas cierre"] = filas_cierre
                    fila["Cierre real"] = "Sí" if filas_cierre > 0 else "Hoja vacía"
                    fila["Estado"] = "Mes cerrado" if filas_cierre > 0 else "Hoja de cierre vacía"
                except Exception as e:
                    fila["Cierre real"] = "Error"
                    fila["Estado"] = f"Error al leer cierre: {e}"
            else:
                fila["Cierre real"] = "No"
                fila["Estado"] = "Mes sin cierre real"

        except Exception as e:
            fila["Estado"] = f"Error al abrir archivo: {e}"

        filas.append(fila)

    return pd.DataFrame(filas)


def obtener_semanas_anuales_por_meses(year: int, meses_analisis: list):
    """
    Devuelve las semanas ISO que aparecen dentro de los meses seleccionados.
    Se usa para evaluar la igualdad de turnos desde el calendario anual,
    sin que los libres mensuales modifiquen el indicador.
    """
    semanas = set()

    for mes in meses_analisis:
        try:
            mes = int(mes)
            num_dias = calendar.monthrange(year, mes)[1]
        except Exception:
            continue

        for dia in range(1, num_dias + 1):
            try:
                semana_iso = date(year, mes, dia).isocalendar()[1]
                semanas.add(int(semana_iso))
            except Exception:
                continue

    return sorted(semanas)


def normalizar_turno_anual_dashboard(valor):
    """
    Normaliza los valores del calendario anual a M, T o N.

    Esto evita que el dashboard quede en 0 cuando el archivo anual trae
    los turnos escritos como Mañana, Manana, Tarde o Noche, en vez de solo M, T, N.
    """
    if pd.isna(valor):
        return None

    texto = str(valor).strip().upper()
    texto = (
        texto.replace("Á", "A")
        .replace("É", "E")
        .replace("Í", "I")
        .replace("Ó", "O")
        .replace("Ú", "U")
        .replace("Ñ", "N")
    )
    texto = texto.replace("_", " ").replace("-", " ")
    texto = " ".join(texto.split())

    if texto in ["M", "MANANA", "MAÑANA", "TURNO M", "TURNO MANANA", "TURNO MAÑANA", "PRIMER TURNO", "1"]:
        return "M"
    if texto in ["T", "TARDE", "TURNO T", "TURNO TARDE", "SEGUNDO TURNO", "2"]:
        return "T"
    if texto in ["N", "NOCHE", "TURNO N", "TURNO NOCHE", "TERCER TURNO", "3"]:
        return "N"

    return None


def extraer_numero_semana_columna(columna):
    """Devuelve el número de semana si la columna representa S1, Semana 1, semana_01, etc."""
    texto = str(columna).strip().upper()
    texto = (
        texto.replace("Á", "A")
        .replace("É", "E")
        .replace("Í", "I")
        .replace("Ó", "O")
        .replace("Ú", "U")
    )
    texto = texto.replace("_", " ").replace("-", " ")
    texto = " ".join(texto.split())

    # Casos: S1, S01, S 1
    m = re.match(r"^S\s*0*(\d+)$", texto)
    if m:
        return int(m.group(1))

    # Casos: SEMANA 1, SEMANA01
    m = re.match(r"^SEMANA\s*0*(\d+)$", texto)
    if m:
        return int(m.group(1))

    # Casos donde Excel pudo traer el encabezado como número 1, 2, 3...
    try:
        if str(columna).strip().isdigit():
            n = int(str(columna).strip())
            if 1 <= n <= 54:
                return n
    except Exception:
        pass

    return None


def cargar_turnos_anual_dashboard(year: int, meses_analisis: list):
    """
    Carga M, T y N desde TODO el calendario anual para medir equidad de turnos.

    Este cálculo NO se filtra por mes. La igualdad de turnos se mide sobre la
    planificación anual completa, porque ahí se define cuántas semanas de
    mañana, tarde y noche recibe cada persona. El mensual agrega L y LB, por lo
    que no debe usarse para medir igualdad anual de turnos.
    """
    registros = []
    errores = []
    rutas_leidas = []
    semanas_analisis = []

    ruta = ruta_anual(year)
    if not ruta.exists():
        return pd.DataFrame(), [], semanas_analisis, [f"No existe el calendario anual: {ruta}"]

    try:
        xls_anual = pd.ExcelFile(ruta, engine="openpyxl")

        # Buscar la hoja correcta. Preferimos Calendario, pero si no existe,
        # usamos la primera hoja que tenga Persona y columnas de semana.
        hoja_usada = None
        hojas_candidatas = ["Calendario", "calendario", *xls_anual.sheet_names]
        for hoja in hojas_candidatas:
            if hoja not in xls_anual.sheet_names:
                continue
            df_prueba = pd.read_excel(ruta, sheet_name=hoja, engine="openpyxl", nrows=5)
            df_prueba.columns = [str(c).strip() for c in df_prueba.columns]
            tiene_persona = any(str(c).strip().lower() == "persona" for c in df_prueba.columns)
            tiene_semana = any(extraer_numero_semana_columna(c) is not None for c in df_prueba.columns)
            if tiene_persona and tiene_semana:
                hoja_usada = hoja
                break

        if hoja_usada is None:
            raise ValueError(
                "No se encontró una hoja anual con columna Persona y columnas de semana tipo S1, S2..."
            )

        df_anual = pd.read_excel(ruta, sheet_name=hoja_usada, engine="openpyxl")
        df_anual.columns = [str(c).strip() for c in df_anual.columns]
        rutas_leidas.append(f"{ruta} | hoja: {hoja_usada}")

        col_persona = buscar_columna(df_anual, ["Persona"], obligatoria=False)
        if col_persona is None:
            raise ValueError("El calendario anual no tiene la columna Persona.")

        col_rol = buscar_columna(df_anual, ["Rol"], obligatoria=False)
        col_genero = buscar_columna(df_anual, ["Género", "Genero"], obligatoria=False)

        columnas_semana = []
        for col in df_anual.columns:
            semana = extraer_numero_semana_columna(col)
            if semana is not None:
                columnas_semana.append((int(semana), col))

        columnas_semana = sorted(columnas_semana, key=lambda x: x[0])
        semanas_analisis = [semana for semana, _ in columnas_semana]

        if not columnas_semana:
            errores.append("No se encontraron columnas de semana tipo S1, S2... en el calendario anual.")

        valores_no_reconocidos = defaultdict(int)

        for _, row in df_anual.iterrows():
            persona = str(row.get(col_persona, "")).strip()
            if persona == "" or persona.lower() == "nan":
                continue

            rol = row.get(col_rol, "") if col_rol is not None else ""
            genero = row.get(col_genero, "") if col_genero is not None else ""

            for semana, col in columnas_semana:
                valor_original = row.get(col, "")
                turno = normalizar_turno_anual_dashboard(valor_original)

                if turno is None:
                    texto = "" if pd.isna(valor_original) else str(valor_original).strip()
                    if texto not in ["", "nan", "NaN"]:
                        valores_no_reconocidos[texto] += 1
                    continue

                registros.append({
                    "Año": year,
                    "SemanaISO": int(semana),
                    "Persona": persona,
                    "Rol": rol,
                    "Género": genero,
                    "Turno": turno,
                    "Turno nombre": NOMBRES_ESTADOS.get(turno, turno),
                    "Fuente": "Calendario anual completo",
                })

        if not registros:
            errores.append(
                "Se leyó el calendario anual, pero no se encontraron valores M, T o N. "
                "Revise si los turnos están escritos de otra forma."
            )

        if valores_no_reconocidos:
            ejemplos = list(valores_no_reconocidos.items())[:8]
            errores.append(
                "Valores del anual ignorados para equidad de turnos: "
                + ", ".join([f"'{k}' ({v})" for k, v in ejemplos])
            )

    except Exception as e:
        errores.append(f"{ruta.name}: {e}")

    return pd.DataFrame(registros), rutas_leidas, semanas_analisis, errores

def contar_turnos_anuales_por_persona(df_turnos_anual):
    """Cuenta M, T y N por persona usando el anual."""
    if df_turnos_anual is None or df_turnos_anual.empty:
        return pd.DataFrame()

    tabla = pd.crosstab(df_turnos_anual["Persona"], df_turnos_anual["Turno"])
    for turno in ESTADOS_TURNOS:
        if turno not in tabla.columns:
            tabla[turno] = 0

    tabla = tabla.reset_index()
    tabla["Mañanas"] = tabla["M"]
    tabla["Tardes"] = tabla["T"]
    tabla["Noches"] = tabla["N"]
    tabla["Total turnos anuales"] = tabla[["M", "T", "N"]].sum(axis=1)

    return tabla[["Persona", "Mañanas", "Tardes", "Noches", "Total turnos anuales"]].sort_values(
        by="Total turnos anuales", ascending=False
    )



def normalizar_turno_funciones_dashboard(valor):
    """Normaliza nombres de hoja o valores de turno a M, T o N."""
    if pd.isna(valor):
        return None
    texto = str(valor).strip().upper()
    texto = (
        texto.replace("Á", "A")
        .replace("É", "E")
        .replace("Í", "I")
        .replace("Ó", "O")
        .replace("Ú", "U")
        .replace("Ñ", "N")
    )
    texto = texto.replace("_", " ").replace("-", " ")
    texto = " ".join(texto.split())

    if texto in ["M", "MANANA", "TURNO M", "TURNO MANANA", "MAÑANA"]:
        return "M"
    if texto in ["T", "TARDE", "TURNO T", "TURNO TARDE"]:
        return "T"
    if texto in ["N", "NOCHE", "TURNO N", "TURNO NOCHE"]:
        return "N"
    return None


def es_pseudo_persona_funciones(valor):
    """
    Identifica registros técnicos que no son personas reales en los archivos de funciones.

    En las salidas de funciones puede aparecer la palabra LIBRE cuando la persona
    asignada originalmente está libre y la función debe ser cubierta por otra persona.
    Ese registro no debe entrar como persona en los indicadores de rotación ni de carga.
    """
    if pd.isna(valor):
        return True
    texto = normalizar_texto(valor)
    texto = texto.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    texto = " ".join(texto.replace("-", " ").replace("_", " ").split())
    return texto in {
        "",
        "libre",
        "l",
        "lb",
        "libre biologico",
        "vacio",
        "nan",
        "none",
        "no aplica",
        "na",
        "n/a",
        "sin asignar",
        "sin persona",
    }


def separar_personas_celda_funciones(valor):
    """Separa una celda de funciones en personas, aceptando coma, punto y coma o salto de línea."""
    if pd.isna(valor):
        return []
    texto = str(valor).strip()
    if texto == "":
        return []

    if es_pseudo_persona_funciones(texto):
        return []

    for sep in ["\n", ";", "|"]:
        texto = texto.replace(sep, ",")
    partes = [p.strip() for p in texto.split(",") if p.strip()]
    return [p for p in partes if not es_pseudo_persona_funciones(p)]


def clave_ruta_dashboard(ruta):
    """Clave normalizada para evitar que un mismo archivo aparezca repetido."""
    try:
        ruta_abs = Path(ruta).resolve()
    except Exception:
        ruta_abs = Path(ruta)
    return os.path.normcase(os.path.abspath(str(ruta_abs)))


def buscar_archivos_funciones_dashboard(year: int, mes: int):
    """
    Busca archivos de resultados de funciones para un mes.

    Se prioriza el archivo oficial del modelo:
    asignacion_funciones_YYYY_MM.xlsx.

    Las búsquedas recursivas quedan solo como respaldo. Además, se eliminan
    duplicados para no leer dos veces el mismo archivo ni duplicar los indicadores.
    """
    carpeta = carpeta_year(year)
    candidatos = []

    rutas_directas = [
        ruta_salida_funciones(year, mes),
        carpeta_funciones(year) / f"asignacion_funciones_{year}_{mes}.xlsx",
        carpeta_funciones(year) / f"funciones_{year}_{mes:02d}.xlsx",
        carpeta_funciones(year) / f"funciones_{year}_{mes}.xlsx",
        carpeta / f"asignacion_funciones_{year}_{mes:02d}.xlsx",
        carpeta / f"asignacion_funciones_{year}_{mes}.xlsx",
    ]

    for ruta in rutas_directas:
        if ruta.exists():
            candidatos.append(ruta)

    # Búsqueda recursiva: respaldo para archivos guardados en subcarpetas distintas.
    mes_txt = f"{int(mes):02d}"
    for ruta in carpeta.rglob("*.xlsx"):
        nombre_norm = normalizar_texto(ruta.name)
        if "funcion" not in nombre_norm:
            continue
        if str(year) not in ruta.name:
            continue

        mes_detectado = extraer_mes_desde_nombre(ruta.name, rf"{year}[_\-\s]?(\d{{1,2}})\.xlsx")
        if mes_detectado is None:
            m = re.search(rf"{year}\D+(\d{{1,2}})", ruta.stem)
            if m:
                try:
                    mes_detectado = int(m.group(1))
                except Exception:
                    mes_detectado = None

        if mes_detectado == int(mes):
            candidatos.append(ruta)
        elif mes_txt in ruta.stem and f"{year}" in ruta.stem:
            candidatos.append(ruta)

    # Quitar duplicados conservando el orden y normalizando mayúsculas/minúsculas.
    unicos = []
    vistos = set()
    for ruta in candidatos:
        clave = clave_ruta_dashboard(ruta)
        if clave not in vistos:
            vistos.add(clave)
            unicos.append(ruta)

    return unicos


def hoja_turno_funciones_dashboard(xls, turno):
    """Devuelve la hoja asociada a M, T o N aunque venga con nombre largo."""
    for hoja in xls.sheet_names:
        if normalizar_turno_funciones_dashboard(hoja) == turno:
            return hoja
    return None

def cargar_funciones_dashboard(year: int, meses_analisis: list):
    """
    Carga las asignaciones de funciones para el dashboard.

    Importante:
    - El archivo de funciones puede venir con hojas M/T/N o con nombres Mañana/Tarde/Noche.
    - Para el indicador gerencial NO se cuenta persona-día-función.
    - Se cuenta una vez por persona, semana ISO, mes y función.
    """
    registros = []
    sin_asignar = []
    rotacion = []
    rutas_leidas = []
    rutas_procesadas = set()
    errores = []

    for mes in meses_analisis:
        rutas_mes = buscar_archivos_funciones_dashboard(year, int(mes))
        if not rutas_mes:
            continue

        for ruta in rutas_mes:
            clave_archivo = clave_ruta_dashboard(ruta)
            if clave_archivo in rutas_procesadas:
                continue
            rutas_procesadas.add(clave_archivo)

            registros_antes_archivo = len(registros)
            sin_antes_archivo = len(sin_asignar)
            rotacion_antes_archivo = len(rotacion)

            try:
                xls = pd.ExcelFile(ruta, engine="openpyxl")
                ruta_txt = str(ruta)
                if ruta_txt not in rutas_leidas:
                    rutas_leidas.append(ruta_txt)

                hojas_turno_encontradas = []
                for turno in TURNOS:
                    hoja_turno = hoja_turno_funciones_dashboard(xls, turno)
                    if hoja_turno is None:
                        continue
                    hojas_turno_encontradas.append(hoja_turno)

                    df_turno = pd.read_excel(ruta, sheet_name=hoja_turno, engine="openpyxl", index_col=0)
                    df_turno.index = [str(i).strip() for i in df_turno.index]

                    for funcion, fila in df_turno.iterrows():
                        funcion = str(funcion).strip()
                        if funcion == "" or funcion.lower() == "nan":
                            continue

                        for col, valor in fila.items():
                            col_txt = str(col).strip()
                            if not col_txt.startswith("D") or not col_txt[1:].isdigit():
                                continue

                            dia = int(col_txt[1:])
                            personas = separar_personas_celda_funciones(valor)
                            if not personas:
                                continue

                            try:
                                semana_iso = date(year, int(mes), dia).isocalendar()[1]
                                iso_year = date(year, int(mes), dia).isocalendar()[0]
                            except Exception:
                                semana_iso = None
                                iso_year = year

                            for persona in personas:
                                registros.append({
                                    "Año": year,
                                    "ISO_Year": iso_year,
                                    "Mes": int(mes),
                                    "Mes nombre": NOMBRES_MESES_DASHBOARD[int(mes) - 1],
                                    "SemanaISO": semana_iso,
                                    "Turno": turno,
                                    "Día ejemplo": dia,
                                    "Persona": persona,
                                    "Funcion": funcion,
                                    "Unidad de conteo": "persona-semana-función",
                                    "Archivo": ruta.name,
                                })

                # Lectura complementaria de hojas auxiliares.
                hoja_sin = next((h for h in xls.sheet_names if normalizar_texto(h) == normalizar_texto("Personas_sin_asignar")), None)
                if hoja_sin is not None:
                    df_sin = pd.read_excel(ruta, sheet_name=hoja_sin, engine="openpyxl")
                    df_sin.columns = [str(c).strip() for c in df_sin.columns]
                    col_persona_sin = buscar_columna(df_sin, ["Persona", "Nombre", "Funcionario"], obligatoria=False)
                    if col_persona_sin is not None:
                        df_sin = df_sin[~df_sin[col_persona_sin].apply(es_pseudo_persona_funciones)].copy()
                    df_sin["Mes"] = int(mes)
                    df_sin["Mes nombre"] = NOMBRES_MESES_DASHBOARD[int(mes) - 1]
                    df_sin["Archivo"] = ruta.name
                    sin_asignar.append(df_sin)

                hoja_rot = next((h for h in xls.sheet_names if normalizar_texto(h) == normalizar_texto("Rotacion_Modelo_Usada")), None)
                if hoja_rot is not None:
                    df_rot = pd.read_excel(ruta, sheet_name=hoja_rot, engine="openpyxl")
                    df_rot.columns = [str(c).strip() for c in df_rot.columns]
                    col_persona_rot = buscar_columna(df_rot, ["Persona", "Nombre", "Funcionario"], obligatoria=False)
                    if col_persona_rot is not None:
                        df_rot = df_rot[~df_rot[col_persona_rot].apply(es_pseudo_persona_funciones)].copy()
                    df_rot["Mes"] = int(mes)
                    df_rot["Mes nombre"] = NOMBRES_MESES_DASHBOARD[int(mes) - 1]
                    df_rot["Archivo"] = ruta.name
                    rotacion.append(df_rot)

                if not hojas_turno_encontradas:
                    errores.append(
                        f"{ruta.name}: se encontró el archivo, pero no se encontraron hojas de turno M, T o N. "
                        f"Hojas disponibles: {', '.join(xls.sheet_names)}"
                    )
                elif len(registros) == registros_antes_archivo:
                    errores.append(
                        f"{ruta.name}: se encontraron hojas {', '.join(hojas_turno_encontradas)}, "
                        "pero no se detectaron nombres de personas en columnas D1, D2, etc."
                    )

                # Para un mismo mes se usa el primer archivo válido. Esto evita duplicar
                # los indicadores si existe el archivo oficial y además aparece como
                # resultado de la búsqueda recursiva.
                archivo_con_datos = (
                    len(registros) > registros_antes_archivo
                    or len(sin_asignar) > sin_antes_archivo
                    or len(rotacion) > rotacion_antes_archivo
                )
                if archivo_con_datos:
                    break

            except Exception as e:
                errores.append(f"{ruta.name}: {e}")

    df_funciones = pd.DataFrame(registros)

    if not df_funciones.empty:
        df_funciones = df_funciones[~df_funciones["Persona"].apply(es_pseudo_persona_funciones)].copy()

    if not df_funciones.empty:
        # Evita inflar el total de funciones por repetir la misma asignación en todos los días de la semana.
        columnas_unicas = ["Año", "ISO_Year", "Mes", "SemanaISO", "Persona", "Funcion"]
        for col in columnas_unicas:
            if col not in df_funciones.columns:
                df_funciones[col] = None
        df_funciones = (
            df_funciones
            .sort_values(by=["Mes", "SemanaISO", "Persona", "Día ejemplo"], na_position="last")
            .drop_duplicates(subset=columnas_unicas, keep="first")
            .reset_index(drop=True)
        )

    df_sin = pd.concat(sin_asignar, ignore_index=True) if sin_asignar else pd.DataFrame()
    if not df_sin.empty:
        col_persona_sin = buscar_columna(df_sin, ["Persona", "Nombre", "Funcionario"], obligatoria=False)
        if col_persona_sin is not None:
            df_sin = df_sin[~df_sin[col_persona_sin].apply(es_pseudo_persona_funciones)].copy()

    df_rotacion = pd.concat(rotacion, ignore_index=True) if rotacion else pd.DataFrame()
    if not df_rotacion.empty:
        col_persona_rot = buscar_columna(df_rotacion, ["Persona", "Nombre", "Funcionario"], obligatoria=False)
        if col_persona_rot is not None:
            df_rotacion = df_rotacion[~df_rotacion[col_persona_rot].apply(es_pseudo_persona_funciones)].copy()

    return df_funciones, df_sin, df_rotacion, rutas_leidas, errores

def contar_estados_por_persona(df_estados):
    if df_estados.empty:
        return pd.DataFrame()

    df = df_estados.copy()
    tabla = pd.crosstab(df["Persona"], df["Estado"])

    for estado in [*ESTADOS_TURNOS, *ESTADOS_LIBRES, *ESTADOS_VACACIONES, *ESTADOS_AUSENCIAS]:
        if estado not in tabla.columns:
            tabla[estado] = 0

    tabla = tabla.reset_index()
    tabla["Días trabajados"] = tabla[ESTADOS_TURNOS].sum(axis=1)
    tabla["Mañanas"] = tabla["M"]
    tabla["Tardes"] = tabla["T"]
    tabla["Noches"] = tabla["N"]
    tabla["Libres"] = tabla["L"]
    tabla["Libres biológicos"] = tabla["LB"]
    tabla["Vacaciones"] = tabla["V"]
    tabla["Ausencias"] = tabla[ESTADOS_AUSENCIAS].sum(axis=1)
    tabla["Total registros"] = tabla[[*ESTADOS_TURNOS, *ESTADOS_LIBRES, *ESTADOS_VACACIONES, *ESTADOS_AUSENCIAS]].sum(axis=1)

    columnas = [
        "Persona", "Días trabajados", "Mañanas", "Tardes", "Noches",
        "Libres", "Libres biológicos", "Vacaciones", "Ausencias", "Total registros"
    ]
    return tabla[columnas].sort_values(by="Días trabajados", ascending=False)






def construir_cobertura_y_libres_mensual_dashboard(df_estados, df_libres_diarios=None):
    """
    Construye los indicadores mensuales que corresponden al modelo mensual:
    dotación diaria por turno (M, T, N) y distribución diaria de libres (L + LB).

    La equidad de turnos NO se calcula aquí, porque esa se evalúa con el anual.
    No se usa un objetivo fijo de libres; se analiza la distribución observada.
    """
    columnas_cobertura = [
        "Mes", "Mes nombre", "Día", "Etiqueta día",
        "M", "T", "N", "Total M/T/N", "Libres", "L", "LB",
    ]

    if df_estados is None or df_estados.empty:
        return pd.DataFrame(columns=columnas_cobertura), pd.DataFrame()

    df = df_estados.copy()
    if "Tipo" in df.columns:
        df = df[df["Tipo"].astype(str).str.strip().str.lower().eq("regular")].copy()

    if df.empty:
        return pd.DataFrame(columns=columnas_cobertura), pd.DataFrame()

    base = (
        df[df["Estado"].isin([*ESTADOS_TURNOS, *ESTADOS_LIBRES])]
        .groupby(["Mes", "Mes nombre", "Día", "Estado"])
        .size()
        .reset_index(name="Cantidad")
    )

    if base.empty:
        return pd.DataFrame(columns=columnas_cobertura), pd.DataFrame()

    tabla = base.pivot_table(
        index=["Mes", "Mes nombre", "Día"],
        columns="Estado",
        values="Cantidad",
        aggfunc="sum",
        fill_value=0,
    ).reset_index()

    for col in ["M", "T", "N", "L", "LB"]:
        if col not in tabla.columns:
            tabla[col] = 0
        tabla[col] = pd.to_numeric(tabla[col], errors="coerce").fillna(0).astype(int)

    tabla["Total M/T/N"] = tabla[["M", "T", "N"]].sum(axis=1).astype(int)
    tabla["Libres"] = tabla[["L", "LB"]].sum(axis=1).astype(int)
    tabla["Etiqueta día"] = tabla.apply(
        lambda r: f"{int(r['Mes']):02d}-{int(r['Día']):02d}", axis=1
    )

    tabla = tabla.sort_values(by=["Mes", "Día"])
    tabla = tabla[columnas_cobertura]

    resumen_mes = (
        tabla.groupby(["Mes", "Mes nombre"])
        .agg(
            **{
                "Promedio M diario": ("M", "mean"),
                "Mínimo M": ("M", "min"),
                "Máximo M": ("M", "max"),
                "Promedio T diario": ("T", "mean"),
                "Mínimo T": ("T", "min"),
                "Máximo T": ("T", "max"),
                "Promedio N diario": ("N", "mean"),
                "Mínimo N": ("N", "min"),
                "Máximo N": ("N", "max"),
                "Promedio libres diario": ("Libres", "mean"),
                "Máximo libres": ("Libres", "max"),
                "Mínimo libres": ("Libres", "min"),
                "Brecha libres": ("Libres", lambda s: int(s.max() - s.min()) if len(s) else 0),
            }
        )
        .reset_index()
    )

    for col in ["Promedio M diario", "Promedio T diario", "Promedio N diario", "Promedio libres diario"]:
        if col in resumen_mes.columns:
            resumen_mes[col] = pd.to_numeric(resumen_mes[col], errors="coerce").fillna(0).round(2)

    return tabla, resumen_mes


def construir_indicadores_consistencia_mensual_dashboard(df_cobertura):
    """
    Construye indicadores de consistencia mensual para M, T, N y libres.

    La consistencia no mide equidad entre personas. Mide qué tan estable se
    mantiene la dotación diaria respecto al promedio de los días evaluados.
    Sirve para revisar la lógica del modelo mensual: dotación por turno y
    distribución diaria de libres.
    """
    columnas_resumen = [
        "Indicador", "Promedio diario", "Desviación promedio", "Consistencia (%)",
        "Mínimo", "Máximo", "Brecha", "Días evaluados"
    ]
    columnas_mes = ["Mes", "Mes nombre", *columnas_resumen]

    if df_cobertura is None or df_cobertura.empty:
        return (
            pd.DataFrame(columns=columnas_resumen),
            pd.DataFrame(columns=columnas_mes),
            pd.DataFrame(),
        )

    df = df_cobertura.copy()
    for col in ["M", "T", "N", "Libres"]:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    variables = [
        ("M", "Dotación M"),
        ("T", "Dotación T"),
        ("N", "Dotación N"),
        ("Libres", "Libres L + LB"),
    ]

    def calcular_fila(serie, nombre):
        serie = pd.to_numeric(pd.Series(serie), errors="coerce").fillna(0)
        if serie.empty:
            promedio = 0.0
            desviacion = 0.0
            consistencia = 0.0
            minimo = 0
            maximo = 0
            brecha = 0
        else:
            promedio = float(serie.mean())
            desviacion = float((serie - promedio).abs().mean()) if promedio > 0 else 0.0
            consistencia = indice_cercania_promedio(serie)
            minimo = int(serie.min())
            maximo = int(serie.max())
            brecha = int(maximo - minimo)
        return {
            "Indicador": nombre,
            "Promedio diario": round(promedio, 2),
            "Desviación promedio": round(desviacion, 2),
            "Consistencia (%)": consistencia,
            "Mínimo": minimo,
            "Máximo": maximo,
            "Brecha": brecha,
            "Días evaluados": int(len(serie)),
        }

    resumen_global = pd.DataFrame([
        calcular_fila(df[col], nombre)
        for col, nombre in variables
    ])

    filas_mes = []
    if "Mes" in df.columns and "Mes nombre" in df.columns:
        for (mes, mes_nombre), df_mes in df.groupby(["Mes", "Mes nombre"], sort=True):
            for col, nombre in variables:
                fila = calcular_fila(df_mes[col], nombre)
                fila["Mes"] = int(mes)
                fila["Mes nombre"] = mes_nombre
                filas_mes.append(fila)

    resumen_por_mes = pd.DataFrame(filas_mes)
    if not resumen_por_mes.empty:
        resumen_por_mes = resumen_por_mes[["Mes", "Mes nombre", *columnas_resumen]]

    # Tabla tipo matriz: filas M/T/N/Libres y columnas por día evaluado.
    etiquetas = df["Etiqueta día"].tolist() if "Etiqueta día" in df.columns else [str(i + 1) for i in range(len(df))]
    matriz = []
    for col, nombre in variables:
        fila = {"Indicador": nombre}
        for etiqueta, valor in zip(etiquetas, df[col].tolist()):
            fila[str(etiqueta)] = int(valor)
        calc = calcular_fila(df[col], nombre)
        fila["Promedio"] = calc["Promedio diario"]
        fila["Desviación prom."] = calc["Desviación promedio"]
        fila["Consistencia (%)"] = calc["Consistencia (%)"]
        fila["Mínimo"] = calc["Mínimo"]
        fila["Máximo"] = calc["Máximo"]
        fila["Brecha"] = calc["Brecha"]
        matriz.append(fila)

    matriz_diaria = pd.DataFrame(matriz)
    return resumen_global, resumen_por_mes, matriz_diaria


def construir_ausentismo_cierre_dashboard(df_cierres):
    """
    Calcula tres indicadores separados a partir de la hoja de cierre real:
    1) Ausentismo: registros A.
    2) Incapacidades: registros INCAP.
    3) Absentismo: otros estados administrativos o permisos: SSG, H, MC, LE, LM, LP, PCG y PSG.

    Además genera una tabla detallada por estado para graficar la distribución completa del cierre real.
    """
    otros_estados = ["SSG", "H", "MC", "LE", "LM", "LP", "PCG", "PSG"]
    estados_detalle = ["A", "INCAP", *otros_estados]
    nombres_detalle = {
        "A": "Ausentismo",
        "INCAP": "Incapacidades",
        "SSG": "SSG",
        "H": "H",
        "MC": "MC",
        "LE": "LE",
        "LM": "LM",
        "LP": "LP",
        "PCG": "PCG",
        "PSG": "PSG",
    }
    categorias_detalle = {
        "A": "Ausentismo",
        "INCAP": "Incapacidades",
        "SSG": "Absentismo",
        "H": "Absentismo",
        "MC": "Absentismo",
        "LE": "Absentismo",
        "LM": "Absentismo",
        "LP": "Absentismo",
        "PCG": "Absentismo",
        "PSG": "Absentismo",
    }

    metricas = {
        "meses_cerrados": 0,
        "personas_con_cierre": 0,
        "dias_actividad_reales": 0,
        "base_operativa": 0,
        "ausencias_a": 0,
        "ausencias_a_pct": 0.0,
        "incapacidades": 0,
        "incapacidades_pct": 0.0,
        "otros_absentismo": 0,
        "otros_absentismo_pct": 0.0,
        "total_no_trabajado": 0,
    }

    columnas_persona = [
        "Persona",
        "Días con actividad reales",
        "Ausentismo",
        "Incapacidades",
        "Absentismo",
        "Total no trabajado",
        "Base operativa",
        "Ausentismo (%)",
        "Incapacidades (%)",
        "Absentismo (%)",
    ]

    if df_cierres is None or df_cierres.empty:
        df_tipo_vacio = pd.DataFrame(columns=["Indicador", "Cantidad", "Porcentaje"])
        df_detalle_vacio = pd.DataFrame(columns=["Estado", "Indicador", "Categoría", "Cantidad", "Porcentaje"])
        df_persona_vacio = pd.DataFrame(columns=columnas_persona)
        return metricas, df_tipo_vacio, df_detalle_vacio, df_persona_vacio

    df = df_cierres.copy()
    df.columns = [str(c).strip() for c in df.columns]

    col_persona = buscar_columna_flexible_dashboard(df, ["Persona", "Nombre", "Funcionario", "Colaborador"])
    if col_persona and col_persona != "Persona":
        df["Persona"] = df[col_persona]
    elif "Persona" not in df.columns:
        df["Persona"] = ""

    col_dias = buscar_columna_flexible_dashboard(
        df,
        [
            "Días con actividad reales",
            "Dias con actividad reales",
            "Días actividad reales",
            "Dias actividad reales",
            "Actividad real",
            "Días reales",
            "Dias reales",
        ],
    )
    if col_dias:
        df["Días con actividad reales"] = pd.to_numeric(df[col_dias], errors="coerce").fillna(0)
    else:
        df["Días con actividad reales"] = 0

    mapa_columnas = {
        "A del mes": ["A del mes", "Ausencias A", "Ausencia A", "A"],
        "INCAP del mes": ["INCAP del mes", "Incapacidades", "Incapacidad", "INCAP"],
        "SSG del mes": ["SSG del mes", "SSG", "Suspensión sin goce", "Suspension sin goce"],
        "H del mes": ["H del mes", "H", "Huelga"],
        "MC del mes": ["MC del mes", "MC", "Medida cautelar"],
        "LE del mes": ["LE del mes", "LE", "Licencia extraordinaria"],
        "LM del mes": ["LM del mes", "LM", "Licencia maternidad"],
        "LP del mes": ["LP del mes", "LP", "Licencia paternidad"],
        "PCG del mes": ["PCG del mes", "PCG", "Permiso con goce", "Permiso con goce salarial"],
        "PSG del mes": ["PSG del mes", "PSG", "Permiso sin goce", "Permiso sin goce salarial"],
    }

    for col_estandar, candidatos in mapa_columnas.items():
        col_real = buscar_columna_flexible_dashboard(df, candidatos)
        if col_real:
            df[col_estandar] = pd.to_numeric(df[col_real], errors="coerce").fillna(0)
        else:
            df[col_estandar] = 0

    otros_columnas = [f"{estado} del mes" for estado in otros_estados]

    df["Ausentismo"] = df["A del mes"]
    df["Incapacidades"] = df["INCAP del mes"]
    df["Absentismo"] = df[otros_columnas].sum(axis=1)
    df["Total no trabajado"] = df["Ausentismo"] + df["Incapacidades"] + df["Absentismo"]
    df["Base operativa"] = df["Días con actividad reales"] + df["Total no trabajado"]

    if "Mes" in df.columns:
        metricas["meses_cerrados"] = int(pd.to_numeric(df["Mes"], errors="coerce").dropna().nunique())
    else:
        metricas["meses_cerrados"] = 1

    metricas["personas_con_cierre"] = int(df["Persona"].astype(str).str.strip().replace("", pd.NA).dropna().nunique())
    metricas["dias_actividad_reales"] = int(round(float(df["Días con actividad reales"].sum())))
    metricas["ausencias_a"] = int(round(float(df["Ausentismo"].sum())))
    metricas["incapacidades"] = int(round(float(df["Incapacidades"].sum())))
    metricas["otros_absentismo"] = int(round(float(df["Absentismo"].sum())))
    metricas["total_no_trabajado"] = int(round(float(df["Total no trabajado"].sum())))
    metricas["base_operativa"] = int(round(float(df["Base operativa"].sum())))

    metricas["ausencias_a_pct"] = porcentaje_seguro(metricas["ausencias_a"], metricas["base_operativa"])
    metricas["incapacidades_pct"] = porcentaje_seguro(metricas["incapacidades"], metricas["base_operativa"])
    metricas["otros_absentismo_pct"] = porcentaje_seguro(metricas["otros_absentismo"], metricas["base_operativa"])

    df_tipo = pd.DataFrame([
        {"Indicador": "Ausentismo", "Cantidad": metricas["ausencias_a"], "Porcentaje": metricas["ausencias_a_pct"]},
        {"Indicador": "Incapacidades", "Cantidad": metricas["incapacidades"], "Porcentaje": metricas["incapacidades_pct"]},
        {"Indicador": "Absentismo", "Cantidad": metricas["otros_absentismo"], "Porcentaje": metricas["otros_absentismo_pct"]},
    ])

    filas_detalle = []
    for estado in estados_detalle:
        col = "A del mes" if estado == "A" else "INCAP del mes" if estado == "INCAP" else f"{estado} del mes"
        cantidad = int(round(float(df[col].sum()))) if col in df.columns else 0
        filas_detalle.append({
            "Estado": estado,
            "Indicador": nombres_detalle[estado],
            "Categoría": categorias_detalle[estado],
            "Cantidad": cantidad,
            "Porcentaje": porcentaje_seguro(cantidad, metricas["base_operativa"]),
        })
    df_detalle_estado = pd.DataFrame(filas_detalle)

    df_persona = (
        df.groupby("Persona", dropna=False)
        .agg(**{
            "Días con actividad reales": ("Días con actividad reales", "sum"),
            "Ausentismo": ("Ausentismo", "sum"),
            "Incapacidades": ("Incapacidades", "sum"),
            "Absentismo": ("Absentismo", "sum"),
            "Total no trabajado": ("Total no trabajado", "sum"),
            "Base operativa": ("Base operativa", "sum"),
        })
        .reset_index()
    )

    df_persona["Ausentismo (%)"] = df_persona.apply(
        lambda r: porcentaje_seguro(r["Ausentismo"], r["Base operativa"]), axis=1
    )
    df_persona["Incapacidades (%)"] = df_persona.apply(
        lambda r: porcentaje_seguro(r["Incapacidades"], r["Base operativa"]), axis=1
    )
    df_persona["Absentismo (%)"] = df_persona.apply(
        lambda r: porcentaje_seguro(r["Absentismo"], r["Base operativa"]), axis=1
    )

    df_persona = df_persona.sort_values(
        by=["Total no trabajado", "Ausentismo", "Incapacidades", "Absentismo"],
        ascending=False,
    )

    df_persona = df_persona[[c for c in columnas_persona if c in df_persona.columns]]

    return metricas, df_tipo, df_detalle_estado, df_persona

def _normalizar_porcentaje_dashboard(serie):
    """Convierte porcentajes en formato 0-1, 0-100 o texto con % a escala 0-100."""
    s = pd.Series(serie).astype(str).str.replace("%", "", regex=False).str.replace(",", ".", regex=False)
    s = pd.to_numeric(s, errors="coerce").fillna(0)
    if not s.empty and s.max() <= 1:
        s = s * 100
    return s.clip(lower=0, upper=100)


def construir_indicadores_funciones_dashboard(df_funciones, df_sin_asignar, df_rotacion):
    """
    Construye indicadores de rotación funcional.

    La unidad de análisis es persona-semana-función. No se cuentan repeticiones por día,
    porque una misma asignación semanal aparece en varias columnas D del archivo de funciones.
    """
    metricas = {
        "total_asignaciones": 0,
        "personas_con_funcion": 0,
        "funciones_distintas_total": 0,
        "rotacion_funcional_pct": 0.0,
        "funciones_distintas_promedio": 0.0,
        "repeticion_promedio": 0.0,
        "equilibrio_asignaciones_pct": 0.0,
        "sin_asignar": 0,
        "sin_asignar_pct": 0.0,
        "personas_baja_rotacion": 0,
        "fuente_rotacion": "Asignaciones del período",
    }

    columnas_persona = [
        "Persona", "Asignaciones", "Funciones distintas", "Repeticiones", "Rotación del período (%)"
    ]
    df_persona = pd.DataFrame(columns=columnas_persona)
    df_funcion = pd.DataFrame(columns=["Función", "Asignaciones", "Participación (%)"])

    total_sin_asignar = int(len(df_sin_asignar)) if df_sin_asignar is not None and not df_sin_asignar.empty else 0
    metricas["sin_asignar"] = total_sin_asignar

    def calcular_rotacion_modelo(df_rotacion_local):
        rotacion_modelo_pct = None
        serie_pct = pd.Series(dtype=float)

        if df_rotacion_local is not None and not df_rotacion_local.empty:
            df_rot = df_rotacion_local.copy()
            col_persona_rot_local = buscar_columna(df_rot, ["Persona", "Nombre", "Funcionario"], obligatoria=False)
            if col_persona_rot_local is not None:
                df_rot = df_rot[~df_rot[col_persona_rot_local].apply(es_pseudo_persona_funciones)].copy()
            posibles_pct = [c for c in df_rot.columns if normalizar_texto(c) == normalizar_texto("Porcentaje_visitadas")]
            posibles_vis = [c for c in df_rot.columns if normalizar_texto(c) == normalizar_texto("Funciones_visitadas")]
            posibles_eleg = [c for c in df_rot.columns if normalizar_texto(c) == normalizar_texto("Funciones_elegibles")]

            if posibles_pct:
                serie_pct = _normalizar_porcentaje_dashboard(df_rot[posibles_pct[0]])
                if not serie_pct.empty:
                    rotacion_modelo_pct = round(float(serie_pct.mean()), 2)
                    metricas["fuente_rotacion"] = "Hoja Rotacion_Modelo_Usada"
            elif posibles_vis and posibles_eleg:
                vis = pd.to_numeric(df_rot[posibles_vis[0]], errors="coerce").fillna(0)
                eleg = pd.to_numeric(df_rot[posibles_eleg[0]], errors="coerce").fillna(0)
                serie_pct = pd.Series([porcentaje_seguro(v, e) for v, e in zip(vis, eleg)])
                if not serie_pct.empty:
                    rotacion_modelo_pct = round(float(serie_pct.mean()), 2)
                    metricas["fuente_rotacion"] = "Funciones visitadas / elegibles"

        return rotacion_modelo_pct, serie_pct

    # Fallback: si no se pudieron leer las hojas M/T/N, pero sí existe Rotacion_Modelo_Usada,
    # se construyen los indicadores con esa hoja para que el dashboard no quede en cero.
    if (df_funciones is None or df_funciones.empty) and df_rotacion is not None and not df_rotacion.empty:
        df_rot = df_rotacion.copy()
        col_persona = buscar_columna(df_rot, ["Persona"], obligatoria=False)
        if col_persona is None:
            col_persona = df_rot.columns[0]

        columnas_funciones = [c for c in df_rot.columns if str(c).strip() in FUNCIONES]
        if columnas_funciones:
            matriz = df_rot[[col_persona, *columnas_funciones]].copy()
            matriz = matriz.rename(columns={col_persona: "Persona"})
            matriz["Persona"] = matriz["Persona"].astype(str).str.strip()
            matriz = matriz[~matriz["Persona"].apply(es_pseudo_persona_funciones)].copy()
            for c in columnas_funciones:
                matriz[c] = pd.to_numeric(matriz[c], errors="coerce").fillna(0)

            matriz["Asignaciones"] = matriz[columnas_funciones].sum(axis=1)
            matriz["Funciones distintas"] = matriz[columnas_funciones].gt(0).sum(axis=1)
            matriz = matriz[matriz["Asignaciones"] > 0].copy()

            if not matriz.empty:
                matriz["Repeticiones"] = matriz["Asignaciones"] - matriz["Funciones distintas"]
                matriz["Rotación del período (%)"] = matriz.apply(
                    lambda r: porcentaje_seguro(r["Funciones distintas"], r["Asignaciones"]), axis=1
                )
                df_persona = matriz[["Persona", "Asignaciones", "Funciones distintas", "Repeticiones", "Rotación del período (%)"]].copy()

                total_asignaciones = int(matriz["Asignaciones"].sum())
                metricas["total_asignaciones"] = total_asignaciones
                metricas["personas_con_funcion"] = int(matriz["Persona"].nunique())
                metricas["funciones_distintas_total"] = int(sum(matriz[columnas_funciones].sum(axis=0) > 0))
                metricas["funciones_distintas_promedio"] = round(float(matriz["Funciones distintas"].mean()), 2)
                metricas["repeticion_promedio"] = round(float(matriz["Repeticiones"].mean()), 2)
                metricas["equilibrio_asignaciones_pct"] = indice_cercania_promedio(matriz["Asignaciones"])
                metricas["sin_asignar_pct"] = porcentaje_seguro(total_sin_asignar, total_asignaciones + total_sin_asignar)

                rotacion_modelo_pct, serie_pct = calcular_rotacion_modelo(df_rotacion)
                if rotacion_modelo_pct is not None:
                    metricas["rotacion_funcional_pct"] = rotacion_modelo_pct
                    metricas["personas_baja_rotacion"] = int((serie_pct < 50).sum()) if not serie_pct.empty else 0
                else:
                    metricas["rotacion_funcional_pct"] = round(float(df_persona["Rotación del período (%)"].mean()), 2)
                    metricas["personas_baja_rotacion"] = int((df_persona["Rotación del período (%)"] < 50).sum())

                df_funcion = pd.DataFrame({
                    "Función": columnas_funciones,
                    "Asignaciones": [int(matriz[c].sum()) for c in columnas_funciones],
                })
                df_funcion = df_funcion[df_funcion["Asignaciones"] > 0].sort_values(by="Asignaciones", ascending=False)
                df_funcion["Participación (%)"] = df_funcion["Asignaciones"].apply(
                    lambda x: porcentaje_seguro(x, total_asignaciones)
                )

                df_persona = df_persona.sort_values(
                    by=["Rotación del período (%)", "Asignaciones"],
                    ascending=[True, False]
                )
                metricas["fuente_rotacion"] = metricas["fuente_rotacion"] + " / respaldo por hoja de rotación"
                return metricas, df_persona, df_funcion

        metricas["sin_asignar_pct"] = porcentaje_seguro(total_sin_asignar, total_sin_asignar)
        return metricas, df_persona, df_funcion

    if df_funciones is None or df_funciones.empty:
        metricas["sin_asignar_pct"] = porcentaje_seguro(total_sin_asignar, total_sin_asignar)
        return metricas, df_persona, df_funcion

    df = df_funciones.copy()
    for col in ["Persona", "Funcion"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].astype(str).str.strip()

    df = df[(df["Persona"] != "") & (df["Funcion"] != "")].copy()
    df = df[~df["Persona"].apply(es_pseudo_persona_funciones)].copy()
    if df.empty:
        metricas["sin_asignar_pct"] = porcentaje_seguro(total_sin_asignar, total_sin_asignar)
        return metricas, df_persona, df_funcion

    metricas["total_asignaciones"] = int(len(df))
    metricas["personas_con_funcion"] = int(df["Persona"].nunique())
    metricas["funciones_distintas_total"] = int(df["Funcion"].nunique())

    df_persona = (
        df.groupby("Persona", dropna=False)
        .agg(
            Asignaciones=("Funcion", "count"),
            **{"Funciones distintas": ("Funcion", "nunique")}
        )
        .reset_index()
    )
    df_persona["Repeticiones"] = df_persona["Asignaciones"] - df_persona["Funciones distintas"]
    df_persona["Rotación del período (%)"] = df_persona.apply(
        lambda r: porcentaje_seguro(r["Funciones distintas"], r["Asignaciones"]), axis=1
    )

    rotacion_modelo_pct, serie_pct = calcular_rotacion_modelo(df_rotacion)
    if rotacion_modelo_pct is not None:
        metricas["rotacion_funcional_pct"] = rotacion_modelo_pct
        metricas["personas_baja_rotacion"] = int((serie_pct < 50).sum()) if not serie_pct.empty else 0
    else:
        metricas["rotacion_funcional_pct"] = round(float(df_persona["Rotación del período (%)"].mean()), 2)
        metricas["personas_baja_rotacion"] = int((df_persona["Rotación del período (%)"] < 50).sum())

    metricas["funciones_distintas_promedio"] = round(float(df_persona["Funciones distintas"].mean()), 2)
    metricas["repeticion_promedio"] = round(float(df_persona["Repeticiones"].mean()), 2)
    metricas["equilibrio_asignaciones_pct"] = indice_cercania_promedio(df_persona["Asignaciones"])
    metricas["sin_asignar_pct"] = porcentaje_seguro(
        metricas["sin_asignar"],
        metricas["total_asignaciones"] + metricas["sin_asignar"]
    )

    df_funcion = (
        df.groupby("Funcion", dropna=False)
        .size()
        .reset_index(name="Asignaciones")
        .rename(columns={"Funcion": "Función"})
        .sort_values(by="Asignaciones", ascending=False)
    )
    df_funcion["Participación (%)"] = df_funcion["Asignaciones"].apply(
        lambda x: porcentaje_seguro(x, metricas["total_asignaciones"])
    )

    df_persona = df_persona.sort_values(
        by=["Rotación del período (%)", "Asignaciones"],
        ascending=[True, False]
    )
    df_persona = df_persona[columnas_persona]

    return metricas, df_persona, df_funcion

def porcentaje_seguro(numerador, denominador):
    try:
        numerador = float(numerador)
        denominador = float(denominador)
    except Exception:
        return 0.0
    if denominador <= 0:
        return 0.0
    return round((numerador / denominador) * 100, 2)


def indice_igualdad(valores):
    """
    Índice por brecha simple. Se conserva para indicadores secundarios.
    100% significa que todos tienen el mismo valor.
    """
    serie = pd.to_numeric(pd.Series(valores), errors="coerce").fillna(0)
    if serie.empty:
        return 0.0
    maximo = float(serie.max())
    minimo = float(serie.min())
    if maximo <= 0:
        return 0.0
    valor = (1 - ((maximo - minimo) / maximo)) * 100
    return round(max(0.0, min(100.0, valor)), 2)


def indice_cercania_promedio(valores):
    """
    Mide equidad al promedio.

    Fórmula:
        equidad = 100 - (desviación promedio absoluta / promedio × 100)

    Lectura:
        100% = todos tienen prácticamente la misma cantidad.
        Un valor menor indica que algunas personas se alejan más del promedio.

    Esta fórmula es más útil para turnos que usar mínimo/máximo, porque evita que
    una sola persona con 0 turnos vuelva automáticamente 0% todo el indicador.
    """
    serie = pd.to_numeric(pd.Series(valores), errors="coerce").fillna(0)
    if serie.empty:
        return 0.0
    promedio = float(serie.mean())
    if promedio <= 0:
        return 0.0
    desviacion_promedio = float((serie - promedio).abs().mean())
    valor = 100 - ((desviacion_promedio / promedio) * 100)
    return round(max(0.0, min(100.0, valor)), 2)


def cercania_valor_promedio(valor, promedio):
    try:
        valor = float(valor)
        promedio = float(promedio)
    except Exception:
        return 0.0
    if promedio <= 0:
        return 0.0
    cercania = 100 - (abs(valor - promedio) / promedio * 100)
    return round(max(0.0, min(100.0, cercania)), 2)


def construir_metricas_porcentuales_dashboard(df_estados, df_equidad, df_funciones, df_sin_asignar, df_turnos_anual=None):
    """
    Construye indicadores claros para el dashboard.

    Criterios corregidos:
    - M, T y N no se presentan como "días trabajados" del calendario.
      Se presentan como turnos-persona programados.
    - El total de funciones se cuenta como persona-semana-función, no como persona-día-función.
    - La igualdad por turno se calcula como equidad al promedio de cada turno.
    - Si existe calendario anual, la igualdad de turnos se calcula desde el anual,
      no desde el mensual, para que L y LB no distorsionen el indicador.
    """
    metricas = {
        "tasa_ausentismo_operativo": 0.0,
        "tasa_ausentismo_total": 0.0,
        "porcentaje_trabajo": 0.0,
        "porcentaje_libres": 0.0,
        "porcentaje_vacaciones": 0.0,
        "carga_promedio": 0.0,
        "brecha_carga": 0,
        "igualdad_trabajo": 0.0,
        "igualdad_m": 0.0,
        "igualdad_t": 0.0,
        "igualdad_n": 0.0,
        "igualdad_turnos_global": 0.0,
        "igualdad_global": 0.0,
        "igualdad_funciones": 0.0,
        "rotacion_funcional_promedio": 0.0,
        "porcentaje_sin_asignar": 0.0,
        "promedio_m": 0.0,
        "promedio_t": 0.0,
        "promedio_n": 0.0,
    }

    df_turnos_pct = pd.DataFrame()
    df_aus_persona = pd.DataFrame()
    df_persona_turnos = pd.DataFrame()
    df_func_persona = pd.DataFrame()
    df_indicadores = pd.DataFrame()
    df_mensual_pct = pd.DataFrame()

    if df_estados is not None and not df_estados.empty:
        total_registros = len(df_estados)
        total_turnos_programados = int(df_estados["Estado"].isin(ESTADOS_TURNOS).sum())
        total_libres = int(df_estados["Estado"].isin(ESTADOS_LIBRES).sum())
        total_vacaciones = int(df_estados["Estado"].isin(ESTADOS_VACACIONES).sum())
        total_ausencias = int(df_estados["Estado"].isin(ESTADOS_AUSENCIAS).sum())
        base_operativa = total_turnos_programados + total_ausencias

        metricas["tasa_ausentismo_operativo"] = porcentaje_seguro(total_ausencias, base_operativa)
        metricas["tasa_ausentismo_total"] = porcentaje_seguro(total_ausencias, total_registros)
        metricas["porcentaje_trabajo"] = porcentaje_seguro(total_turnos_programados, total_registros)
        metricas["porcentaje_libres"] = porcentaje_seguro(total_libres, total_registros)
        metricas["porcentaje_vacaciones"] = porcentaje_seguro(total_vacaciones, total_registros)

        df_tmp = df_estados.copy()
        df_tmp["Categoría"] = df_tmp["Estado"].apply(
            lambda e: "Turno programado" if e in ESTADOS_TURNOS
            else "Libres" if e in ESTADOS_LIBRES
            else "Vacaciones" if e in ESTADOS_VACACIONES
            else "Ausencias" if e in ESTADOS_AUSENCIAS
            else "Otros"
        )
        df_mensual_pct = (
            df_tmp.groupby(["Mes", "Mes nombre", "Categoría"])
            .size()
            .reset_index(name="Cantidad")
        )
        if not df_mensual_pct.empty:
            total_mes = df_mensual_pct.groupby("Mes")["Cantidad"].transform("sum")
            df_mensual_pct["Porcentaje"] = (df_mensual_pct["Cantidad"] / total_mes * 100).round(2)

    if df_equidad is not None and not df_equidad.empty:
        total_turnos_programados = float(df_equidad["Días trabajados"].sum())
        total_ausencias_persona = float(df_equidad["Ausencias"].sum())
        max_trabajo = int(df_equidad["Días trabajados"].max())
        min_trabajo = int(df_equidad["Días trabajados"].min())

        metricas["carga_promedio"] = round(float(df_equidad["Días trabajados"].mean()), 2)
        metricas["brecha_carga"] = max_trabajo - min_trabajo
        metricas["igualdad_trabajo"] = indice_cercania_promedio(df_equidad["Días trabajados"])

        df_aus_persona = df_equidad[["Persona", "Días trabajados", "Ausencias"]].copy()
        df_aus_persona = df_aus_persona.rename(columns={"Días trabajados": "Turnos programados"})
        df_aus_persona["Base operativa"] = df_aus_persona["Turnos programados"] + df_aus_persona["Ausencias"]
        df_aus_persona["Ausentismo operativo (%)"] = df_aus_persona.apply(
            lambda r: porcentaje_seguro(r["Ausencias"], r["Base operativa"]), axis=1
        )
        df_aus_persona["Participación en ausencias (%)"] = df_aus_persona["Ausencias"].apply(
            lambda x: porcentaje_seguro(x, total_ausencias_persona)
        )
        df_aus_persona = df_aus_persona.sort_values(
            by=["Ausentismo operativo (%)", "Ausencias"], ascending=False
        )

    # La igualdad de turnos se calcula únicamente desde el anual.
    # El mensual se reserva para cobertura diaria y distribución de libres.
    # Para noche se excluyen personas con 0 noches, porque corresponden a coordinación
    # y no deben compararse contra quienes sí rotan en el turno nocturno.
    df_base_turnos = contar_turnos_anuales_por_persona(df_turnos_anual)
    fuente_turnos = "Calendario anual"
    columna_total_turnos = "Total turnos anuales"

    if not df_base_turnos.empty:
        total_turnos_base = float(df_base_turnos[columna_total_turnos].sum())

        serie_m = pd.to_numeric(df_base_turnos["Mañanas"], errors="coerce").fillna(0)
        serie_t = pd.to_numeric(df_base_turnos["Tardes"], errors="coerce").fillna(0)
        serie_n_todas = pd.to_numeric(df_base_turnos["Noches"], errors="coerce").fillna(0)
        serie_n_calculo = serie_n_todas[serie_n_todas > 0]

        metricas["igualdad_m"] = indice_cercania_promedio(serie_m)
        metricas["igualdad_t"] = indice_cercania_promedio(serie_t)
        metricas["igualdad_n"] = indice_cercania_promedio(serie_n_calculo)
        metricas["igualdad_turnos_global"] = round(
            (metricas["igualdad_m"] + metricas["igualdad_t"] + metricas["igualdad_n"]) / 3,
            2
        )
        metricas["igualdad_global"] = metricas["igualdad_turnos_global"]

        promedios_turno = {
            "Mañanas": float(serie_m.mean()) if not serie_m.empty else 0.0,
            "Tardes": float(serie_t.mean()) if not serie_t.empty else 0.0,
            "Noches": float(serie_n_calculo.mean()) if not serie_n_calculo.empty else 0.0,
        }
        metricas["promedio_m"] = round(promedios_turno["Mañanas"], 2)
        metricas["promedio_t"] = round(promedios_turno["Tardes"], 2)
        metricas["promedio_n"] = round(promedios_turno["Noches"], 2)

        filas_turnos = []
        for estado, nombre, col in [
            ("M", "Mañana", "Mañanas"),
            ("T", "Tarde", "Tardes"),
            ("N", "Noche", "Noches"),
        ]:
            serie_original = pd.to_numeric(df_base_turnos[col], errors="coerce").fillna(0)
            serie_calculo = serie_original[serie_original > 0] if estado == "N" else serie_original
            total_turno = int(serie_original.sum())
            promedio = float(serie_calculo.mean()) if not serie_calculo.empty else 0.0
            desviacion = float((serie_calculo - promedio).abs().mean()) if not serie_calculo.empty else 0.0
            max_turno = int(serie_calculo.max()) if not serie_calculo.empty else 0
            min_turno = int(serie_calculo.min()) if not serie_calculo.empty else 0
            filas_turnos.append({
                "Turno": estado,
                "Nombre": nombre,
                "Fuente": fuente_turnos,
                "Personas incluidas en cálculo": int(serie_calculo.shape[0]),
                "Personas excluidas": int(serie_original.shape[0] - serie_calculo.shape[0]) if estado == "N" else 0,
                "Criterio de exclusión": "Se excluyen personas con 0 noches" if estado == "N" else "No aplica",
                "Total asignaciones anuales": total_turno,
                "Participación del total M/T/N (%)": porcentaje_seguro(total_turno, total_turnos_base),
                "Promedio por persona": round(promedio, 2),
                "Desviación promedio": round(desviacion, 2),
                "Mínimo": min_turno,
                "Máximo": max_turno,
                "Brecha": max_turno - min_turno,
                "Equidad al promedio (%)": indice_cercania_promedio(serie_calculo),
                "Cálculo": "100 - (desviación promedio absoluta / promedio × 100)",
            })
        df_turnos_pct = pd.DataFrame(filas_turnos)

        df_persona_turnos = df_base_turnos.copy()
        df_persona_turnos["Fuente"] = fuente_turnos
        df_persona_turnos["Promedio esperado M"] = round(promedios_turno["Mañanas"], 2)
        df_persona_turnos["Promedio esperado T"] = round(promedios_turno["Tardes"], 2)
        df_persona_turnos["Promedio esperado N"] = round(promedios_turno["Noches"], 2)
        df_persona_turnos["Equidad M (%)"] = df_persona_turnos["Mañanas"].apply(lambda x: cercania_valor_promedio(x, promedios_turno["Mañanas"]))
        df_persona_turnos["Equidad T (%)"] = df_persona_turnos["Tardes"].apply(lambda x: cercania_valor_promedio(x, promedios_turno["Tardes"]))
        df_persona_turnos["Equidad N (%)"] = df_persona_turnos["Noches"].apply(
            lambda x: pd.NA if float(x) == 0 else cercania_valor_promedio(x, promedios_turno["Noches"])
        )
        df_persona_turnos["Nota N"] = df_persona_turnos["Noches"].apply(
            lambda x: "Excluido del cálculo de noche" if float(x) == 0 else "Incluido"
        )
        df_persona_turnos["Equidad turnos global (%)"] = df_persona_turnos[["Equidad M (%)", "Equidad T (%)", "Equidad N (%)"]].mean(axis=1, skipna=True).round(2)
        df_persona_turnos["% Mañana sobre su distribución anual"] = df_persona_turnos.apply(lambda r: porcentaje_seguro(r["Mañanas"], r[columna_total_turnos]), axis=1)
        df_persona_turnos["% Tarde sobre su distribución anual"] = df_persona_turnos.apply(lambda r: porcentaje_seguro(r["Tardes"], r[columna_total_turnos]), axis=1)
        df_persona_turnos["% Noche sobre su distribución anual"] = df_persona_turnos.apply(lambda r: porcentaje_seguro(r["Noches"], r[columna_total_turnos]), axis=1)
        df_persona_turnos = df_persona_turnos.sort_values(by="Equidad turnos global (%)", ascending=True)

    if df_funciones is not None and not df_funciones.empty:
        total_funciones = len(df_funciones)
        df_func_persona = (
            df_funciones.groupby("Persona")
            .agg(
                **{
                    "Funciones asignadas": ("Funcion", "count"),
                    "Funciones distintas": ("Funcion", "nunique"),
                }
            )
            .reset_index()
        )
        if "Turno" in df_funciones.columns:
            turnos_distintos = df_funciones.groupby("Persona")["Turno"].nunique().reset_index(name="Turnos distintos")
            df_func_persona = df_func_persona.merge(turnos_distintos, on="Persona", how="left")
        else:
            df_func_persona["Turnos distintos"] = 0

        df_func_persona["Participación en funciones (%)"] = df_func_persona["Funciones asignadas"].apply(
            lambda x: porcentaje_seguro(x, total_funciones)
        )
        df_func_persona["Rotación de funciones (%)"] = df_func_persona["Funciones distintas"].apply(
            lambda x: porcentaje_seguro(x, len(FUNCIONES))
        )
        df_func_persona = df_func_persona.sort_values(by="Funciones asignadas", ascending=False)
        metricas["igualdad_funciones"] = indice_cercania_promedio(df_func_persona["Funciones asignadas"])
        metricas["rotacion_funcional_promedio"] = round(float(df_func_persona["Rotación de funciones (%)"].mean()), 2)

    total_sin_asignar = len(df_sin_asignar) if df_sin_asignar is not None and not df_sin_asignar.empty else 0
    total_funciones = len(df_funciones) if df_funciones is not None and not df_funciones.empty else 0
    metricas["porcentaje_sin_asignar"] = porcentaje_seguro(total_sin_asignar, total_funciones + total_sin_asignar)

    df_indicadores = pd.DataFrame([
        {
            "Indicador": "Total de funciones asignadas",
            "Valor": total_funciones,
            "Cálculo": "Conteo único persona-semana-función",
            "Lectura": "No se multiplica por cada día; una función semanal cuenta una sola vez.",
        },
        {
            "Indicador": "Turnos-persona programados",
            "Valor": int(df_equidad["Días trabajados"].sum()) if df_equidad is not None and not df_equidad.empty else 0,
            "Cálculo": "Conteo de celdas M, T y N del calendario mensual",
            "Lectura": "No son días calendario; son asignaciones persona-día de turno.",
        },
        {
            "Indicador": "Ausentismo operativo (%)",
            "Valor": f"{metricas['tasa_ausentismo_operativo']}%",
            "Cálculo": "Ausencias / (turnos programados + ausencias)",
            "Lectura": "Mide el peso de las ausencias sobre los turnos donde se esperaba actividad.",
        },
        {
            "Indicador": "Equidad global de turnos (%)",
            "Valor": f"{metricas['igualdad_turnos_global']}%",
            "Cálculo": "Promedio de equidad M, T y N calculado desde el anual",
            "Lectura": "Mide qué tan cerca están las personas del promedio de semanas asignadas por turno, sin descontar libres mensuales.",
        },
        {
            "Indicador": "Equidad mañanas (%)",
            "Valor": f"{metricas['igualdad_m']}%",
            "Cálculo": "100 - (desviación promedio de M anual / promedio M anual × 100)",
            "Lectura": "Mide si las semanas de mañana del anual están distribuidas cerca del promedio.",
        },
        {
            "Indicador": "Equidad tardes (%)",
            "Valor": f"{metricas['igualdad_t']}%",
            "Cálculo": "100 - (desviación promedio de T anual / promedio T anual × 100)",
            "Lectura": "Mide si las semanas de tarde del anual están distribuidas cerca del promedio.",
        },
        {
            "Indicador": "Equidad noches (%)",
            "Valor": f"{metricas['igualdad_n']}%",
            "Cálculo": "100 - (desviación promedio de N anual / promedio N anual × 100)",
            "Lectura": "Mide si las semanas de noche del anual están distribuidas cerca del promedio.",
        },
        {
            "Indicador": "Brecha de carga",
            "Valor": metricas["brecha_carga"],
            "Cálculo": "Máximo de turnos-persona - mínimo de turnos-persona",
            "Lectura": "Muestra la diferencia de carga operativa entre la persona más cargada y la menos cargada.",
        },
        {
            "Indicador": "Rotación de funciones (%)",
            "Valor": f"{metricas['rotacion_funcional_promedio']}%",
            "Cálculo": "Funciones distintas visitadas / funciones posibles",
            "Lectura": "Mide qué tanto se diversifica la asignación funcional del personal.",
        },
        {
            "Indicador": "Personas sin función asignada (%)",
            "Valor": f"{metricas['porcentaje_sin_asignar']}%",
            "Cálculo": "Sin asignar / (funciones asignadas + sin asignar)",
            "Lectura": "Permite detectar problemas de cobertura funcional.",
        },
    ])

    return metricas, df_indicadores, df_turnos_pct, df_aus_persona, df_persona_turnos, df_func_persona, df_mensual_pct

# Paleta azul institucional para gráficos generales.
# Se usa en gráficos analíticos del dashboard, excepto en gráficos/tablitas que
# deben respetar la simbología operativa de estados M, T, N, L, LB, V, A, etc.
PALETA_GRAFICOS_AZUL = ["#dbe6ef", "#9fb7cf", "#4f6f8d", "#12263a"]
PALETA_GRAFICOS_AZUL_CATEGORICA = ["#12263a", "#4f6f8d", "#9fb7cf", "#dbe6ef"]

def grafico_barras(df, x, y, titulo, color=None, dominio=None, rango=None, horizontal=False, altura=320, y_title="Cantidad"):
    if df is None or df.empty:
        st.info("No hay datos suficientes para este gráfico.")
        return

    if horizontal:
        eje_x = alt.X(f"{y}:Q", title=y_title)
        eje_y = alt.Y(f"{x}:N", sort="-x", title=None)
    else:
        eje_x = alt.X(f"{x}:N", sort=None, title=None)
        eje_y = alt.Y(f"{y}:Q", title=y_title)

    if color and dominio and rango:
        color_enc = alt.Color(
            f"{color}:N",
            scale=alt.Scale(domain=dominio, range=rango),
            legend=alt.Legend(title="Categoría")
        )
    elif color:
        color_enc = alt.Color(f"{color}:N", legend=alt.Legend(title="Categoría"))
    else:
        color_enc = alt.Color(
            f"{y}:Q",
            scale=alt.Scale(range=PALETA_GRAFICOS_AZUL),
            legend=None,
        )

    chart = (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=eje_x,
            y=eje_y,
            color=color_enc,
            tooltip=list(df.columns),
        )
        .properties(title=titulo, height=altura)
        .configure_title(
            font="Georgia",
            fontSize=17,
            fontWeight="bold",
            color="#20384a",
            anchor="start",
        )
        .configure_axis(
            labelFont="Georgia",
            titleFont="Georgia",
            labelColor="#64748b",
            titleColor="#475569",
        )
        .configure_legend(
            labelFont="Georgia",
            titleFont="Georgia",
            labelColor="#475569",
            titleColor="#20384a",
        )
    )

    st.altair_chart(chart, use_container_width=True)


def mostrar_leyenda_estados():
    chips = []
    for estado, color in COLORES_ESTADOS_DASHBOARD.items():
        texto = NOMBRES_ESTADOS.get(estado, estado)
        color_texto = "#ffffff" if estado in ["N", "V", "LB", "A", "INCAP", "SSG", "H", "MC", "LE", "PSG"] else "#083344"
        chips.append(
            f"<span style='display:inline-block;background:{color};color:{color_texto};"
            f"padding:0.28rem 0.55rem;border-radius:999px;font-size:0.80rem;"
            f"font-weight:700;margin-right:0.35rem;margin-bottom:0.35rem;'>{estado} · {texto}</span>"
        )
    st.markdown("".join(chips), unsafe_allow_html=True)


def construir_alertas_dashboard(df_estados, df_equidad, df_funciones, df_sin_asignar):
    alertas = []

    if df_estados.empty:
        alertas.append({"Nivel": "Revisar", "Detalle": "No se encontraron calendarios mensuales para el período seleccionado."})
        return pd.DataFrame(alertas)

    if not df_equidad.empty:
        max_trab = int(df_equidad["Días trabajados"].max())
        min_trab = int(df_equidad["Días trabajados"].min())
        brecha = max_trab - min_trab
        if brecha >= 6:
            alertas.append({"Nivel": "Revisar", "Detalle": f"La brecha de turnos programados entre personas es alta: {brecha} registros persona-día."})
        else:
            alertas.append({"Nivel": "OK", "Detalle": f"La brecha de turnos programados es de {brecha} registros persona-día para el período filtrado."})

        personas_mas_noches = df_equidad.sort_values(by="Noches", ascending=False).head(3)
        if not personas_mas_noches.empty and int(personas_mas_noches.iloc[0]["Noches"]) > 0:
            detalle = ", ".join(
                f"{row['Persona']} ({int(row['Noches'])})"
                for _, row in personas_mas_noches.iterrows()
            )
            alertas.append({"Nivel": "Info", "Detalle": f"Personas con más noches: {detalle}."})

        personas_mas_aus = df_equidad.sort_values(by="Ausencias", ascending=False).head(3)
        if not personas_mas_aus.empty and int(personas_mas_aus.iloc[0]["Ausencias"]) > 0:
            detalle = ", ".join(
                f"{row['Persona']} ({int(row['Ausencias'])})"
                for _, row in personas_mas_aus.iterrows()
            )
            alertas.append({"Nivel": "Revisar", "Detalle": f"Personas con más ausencias registradas: {detalle}."})

    if not df_sin_asignar.empty:
        alertas.append({"Nivel": "Revisar", "Detalle": f"Hay {len(df_sin_asignar)} registros de personas sin asignar en funciones."})
    elif not df_funciones.empty:
        alertas.append({"Nivel": "OK", "Detalle": "No se detectaron personas sin asignar en los archivos de funciones revisados."})

    if df_funciones.empty:
        alertas.append({"Nivel": "Info", "Detalle": "No hay archivos de funciones para todos los meses seleccionados o todavía no se han generado."})

    return pd.DataFrame(alertas)

# =========================================================
# INTERFAZ PRINCIPAL 
# =========================================================
# =========================================================
# INTERFAZ PRINCIPAL - APP CEYE
# =========================================================

with st.sidebar:
    RUTA_LOGO = Path(__file__).parent / "logo_hnn.png"

    if RUTA_LOGO.exists():
        st.image(str(RUTA_LOGO), width=165)

    st.markdown("""
    <div style="margin-top: 0.35rem; margin-bottom: 1.35rem; max-width: 190px;">
        <div style="
            font-family: Georgia, 'Times New Roman', serif;
            font-size: 1.30rem;
            font-weight: 700;
            line-height: 1.18;
            color: white;">
            Central de Esterilización y Equipos
        </div>
        <div style="
            color: #dceffd;
            margin-top: 0.65rem;
            font-size: 0.92rem;
            line-height: 1.4;">
            Hospital Nacional de Niños
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    year_app = st.number_input(
        "Año de trabajo",
        min_value=2024,
        max_value=2100,
        value=datetime.date.today().year,
        step=1
    )
    year_app = int(year_app)

    meses = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Setiembre", "Octubre", "Noviembre", "Diciembre"
    ]

    mes_panel = st.selectbox(
        "Mes de revisión",
        options=list(range(1, 13)),
        index=datetime.date.today().month - 1,
        format_func=lambda x: meses[x - 1]
    )

    carpeta_trabajo = APP_DATA_DIR / str(year_app)
    carpeta_trabajo.mkdir(parents=True, exist_ok=True)

    st.markdown("---")
    st.caption(f"Carpeta interna: {carpeta_trabajo}")


st.markdown("""
<div class="app-header">
    <div class="app-title">Planificación y Asignación de Personal CEYE</div>
    <div class="app-subtitle">
        Aplicación para generar la programación anual, mensual y asignación de funciones
        del personal de la Central de Esterilización y Equipos.
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="app-box">
    <h3>Flujo de trabajo</h3>
    <p style="margin-bottom: 0.55rem;">
        <b>1.</b> Administre la <b>base de datos interna</b> desde la interfaz.
    </p>
    <p style="margin-bottom: 0.55rem;">
        <b>2.</b> Genere el <b>calendario anual</b> usando la base guardada.
    </p>
    <p style="margin-bottom: 0.55rem;">
        <b>3.</b> Seleccione un mes y ejecute el <b>modelo mensual</b> usando el anual guardado.
    </p>
    <p style="margin-bottom: 0;">
        <b>4.</b> Edite, cierre el mes real y asigne funciones con los archivos internos.
    </p>
</div>
""", unsafe_allow_html=True) 
tab_base, tab_anual, tab_mensual, tab_editar, tab_funciones, tab_dashboard, tab_archivos = st.tabs([
    "Base de datos",
    "Anual",
    "Programar mes",
    "Editar y cerrar mes",
    "Asignar funciones",
    "Dashboard",
    "Archivos guardados"
])
# =========================================================
# TAB 0: BASE DE DATOS
# =========================================================
with tab_base:
    st.subheader("🗂️ Base de datos interna")
    ruta_base_actual = ruta_base(year_app)

    st.markdown("""
    <div class="custom-card">
        <h3>Base editable del sistema</h3>
        <p class="soft-text">
            La aplicación usa automáticamente la base guardada para el año seleccionado.
            Puede importar una base nueva, editar sus hojas desde esta pantalla y descargar
            un respaldo cuando lo necesite.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col_estado_base, col_accion_base = st.columns([1, 2])
    with col_estado_base:
        st.write("Base interna:", "✅ disponible" if ruta_base_actual.exists() else "❌ falta")
        st.caption(f"Año seleccionado: {year_app}")
    with col_accion_base:
        archivo_base = st.file_uploader(
            "Importar o reemplazar BaseDatos.xlsx",
            type=["xlsx"],
            key=f"base_interna_{year_app}"
        )
        if archivo_base:
            guardar_archivo_subido(archivo_base, ruta_base_actual)
            st.success("✅ Base importada. A partir de ahora los modelos usarán esta versión.")
            st.rerun()

    if not ruta_base_actual.exists():
        st.warning("Todavía no hay una base interna para este año.")
        if st.button("Crear plantilla vacía de base", key=f"crear_base_plantilla_{year_app}"):
            crear_base_plantilla(ruta_base_actual)
            st.success("✅ Plantilla creada. Ahora puede editar las hojas Asistentes y Saldo.")
            st.rerun()
    else:
        try:
            hojas_base_editor = leer_hojas_excel(ruta_base_actual)
            hojas_prioritarias = [h for h in ["Asistentes", "Saldo", "Hoja1", "Hoja3"] if h in hojas_base_editor]
            otras_hojas = [h for h in hojas_base_editor if h not in hojas_prioritarias]
            hojas_ordenadas = hojas_prioritarias + otras_hojas

            col_hoja_base, col_descarga_base = st.columns([2, 1])
            with col_hoja_base:
                hoja_editable = st.selectbox(
                    "Hoja a editar",
                    options=hojas_ordenadas,
                    key=f"hoja_base_editable_{year_app}"
                )
            with col_descarga_base:
                st.download_button(
                    "📥 Descargar respaldo",
                    archivo_a_bytes(ruta_base_actual),
                    file_name=f"BaseDatos_{year_app}_respaldo.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"download_base_respaldo_{year_app}"
                )

            df_hoja_base = pd.read_excel(ruta_base_actual, sheet_name=hoja_editable, engine="openpyxl")
            df_hoja_base.columns = [str(c).strip() for c in df_hoja_base.columns]

            if hoja_editable == "Asistentes":
                columnas_obligatorias_base = ["Persona", "Rol", "Semanas de Vacaciones"]
                faltantes_base = [c for c in columnas_obligatorias_base if c not in df_hoja_base.columns]
                if faltantes_base:
                    st.error(
                        "A esta hoja le faltan columnas obligatorias para el modelo anual: "
                        + ", ".join(faltantes_base)
                    )
                if "Esteriliza" not in df_hoja_base.columns and "F6" not in df_hoja_base.columns:
                    st.warning("Conviene incluir la columna Esteriliza o F6 para validar esterilización.")
            elif hoja_editable == "Saldo":
                if "Persona" not in df_hoja_base.columns:
                    st.error("La hoja Saldo debe tener una columna Persona para poder unirla con Asistentes.")

            st.caption(
                f"Editando hoja {hoja_editable}: "
                f"{len(df_hoja_base)} filas y {len(df_hoja_base.columns)} columnas."
            )

            df_hoja_editada = st.data_editor(
                df_hoja_base,
                use_container_width=True,
                height=650,
                num_rows="dynamic",
                key=f"editor_base_{year_app}_{hoja_editable}"
            )

            col_guardar_base, col_recargar_base = st.columns(2)
            with col_guardar_base:
                if st.button("💾 Guardar cambios en esta hoja", key=f"guardar_base_{year_app}_{hoja_editable}"):
                    guardar_hoja_excel(ruta_base_actual, hoja_editable, df_hoja_editada)
                    st.success(f"✅ Hoja {hoja_editable} guardada en la base interna.")
                    st.rerun()
            with col_recargar_base:
                if st.button("↻ Descartar cambios no guardados", key=f"recargar_base_{year_app}_{hoja_editable}"):
                    st.rerun()

        except Exception as e:
            st.error(f"No se pudo abrir o editar la base interna: {e}")

# =========================================================
# TAB 1: ANUAL
# =========================================================
with tab_anual:
    st.subheader("1️⃣ Generar calendario anual")
    st.caption("El modelo anual usa automáticamente la base interna administrada en la pestaña Base de datos.")

    if ruta_base(year_app).exists():
        try:
            columnas_preview_requeridas = ["Persona", "Rol", "Semanas de Vacaciones"]
            xls_preview = pd.ExcelFile(ruta_base(year_app), engine="openpyxl")
            df_base_preview = None
            for hoja_preview in ["Asistentes", "Hoja1", "Hoja3", *xls_preview.sheet_names]:
                if hoja_preview not in xls_preview.sheet_names:
                    continue
                df_preview_temp = pd.read_excel(ruta_base(year_app), sheet_name=hoja_preview, engine="openpyxl")
                df_preview_temp.columns = df_preview_temp.columns.str.strip()
                if all(col in df_preview_temp.columns for col in columnas_preview_requeridas):
                    df_base_preview = df_preview_temp
                    break
            if df_base_preview is None:
                raise ValueError("No se encontró una hoja de personas con Persona, Rol y Semanas de Vacaciones.")
            # Limpieza igual que en el modelo anual: evita que vacaciones fijas
            # seleccionadas en la interfaz no se apliquen por espacios en Persona.
            df_base_preview = df_base_preview[df_base_preview["Persona"].notna()].copy()
            df_base_preview["Persona"] = df_base_preview["Persona"].astype(str).str.strip()
            df_base_preview = df_base_preview[df_base_preview["Persona"] != ""].copy()
            df_base_preview["Rol"] = pd.to_numeric(df_base_preview["Rol"], errors="coerce")
            df_base_preview = df_base_preview[df_base_preview["Rol"].notna()].copy()
            df_base_preview = df_base_preview[df_base_preview["Rol"].astype(int) != 4].copy()
            df_base_preview["Rol"] = df_base_preview["Rol"].astype(int)
            df_base_preview["Semanas de Vacaciones"] = pd.to_numeric(
                df_base_preview["Semanas de Vacaciones"], errors="coerce"
            ).fillna(0).astype(int)
            st.markdown("**Vista previa del personal usado en el modelo anual**")
            mostrar_dataframe_persona_fija(df_base_preview.head(20))

            df_tmp = df_base_preview.set_index("Persona")
            P_tmp = list(df_tmp.index)
            W_tmp = df_tmp["Semanas de Vacaciones"].to_dict()
            rol_tmp = df_tmp["Rol"].astype(int).to_dict()
            num_semanas = datetime.date(year_app, 12, 31).isocalendar()[1]
            semanas = list(range(1, num_semanas + 1))

            st.markdown("### 👥 Configurar cantidad mínima y máxima de personas por turno")
            st.caption("Estos valores se usan en el calendario anual como límites mínimo y máximo por semana y turno.")

            col_dot_m, col_dot_t, col_dot_n = st.columns(3)
            with col_dot_m:
                min_m = st.number_input(
                    "Mínimo Mañana",
                    min_value=0,
                    max_value=len(P_tmp),
                    value=min(11, len(P_tmp)),
                    step=1,
                    key=f"min_m_{year_app}"
                )
                max_m = st.number_input(
                    "Máximo Mañana",
                    min_value=0,
                    max_value=len(P_tmp),
                    value=min(20, len(P_tmp)),
                    step=1,
                    key=f"max_m_{year_app}"
                )
            with col_dot_t:
                min_t = st.number_input(
                    "Mínimo Tarde",
                    min_value=0,
                    max_value=len(P_tmp),
                    value=min(10, len(P_tmp)),
                    step=1,
                    key=f"min_t_{year_app}"
                )
                max_t = st.number_input(
                    "Máximo Tarde",
                    min_value=0,
                    max_value=len(P_tmp),
                    value=min(20, len(P_tmp)),
                    step=1,
                    key=f"max_t_{year_app}"
                )
            with col_dot_n:
                min_n = st.number_input(
                    "Mínimo Noche",
                    min_value=0,
                    max_value=len(P_tmp),
                    value=min(3, len(P_tmp)),
                    step=1,
                    key=f"min_n_{year_app}"
                )
                max_n = st.number_input(
                    "Máximo Noche",
                    min_value=0,
                    max_value=len(P_tmp),
                    value=min(4, len(P_tmp)),
                    step=1,
                    key=f"max_n_{year_app}"
                )

            dotacion_turnos_min_ui = {
                "Mañana": int(min_m),
                "Tarde": int(min_t),
                "Noche": int(min_n),
            }
            dotacion_turnos_max_ui = {
                "Mañana": int(max_m),
                "Tarde": int(max_t),
                "Noche": int(max_n),
            }

            st.markdown("### 🧼 Configurar esterilización nocturna")
            st.caption("Cantidad mínima de personas capaces de esterilizar que deben quedar asignadas en el turno de noche cada semana.")
            min_esteriliza_noche_ui = st.number_input(
                "Mínimo de personas que esterilizan por noche",
                min_value=0,
                max_value=max(0, int(max_n)),
                value=min(2, int(max_n)),
                step=1,
                key=f"min_esteriliza_noche_{year_app}"
            )

            st.markdown("### 📌 Configurar vacaciones fijas")
            st.caption(
                "Marque los cuadritos de las semanas que desea fijar como vacaciones. "
                "La tabla se desplaza horizontalmente para ver todas las semanas del año."
            )

            V_ui = {}
            errores_vacaciones = []

            with st.expander("Seleccionar semanas de vacaciones fijas", expanded=True):
                filas_vacaciones = []
                for p in P_tmp:
                    fila = {
                        "Persona": p,
                        "Rol": int(rol_tmp[p]),
                        "Máx vacaciones": int(W_tmp[p]),
                    }
                    for s in semanas:
                        fila[f"S{s}"] = False
                    filas_vacaciones.append(fila)

                df_vacaciones_base = pd.DataFrame(filas_vacaciones).set_index("Persona")
                df_vacaciones_base.index.name = "Persona"

                # Mantiene la última versión aplicada de la tabla.
                # El editor se coloca dentro de un formulario para evitar que
                # Streamlit reconstruya toda la pestaña con cada cuadrito marcado.
                # La selección se valida y se aplica únicamente al presionar el botón.
                clave_vacaciones_validas = f"vacaciones_fijas_validas_{year_app}"
                clave_mensaje_vacaciones = f"vacaciones_fijas_mensaje_{year_app}"

                reiniciar_tabla_vacaciones = (
                    clave_vacaciones_validas not in st.session_state
                    or list(st.session_state[clave_vacaciones_validas].index) != list(df_vacaciones_base.index)
                    or list(st.session_state[clave_vacaciones_validas].columns) != list(df_vacaciones_base.columns)
                )

                if reiniciar_tabla_vacaciones:
                    st.session_state[clave_vacaciones_validas] = df_vacaciones_base.copy()

                if clave_mensaje_vacaciones in st.session_state:
                    st.warning(st.session_state[clave_mensaje_vacaciones])
                    del st.session_state[clave_mensaje_vacaciones]

                columnas_config_vac = {
                    "Rol": st.column_config.NumberColumn("Rol"),
                    "Máx vacaciones": st.column_config.NumberColumn("Máx vacaciones"),
                }
                for s in semanas:
                    mes_semana = obtener_nombre_mes_semana_anual(year_app, s, abreviado=True)
                    columnas_config_vac[f"S{s}"] = st.column_config.CheckboxColumn(
                        f"{mes_semana}\nS{s}",
                        help=f"{obtener_nombre_mes_semana_anual(year_app, s)} - Semana {s}",
                        default=False,
                    )

                st.info(
                    "Marque todas las semanas necesarias y luego presione "
                    "**Aplicar selección de vacaciones**."
                )

                with st.form(key=f"form_vacaciones_fijas_{year_app}", clear_on_submit=False):
                    df_vacaciones_editor = st.data_editor(
                        st.session_state[clave_vacaciones_validas],
                        column_config=columnas_config_vac,
                        disabled=["Rol", "Máx vacaciones"],
                        hide_index=False,
                        use_container_width=True,
                        height=min(620, 120 + 35 * max(1, len(P_tmp))),
                        num_rows="fixed",
                        key=f"tabla_vacaciones_fijas_{year_app}",
                    )

                    aplicar_vacaciones = st.form_submit_button(
                        "✅ Aplicar selección de vacaciones"
                    )

                if aplicar_vacaciones:
                    errores_temporales_vacaciones = []
                    for persona_idx, row in df_vacaciones_editor.iterrows():
                        persona = str(persona_idx).strip()
                        max_vacaciones = int(W_tmp.get(persona, 0))
                        total_marcadas = 0

                        for s in semanas:
                            valor = row.get(f"S{s}", False)
                            if pd.notna(valor) and bool(valor):
                                total_marcadas += 1

                        if total_marcadas > max_vacaciones:
                            errores_temporales_vacaciones.append(
                                f"{persona}: intentó marcar {total_marcadas} semanas, "
                                f"pero solo tiene {max_vacaciones}."
                            )

                    if errores_temporales_vacaciones:
                        st.session_state[clave_mensaje_vacaciones] = (
                            "No se aplicó la selección porque excede las semanas de vacaciones disponibles.\n\n"
                            + "\n".join([f"- {e}" for e in errores_temporales_vacaciones])
                        )
                        st.warning(st.session_state[clave_mensaje_vacaciones])
                    else:
                        st.session_state[clave_vacaciones_validas] = df_vacaciones_editor.copy()
                        st.success("Selección de vacaciones aplicada correctamente.")

                df_vacaciones_valida = st.session_state[clave_vacaciones_validas].reset_index()

                resumen_vacaciones = []
                for _, row in df_vacaciones_valida.iterrows():
                    persona = str(row["Persona"]).strip()
                    max_vacaciones = int(W_tmp.get(persona, 0))
                    semanas_marcadas = []

                    for s in semanas:
                        valor = row.get(f"S{s}", False)
                        if pd.notna(valor) and bool(valor):
                            semanas_marcadas.append(int(s))

                    V_ui[persona] = semanas_marcadas

                    # Validación secundaria de seguridad antes de habilitar el modelo.
                    if len(semanas_marcadas) > max_vacaciones:
                        errores_vacaciones.append(
                            f"{persona}: marcó {len(semanas_marcadas)} semanas, "
                            f"pero solo tiene {max_vacaciones}."
                        )

                    resumen_vacaciones.append({
                        "Persona": persona,
                        "Máx vacaciones": max_vacaciones,
                        "Semanas marcadas": len(semanas_marcadas),
                        "Disponibles restantes": max_vacaciones - len(semanas_marcadas),
                        "Detalle": ", ".join([f"S{s}" for s in semanas_marcadas]),
                    })

                if resumen_vacaciones:
                    st.markdown("**Resumen de vacaciones marcadas**")
                    mostrar_dataframe_persona_fija(pd.DataFrame(resumen_vacaciones))

                if errores_vacaciones:
                    st.error(
                        "Hay personas con más semanas marcadas que las permitidas. "
                        "Corrija la tabla antes de generar el calendario anual.\n\n"
                        + "\n".join([f"- {e}" for e in errores_vacaciones])
                    )

            if st.button(
                "🚀 Generar y guardar calendario anual",
                key="btn_anual",
                disabled=bool(errores_vacaciones),
            ):
                with st.spinner("Calculando calendario anual..."):
                    df_anual, df_resumen_anual = ejecutar_modelo_anual(
                        ruta_base(year_app),
                        year_app,
                        V_ui,
                        dotacion_turnos_min=dotacion_turnos_min_ui,
                        dotacion_turnos_max=dotacion_turnos_max_ui,
                        min_esteriliza_noche=int(min_esteriliza_noche_ui),
                    )

                    with pd.ExcelWriter(ruta_anual(year_app), engine="openpyxl") as writer:
                        df_anual.to_excel(writer, index=False, sheet_name="Calendario")
                        df_resumen_anual.to_excel(writer, index=False, sheet_name="Resumen")
                        # También se guarda con el nombre del modelo anual original.
                        df_resumen_anual.to_excel(writer, index=False, sheet_name="Verificacion")

                    st.success(f"✅ Anual generado y guardado en: {ruta_anual(year_app)}")
                    st.session_state[f"anual_generado_{year_app}"] = True

            if ruta_anual(year_app).exists():
                df_anual_guardado = pd.read_excel(ruta_anual(year_app), sheet_name="Calendario", engine="openpyxl")
                df_resumen_guardado = pd.read_excel(ruta_anual(year_app), sheet_name="Resumen", engine="openpyxl")
                columnas_semana_anual = [
                    c for c in df_anual_guardado.columns
                    if extraer_numero_semana_columna(c) is not None
                ]

                t1, t2, t3 = st.tabs(["📊 Calendario anual", "✏️ Editar anual", "📈 Resumen"])
                with t1:
                    mostrar_calendario_anual_con_meses(df_anual_guardado, year_app)

                with t2:
                    st.caption(
                        "Edite únicamente las semanas del calendario anual. "
                        "El mensual usará esta versión guardada para expandir los turnos por día."
                    )

                    opciones_anual = ["M", "T", "N", "V", "O"]
                    column_config_anual = {}
                    for c in columnas_semana_anual:
                        semana_col = extraer_numero_semana_columna(c)
                        etiqueta_semana = obtener_nombre_mes_semana_anual(year_app, semana_col, abreviado=True)
                        column_config_anual[c] = st.column_config.SelectboxColumn(
                            f"{etiqueta_semana}\nS{semana_col}",
                            options=opciones_anual,
                            required=True,
                            help=f"{obtener_nombre_mes_semana_anual(year_app, semana_col)} - Semana {semana_col}",
                        )

                    if "Persona" in df_anual_guardado.columns:
                        df_anual_editor = df_anual_guardado.copy().set_index("Persona")
                        df_anual_editor.index.name = "Persona"
                    else:
                        df_anual_editor = df_anual_guardado.copy()

                    columnas_bloqueadas_anual = [
                        c for c in df_anual_editor.columns
                        if c not in columnas_semana_anual
                    ]

                    df_anual_editado = st.data_editor(
                        df_anual_editor,
                        use_container_width=True,
                        height=600,
                        disabled=columnas_bloqueadas_anual,
                        column_config=column_config_anual,
                        hide_index=False,
                        num_rows="fixed",
                        key=f"editor_anual_{year_app}",
                    )

                    if "Persona" in df_anual_guardado.columns:
                        df_anual_editado = df_anual_editado.reset_index()

                    errores_anual_editor = []
                    for c in columnas_semana_anual:
                        df_anual_editado[c] = df_anual_editado[c].astype(str).str.strip().str.upper()
                        valores_invalidos = sorted(
                            v for v in df_anual_editado[c].dropna().unique()
                            if str(v).strip().upper() not in opciones_anual
                        )
                        if valores_invalidos:
                            errores_anual_editor.append(
                                f"{c}: valores no permitidos {', '.join(map(str, valores_invalidos))}"
                            )

                    if errores_anual_editor:
                        st.error(
                            "Hay valores no válidos en el anual. Use solo M, T, N, V u O.\n\n"
                            + "\n".join([f"- {e}" for e in errores_anual_editor])
                        )

                    col_guardar_anual, col_descartar_anual = st.columns(2)
                    with col_guardar_anual:
                        if st.button(
                            "💾 Guardar edición del anual",
                            key=f"guardar_edicion_anual_{year_app}",
                            disabled=bool(errores_anual_editor),
                        ):
                            with pd.ExcelWriter(
                                ruta_anual(year_app),
                                engine="openpyxl",
                                mode="a",
                                if_sheet_exists="replace",
                            ) as writer:
                                df_anual_editado.to_excel(writer, sheet_name="Calendario", index=False)
                            st.success("✅ Edición del calendario anual guardada. El mensual usará esta versión actualizada.")
                            st.rerun()

                    with col_descartar_anual:
                        if st.button("↻ Descartar cambios no guardados", key=f"descartar_edicion_anual_{year_app}"):
                            st.rerun()

                with t3:
                    mostrar_dataframe_persona_fija(df_resumen_guardado)

                st.download_button(
                    "📥 Descargar anual guardado",
                    archivo_a_bytes(ruta_anual(year_app)),
                    file_name=f"solucion_final_revisada_{year_app}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        except Exception as e:
            st.error(f"No se pudo preparar el anual: {e}")
    else:
        st.info("Primero cree o importe la base interna en la pestaña Base de datos.")

# =========================================================
# TAB 2: PROGRAMAR MES
# =========================================================
with tab_mensual:
    st.subheader("2️⃣ Programar mes desde el anual guardado")
    mes_app = int(mes_panel)
    st.info(
        f"Mes seleccionado para programar: **{meses[mes_app - 1]} {year_app}**. "
        "Este mes se toma desde el panel lateral."
    )

    col_a, col_b = st.columns(2)
    with col_a:
        st.write("Base interna:", "✅ disponible" if ruta_base(year_app).exists() else "❌ falta")
    with col_b:
        st.write("Anual interno:", "✅ disponible" if ruta_anual(year_app).exists() else "❌ falta")

    ruta_prev = ruta_mensual(*obtener_mes_anterior(year_app, int(mes_app)))
    if ruta_prev.exists():
        try:
            hojas_prev = pd.ExcelFile(ruta_prev, engine="openpyxl").sheet_names
            if "Arrastre_Real_Siguiente_Mes" in hojas_prev:
                st.info(f"Para este mes se usará el arrastre real del mes anterior: {ruta_prev.name}")
            elif "Arrastre_Siguiente_Mes" in hojas_prev:
                st.info(f"Para este mes se usará el arrastre programado del mes anterior: {ruta_prev.name}")
        except Exception:
            st.warning("Existe un archivo del mes anterior, pero no se pudo revisar su arrastre.")
    else:
        st.info("No se encontró archivo del mes anterior. El modelo usará los saldos de la base original.")

    if st.button("🧮 Ejecutar modelo mensual", key="btn_mensual"):
        try:
            with st.spinner("Calculando programación mensual..."):
                resultado = programar_mes(year_app, int(mes_app), ruta_base(year_app), ruta_anual(year_app), carpeta_year(year_app))

            st.success(f"✅ Mensual generado y guardado en: {resultado['ruta_salida']}")
            st.write(f"Desviación total de libres: **{resultado['desviacion_total']:.2f}**")
            st.write(f"Brecha pico-valle de libres: **{resultado['brecha_pico_valle']:.2f}**")
            st.write(f"Arrastre utilizado: **{resultado['hoja_arrastre_utilizada']}**")

            t1, t2, t3, t4 = st.tabs(["📅 Calendario mensual", "📋 Resumen", "➡️ Arrastre", "📊 Libres diarios"])
            with t1:
                mostrar_dataframe_estilado(resultado["df_final"])
            with t2:
                mostrar_dataframe_persona_fija(resultado["df_resumen"])
            with t3:
                mostrar_dataframe_persona_fija(resultado["df_arrastre"])
            with t4:
                st.dataframe(resultado["df_resumen_dias"], use_container_width=True)

            st.download_button(
                "📥 Descargar mensual generado",
                archivo_a_bytes(resultado["ruta_salida"]),
                file_name=resultado["ruta_salida"].name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        except Exception as e:
            st.error(f"No se pudo generar el mensual: {e}")

    if ruta_mensual(year_app, int(mes_app)).exists():
        st.markdown("---")
        st.markdown("**Archivo mensual existente**")
        st.download_button(
            "📥 Descargar mensual existente",
            archivo_a_bytes(ruta_mensual(year_app, int(mes_app))),
            file_name=ruta_mensual(year_app, int(mes_app)).name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_mensual_existente"
        )

# =========================================================
# TAB 3: EDITAR Y CERRAR MES
# =========================================================
with tab_editar:
    st.subheader("3️⃣ Editar salida mensual y cerrar mes real")
    mes_cierre = st.selectbox(
        "Mes a editar/cerrar",
        options=list(range(1, 13)),
        format_func=lambda m: f"{m:02d} - {meses[m - 1]}",
        key="mes_cerrar"
    )

    ruta_mes = ruta_mensual(year_app, int(mes_cierre))
    if not ruta_mes.exists():
        st.info("Primero debe generar el mensual de este mes en la pestaña anterior.")
    else:
        try:
            df_cal = pd.read_excel(ruta_mes, sheet_name="Calendario_Mensual", engine="openpyxl")
            columnas_dias = obtener_columnas_dias(df_cal)

            st.markdown("""
            <div class="custom-card">
                <h3>✏️ Edición del calendario real</h3>
                <p class="soft-text">
                    Edite únicamente las columnas de días. Puede registrar cambios reales como A, INCAP, SSG, H, MC, LE, LM, LP, PCG, PSG,
                    vacaciones, libres o ajustes de turno. Después guarde los cambios y cierre el mes.
                </p>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("Ver simbología", expanded=False):
                st.caption("Use estas siglas en las columnas de días del calendario mensual. La vista previa muestra los mismos colores usados en la tabla editable.")

                simbologia_programacion = pd.DataFrame([
                    {"Símbolo": "M", "Significado": "Mañana / primer turno"},
                    {"Símbolo": "T", "Significado": "Tarde / segundo turno"},
                    {"Símbolo": "N", "Significado": "Noche / tercer turno"},
                    {"Símbolo": "L", "Significado": "Libre"},
                    {"Símbolo": "LB", "Significado": "Libre biológico"},
                    {"Símbolo": "V", "Significado": "Vacaciones"},
                ])

                simbologia_ausencias = pd.DataFrame([
                    {"Símbolo": "A", "Significado": "Ausencia"},
                    {"Símbolo": "INCAP", "Significado": "Incapacidad"},
                    {"Símbolo": "SSG", "Significado": "Suspensión sin goce"},
                    {"Símbolo": "H", "Significado": "Huelga"},
                    {"Símbolo": "MC", "Significado": "Medida cautelar"},
                    {"Símbolo": "LE", "Significado": "Licencia extraordinaria"},
                    {"Símbolo": "LM", "Significado": "Licencia maternidad"},
                    {"Símbolo": "LP", "Significado": "Licencia paternidad"},
                    {"Símbolo": "PCG", "Significado": "Permiso con goce salarial"},
                    {"Símbolo": "PSG", "Significado": "Permiso sin goce salarial"},
                ])

                def preparar_tabla_simbologia(df_simb):
                    df_s = df_simb.copy()
                    df_s.insert(0, "Color", df_s["Símbolo"])
                    return df_s

                col_sim_1, col_sim_2 = st.columns(2)
                with col_sim_1:
                    st.markdown("**Turnos, libres y vacaciones**")
                    df_simb_prog = preparar_tabla_simbologia(simbologia_programacion)
                    st.dataframe(
                        df_simb_prog.style.map(style_horario, subset=["Color", "Símbolo"]),
                        use_container_width=True,
                        hide_index=True,
                        height=280,
                    )
                with col_sim_2:
                    st.markdown("**Ausencias, licencias y permisos**")
                    df_simb_aus = preparar_tabla_simbologia(simbologia_ausencias)
                    st.dataframe(
                        df_simb_aus.style.map(style_horario, subset=["Color", "Símbolo"]),
                        use_container_width=True,
                        hide_index=True,
                        height=390,
                    )

            opciones_estado = ["", "M", "T", "N", "L", "LB", "V", "A", "INCAP", "SSG", "H", "MC", "LE", "LM", "LP", "PCG", "PSG"]
            column_config = {
                c: st.column_config.SelectboxColumn(c, options=opciones_estado, required=False)
                for c in columnas_dias
            }

            if "Persona" in df_cal.columns:
                df_cal_editor = df_cal.copy().set_index("Persona")
                df_cal_editor.index.name = "Persona"
            else:
                df_cal_editor = df_cal.copy()

            columnas_bloqueadas = [c for c in df_cal_editor.columns if c not in columnas_dias]

            df_editado = st.data_editor(
                df_cal_editor,
                use_container_width=True,
                height=600,
                disabled=columnas_bloqueadas,
                column_config=column_config,
                hide_index=False,
                key=f"editor_{year_app}_{mes_cierre}"
            )

            if "Persona" in df_cal.columns:
                df_editado = df_editado.reset_index()

            col_guardar, col_cerrar = st.columns(2)
            with col_guardar:
                if st.button("💾 Guardar edición del calendario mensual", key="guardar_edicion"):
                    with pd.ExcelWriter(
                        ruta_mes,
                        engine="openpyxl",
                        mode="a",
                        if_sheet_exists="replace"
                    ) as writer:
                        df_editado.to_excel(writer, sheet_name="Calendario_Mensual", index=False)
                    st.success("✅ Edición guardada dentro del mismo archivo mensual.")

            with col_cerrar:
                if st.button("🔒 Cerrar mes real y generar arrastre", key="cerrar_real"):
                    with pd.ExcelWriter(
                        ruta_mes,
                        engine="openpyxl",
                        mode="a",
                        if_sheet_exists="replace"
                    ) as writer:
                        df_editado.to_excel(writer, sheet_name="Calendario_Mensual", index=False)

                    resultado_cierre = cerrar_mes_real(year_app, int(mes_cierre), carpeta_year(year_app))
                    st.success("✅ Cierre real guardado. El siguiente mes leerá este arrastre real automáticamente.")

                    t1, t2 = st.tabs(["📊 Cierre real", "➡️ Arrastre real siguiente mes"])
                    with t1:
                        mostrar_dataframe_persona_fija(resultado_cierre["df_cierre_real"])
                    with t2:
                        mostrar_dataframe_persona_fija(resultado_cierre["df_arrastre_real"])

            st.download_button(
                "📥 Descargar mensual actualizado",
                archivo_a_bytes(ruta_mes),
                file_name=ruta_mes.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_mensual_actualizado"
            )

        except Exception as e:
            st.error(f"No se pudo editar/cerrar el mensual: {e}")


# =========================================================
# TAB 4: ASIGNAR FUNCIONES
# =========================================================
with tab_funciones:
    st.subheader("4️⃣ Asignar funciones desde el mensual generado")
    mes_funciones = st.selectbox(
        "Mes para asignar funciones",
        options=list(range(1, 13)),
        format_func=lambda m: f"{m:02d} - {meses[m - 1]}",
        key="mes_funciones"
    )

    ruta_mes_funciones = ruta_mensual(year_app, int(mes_funciones))

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        st.write("Base interna:", "✅ disponible" if ruta_base(year_app).exists() else "❌ falta")
    with col_f2:
        st.write("Mensual interno:", "✅ disponible" if ruta_mes_funciones.exists() else "❌ falta")
    with col_f3:
        st.write("Historial funciones:", "✅ disponible" if ruta_historial_funciones(year_app).exists() else "🆕 se creará")

    st.markdown("""
    <div class="custom-card">
        <h3>🧩 Funcionamiento del modelo de funciones</h3>
        <p class="soft-text">
            Este modelo usa el archivo mensual ya generado para saber quién trabaja cada día y en qué turno.
            Luego toma de la base la elegibilidad por función, incluye Reemplaza como función variable,
            respeta la continuidad del historial y genera la asignación de funciones del mes.
        </p>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("Configurar cantidad de personas por turno y función", expanded=True):
        st.caption(
            "Edite la matriz de dotación diaria requerida. Las filas son los turnos y las columnas son las funciones. "
            "Use 0 cuando una función no se requiera en ese turno. Reemplaza queda como función variable."
        )
        df_w_base = pd.DataFrame(W_DEFECTO).T[FUNCIONES].astype(int)
        df_w_editado = st.data_editor(
            df_w_base,
            use_container_width=True,
            num_rows="fixed",
            column_config={
                f: st.column_config.NumberColumn(
                    f,
                    min_value=0,
                    step=1,
                    format="%d"
                )
                for f in FUNCIONES
            },
            key=f"w_funciones_{year_app}_{mes_funciones}"
        )

        df_w_editado = df_w_editado.fillna(0).astype(int)
        w_ui = {
            turno: {funcion: int(df_w_editado.loc[turno, funcion]) for funcion in FUNCIONES}
            for turno in TURNOS
        }

    if not ruta_mes_funciones.exists():
        st.info("Primero debe generar el mensual de este mes en la pestaña 2.")
    else:
        if st.button("🧩 Ejecutar modelo de funciones", key="btn_funciones"):
            try:
                with st.spinner("Calculando asignación de funciones..."):
                    resultado_funciones = ejecutar_modelo_funciones(year_app, int(mes_funciones), w_ui)

                st.success(f"✅ Funciones generadas y guardadas en: {resultado_funciones['ruta_salida']}")
                st.write(f"Asignaciones regulares: **{resultado_funciones['asignaciones_regulares']}**")
                st.write(f"Faltantes de cobertura fija: **{resultado_funciones['faltantes_cobertura_total']}**")
                st.write(f"Faltantes de reserva crítica para Esteriliza: **{resultado_funciones['faltantes_reserva_total']}**")
                st.write(f"Personas sin asignar: **{resultado_funciones['personas_sin_asignar']}**")
                st.write(f"Pares persona-función elegibles: **{resultado_funciones['pares_elegibles']}**")

                vista_funciones_generada = st.radio(
                    "Vista de funciones generada",
                    ["Mañana", "Tarde", "Noche", "Personas sin asignar", "Rotación usada"],
                    horizontal=True,
                    label_visibility="collapsed",
                    key=f"vista_funciones_generada_{year_app}_{mes_funciones}"
                )

                if vista_funciones_generada == "Mañana":
                    mostrar_dataframe_persona_fija(resultado_funciones["tablas"]["M"])
                elif vista_funciones_generada == "Tarde":
                    mostrar_dataframe_persona_fija(resultado_funciones["tablas"]["T"])
                elif vista_funciones_generada == "Noche":
                    mostrar_dataframe_persona_fija(resultado_funciones["tablas"]["N"])
                elif vista_funciones_generada == "Personas sin asignar":
                    mostrar_dataframe_persona_fija(resultado_funciones["df_sin"])
                else:
                    mostrar_dataframe_persona_fija(resultado_funciones["df_resumen_rotacion"])

                col_down_func, col_down_hist = st.columns(2)
                with col_down_func:
                    st.download_button(
                        "📥 Descargar asignación de funciones",
                        archivo_a_bytes(resultado_funciones["ruta_salida"]),
                        file_name=resultado_funciones["ruta_salida"].name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="download_funciones_generadas"
                    )
                with col_down_hist:
                    if resultado_funciones["ruta_historial"].exists():
                        st.download_button(
                            "📥 Descargar historial de funciones",
                            archivo_a_bytes(resultado_funciones["ruta_historial"]),
                            file_name=resultado_funciones["ruta_historial"].name,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="download_historial_funciones"
                        )
            except Exception as e:
                st.error(f"No se pudo generar la asignación de funciones: {e}")

    ruta_func_existente = ruta_salida_funciones(year_app, int(mes_funciones))
    if ruta_func_existente.exists():
        st.markdown("---")
        st.markdown("**Archivo de funciones existente**")

        try:
            xls_func_existente = pd.ExcelFile(ruta_func_existente, engine="openpyxl")
            hojas_func_existente = xls_func_existente.sheet_names

            mapa_preview_funciones = {
                "Mañana": ["M", "Mañana"],
                "Tarde": ["T", "Tarde"],
                "Noche": ["N", "Noche"],
                "Personas sin asignar": ["Personas_sin_asignar", "Personas sin asignar"],
                "Rotación usada": ["Rotacion_Modelo_Usada", "Rotación usada"],
            }

            vista_funciones_existente = st.radio(
                "Vista de funciones existente",
                list(mapa_preview_funciones.keys()),
                horizontal=True,
                label_visibility="collapsed",
                key=f"vista_funciones_existente_{year_app}_{mes_funciones}"
            )

            posibles_hojas = mapa_preview_funciones[vista_funciones_existente]
            hoja_encontrada = next(
                (h for h in posibles_hojas if h in hojas_func_existente),
                None
            )

            if hoja_encontrada is None:
                st.info(
                    f"No se encontró una hoja para '{vista_funciones_existente}'. "
                    f"Hojas disponibles: {', '.join(hojas_func_existente)}"
                )
            else:
                df_preview_funciones = pd.read_excel(
                    ruta_func_existente,
                    sheet_name=hoja_encontrada,
                    engine="openpyxl"
                )
                mostrar_dataframe_persona_fija(df_preview_funciones)

        except Exception as e:
            st.warning(f"El archivo de funciones existe, pero no se pudo mostrar la vista previa: {e}")

        st.download_button(
            "📥 Descargar funciones existentes",
            archivo_a_bytes(ruta_func_existente),
            file_name=ruta_func_existente.name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_funciones_existente"
        )


# =========================================================
# TAB 5: DASHBOARD
# =========================================================
with tab_dashboard:
    st.subheader("📊 Dashboard de indicadores")
    st.caption(
        "Panel visual para revisar la equidad anual de turnos y los indicadores mensuales "
        "de dotación, libres y ausentismo real posterior al cierre."
    )

    # -----------------------------------------------------
    # 1. Indicador anual: no depende del filtro mensual
    # -----------------------------------------------------
    df_turnos_anual, rutas_anual_dash, semanas_anual_dash, errores_anual_dash = cargar_turnos_anual_dashboard(
        year_app,
        [],
    )
    (
        metricas_anual,
        _,
        df_turnos_pct,
        _,
        _,
        _,
        _,
    ) = construir_metricas_porcentuales_dashboard(
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        pd.DataFrame(),
        df_turnos_anual,
    )

    st.markdown("### Equidad anual de turnos")
    if df_turnos_anual.empty:
        st.info("Todavía no se puede calcular la equidad anual porque no se encontró o no se pudo leer el calendario anual.")
    else:
        col_kpi_1, col_kpi_2, col_kpi_3, col_kpi_4 = st.columns(4)
        with col_kpi_1:
            render_kpi(
                "Equidad global (%)",
                f"{metricas_anual['igualdad_turnos_global']}%",
                "Promedio de M, T y N anual",
            )
        with col_kpi_2:
            render_kpi(
                "Equidad M (%)",
                f"{metricas_anual['igualdad_m']}%",
                f"Promedio anual M: {metricas_anual['promedio_m']}",
            )
        with col_kpi_3:
            render_kpi(
                "Equidad T (%)",
                f"{metricas_anual['igualdad_t']}%",
                f"Promedio anual T: {metricas_anual['promedio_t']}",
            )
        with col_kpi_4:
            render_kpi(
                "Equidad N (%)",
                f"{metricas_anual['igualdad_n']}%",
                f"Promedio anual N: {metricas_anual['promedio_n']} sin 0 noches",
            )


    with st.expander("¿Cómo se calcula el indicador de equidad de turnos?", expanded=False):
        st.markdown("""
        **Equidad anual de turnos**

        Este indicador se calcula únicamente con el calendario anual `solucion_final_revisada.xlsx`. Para cada persona se cuenta la cantidad de semanas asignadas en **M**, **T** y **N** durante todo el año.

        **Fórmula por turno**

        `Equidad (%) = 100 - (desviación promedio absoluta / promedio del turno × 100)`

        La desviación promedio absoluta mide cuánto se alejan las personas, en promedio, del valor esperado del grupo para cada turno.

        **Interpretación**

        - **100%** indica una distribución muy equilibrada.
        - Un porcentaje menor indica mayor diferencia entre las personas.
        - La **equidad global** corresponde al promedio de la equidad de **M**, **T** y **N**.
        - En el turno **N**, las personas con **0 noches** se excluyen del cálculo porque corresponden a personal que no rota en noche.
        """)

    if errores_anual_dash or rutas_anual_dash:
        with st.expander("Ver archivo anual revisado por el dashboard", expanded=False):
            if rutas_anual_dash:
                st.write("Archivo anual leído:", rutas_anual_dash)
            if errores_anual_dash:
                st.markdown("**Observaciones**")
                for err in errores_anual_dash:
                    st.warning(err)

    st.markdown("---")

    # -----------------------------------------------------
    # 2. Filtros mensuales: solo afectan dotación, libres y cierre real
    # -----------------------------------------------------
    meses_disponibles = meses_disponibles_dashboard(year_app)

    st.markdown("### Filtros mensuales")
    if not meses_disponibles:
        st.info(
            "Todavía no hay archivos mensuales o de funciones guardados para construir indicadores mensuales. "
            "Primero genere al menos un mes en Programar mes."
        )
        with st.expander("Ver carpeta revisada por el dashboard"):
            st.write("Carpeta del año:", str(carpeta_year(year_app)))
            st.write("Carpeta de funciones:", str(carpeta_funciones(year_app)))
    else:
        col_filtro_1, col_filtro_2 = st.columns([2, 1])
        with col_filtro_1:
            meses_seleccionados_dash = st.multiselect(
                "Meses a visualizar",
                options=meses_disponibles,
                default=[],
                format_func=lambda m: f"{m:02d} - {meses[m - 1]}",
                help="Seleccione uno o varios meses. Si deja vacío, se muestra todo el histórico disponible.",
                key=f"dashboard_meses_{year_app}"
            )
        with col_filtro_2:
            modo_dashboard = "Histórico completo" if not meses_seleccionados_dash else "Meses filtrados"
            st.markdown(
                f"""
                <div class="dashboard-card">
                    <div class="dashboard-card-title">Modo mensual</div>
                    <div class="dashboard-card-value" style="font-size:1.35rem;">{modo_dashboard}</div>
                    <div class="dashboard-card-note">Año {year_app}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        meses_analisis = meses_seleccionados_dash if meses_seleccionados_dash else meses_disponibles

        st.markdown(
            "".join([
                f"<span class='dashboard-chip'>{m:02d} · {meses[m - 1]}</span>"
                for m in meses_analisis
            ]),
            unsafe_allow_html=True,
        )

        df_estados, df_cierres, df_libres_diarios, rutas_mensuales, errores_mensuales = cargar_calendarios_dashboard(
            year_app,
            meses_analisis,
        )

        with st.expander("Ver archivos mensuales y estado de cierre", expanded=False):
            st.caption(
                "Esta tabla muestra qué archivo mensual revisó el dashboard y si ese archivo ya contiene la hoja de cierre real."
            )
            df_diagnostico_mensual = construir_diagnostico_archivos_mensuales_dashboard(year_app, meses_analisis)
            if not df_diagnostico_mensual.empty:
                st.dataframe(
                    df_diagnostico_mensual,
                    use_container_width=True,
                    hide_index=True,
                    height=min(420, 80 + 36 * len(df_diagnostico_mensual)),
                )
            else:
                st.write("No hay archivos mensuales para revisar.")

            observaciones_mensuales = [
                obs for obs in errores_mensuales
                if "error" in str(obs).lower()
                or "no se pudo" in str(obs).lower()
                or "no se reconocieron" in str(obs).lower()
            ]
            if observaciones_mensuales:
                st.markdown("**Observaciones de lectura**")
                for obs in observaciones_mensuales:
                    st.warning(obs)

        # -------------------------------------------------
        # 2.1 Consistencia mensual: dotación y libres
        # -------------------------------------------------
        st.markdown("### Consistencia mensual de dotación y libres")
        st.caption(
            "Estos indicadores se calculan desde los calendarios mensuales seleccionados. "
            "Para cada día se cuenta la dotación en M, T, N y la cantidad de libres L + LB."
        )

        df_cobertura_diaria, _ = construir_cobertura_y_libres_mensual_dashboard(
            df_estados,
            df_libres_diarios,
        )

        if df_cobertura_diaria.empty:
            st.info("No hay datos mensuales suficientes para calcular dotación diaria ni distribución de libres.")
        else:
            df_cobertura_vista = df_cobertura_diaria.copy()
            for col_num in ["M", "T", "N", "Total M/T/N", "Libres", "L", "LB"]:
                if col_num in df_cobertura_vista.columns:
                    df_cobertura_vista[col_num] = pd.to_numeric(df_cobertura_vista[col_num], errors="coerce").fillna(0)

            total_dias_mensual = int(df_cobertura_vista[["Mes", "Día"]].drop_duplicates().shape[0])
            df_consistencia_global, df_consistencia_por_mes, df_matriz_diaria = construir_indicadores_consistencia_mensual_dashboard(df_cobertura_vista)

            def valor_resumen(nombre_indicador, columna):
                if df_consistencia_global.empty:
                    return 0
                fila = df_consistencia_global[df_consistencia_global["Indicador"] == nombre_indicador]
                if fila.empty or columna not in fila.columns:
                    return 0
                return fila.iloc[0][columna]

            prom_m_diario = valor_resumen("Dotación M", "Promedio diario")
            prom_t_diario = valor_resumen("Dotación T", "Promedio diario")
            prom_n_diario = valor_resumen("Dotación N", "Promedio diario")
            prom_libres_diario = valor_resumen("Libres L + LB", "Promedio diario")

            cons_m = valor_resumen("Dotación M", "Consistencia (%)")
            cons_t = valor_resumen("Dotación T", "Consistencia (%)")
            cons_n = valor_resumen("Dotación N", "Consistencia (%)")
            cons_libres = valor_resumen("Libres L + LB", "Consistencia (%)")

            brecha_m = valor_resumen("Dotación M", "Brecha")
            brecha_t = valor_resumen("Dotación T", "Brecha")
            brecha_n = valor_resumen("Dotación N", "Brecha")
            brecha_libres = valor_resumen("Libres L + LB", "Brecha")

            min_m = valor_resumen("Dotación M", "Mínimo")
            max_m = valor_resumen("Dotación M", "Máximo")
            min_t = valor_resumen("Dotación T", "Mínimo")
            max_t = valor_resumen("Dotación T", "Máximo")
            min_n = valor_resumen("Dotación N", "Mínimo")
            max_n = valor_resumen("Dotación N", "Máximo")
            min_libres = valor_resumen("Libres L + LB", "Mínimo")
            max_libres = valor_resumen("Libres L + LB", "Máximo")

            st.caption(f"Días evaluados en el período mensual seleccionado: {total_dias_mensual}")

            col_prom_1, col_prom_2, col_prom_3, col_prom_4 = st.columns(4)
            with col_prom_1:
                render_kpi("Promedio dotación M", prom_m_diario, "Personas en mañana por día")
            with col_prom_2:
                render_kpi("Promedio dotación T", prom_t_diario, "Personas en tarde por día")
            with col_prom_3:
                render_kpi("Promedio dotación N", prom_n_diario, "Personas en noche por día")
            with col_prom_4:
                render_kpi("Promedio dotación libres", prom_libres_diario, "L + LB por día")

            col_cons_1, col_cons_2, col_cons_3, col_cons_4 = st.columns(4)
            with col_cons_1:
                render_kpi("Consistencia M (%)", f"{cons_m}%", "Qué tan estable fue M")
            with col_cons_2:
                render_kpi("Consistencia T (%)", f"{cons_t}%", "Qué tan estable fue T")
            with col_cons_3:
                render_kpi("Consistencia N (%)", f"{cons_n}%", "Qué tan estable fue N")
            with col_cons_4:
                render_kpi("Consistencia libres (%)", f"{cons_libres}%", "Qué tan estable fue L + LB")

            st.markdown('<div class="dashboard-inline-title">Brechas diarias</div>', unsafe_allow_html=True)
            col_brecha_1, col_brecha_2, col_brecha_3, col_brecha_4 = st.columns(4)
            with col_brecha_1:
                render_kpi("Brecha dotación M", brecha_m, f"Mín–máx diario: {min_m}–{max_m}")
            with col_brecha_2:
                render_kpi("Brecha dotación T", brecha_t, f"Mín–máx diario: {min_t}–{max_t}")
            with col_brecha_3:
                render_kpi("Brecha dotación N", brecha_n, f"Mín–máx diario: {min_n}–{max_n}")
            with col_brecha_4:
                render_kpi("Brecha dotación libres", brecha_libres, f"Mín–máx diario: {min_libres}–{max_libres}")

            with st.expander("Ver detalle diario tipo matriz", expanded=False):
                st.caption("Cada columna representa un día evaluado. Al final se agregan promedio, desviación, consistencia, mínimo, máximo y brecha.")
                st.dataframe(
                    df_matriz_diaria,
                    use_container_width=True,
                    hide_index=True,
                    height=260,
                )

            st.markdown('<div class="dashboard-inline-title">Gráficos mensuales</div>', unsafe_allow_html=True)

            df_persona_mensual = contar_estados_por_persona(df_estados)
            if not df_persona_mensual.empty:
                st.markdown("**Días trabajados por persona**")
                vista_dias = st.radio(
                    "Mostrar",
                    options=["10 más altos", "10 más bajos", "Todos"],
                    horizontal=True,
                    key="vista_dias_trabajados_dashboard",
                    label_visibility="collapsed",
                )
                df_graf_dias_persona = df_persona_mensual[["Persona", "Días trabajados"]].copy()
                if vista_dias == "10 más altos":
                    df_graf_dias_persona = df_graf_dias_persona.sort_values(by="Días trabajados", ascending=False).head(10)
                    titulo_dias = "Días trabajados por persona · 10 más altos"
                elif vista_dias == "10 más bajos":
                    df_graf_dias_persona = df_graf_dias_persona.sort_values(by="Días trabajados", ascending=True).head(10)
                    titulo_dias = "Días trabajados por persona · 10 más bajos"
                else:
                    df_graf_dias_persona = df_graf_dias_persona.sort_values(by="Días trabajados", ascending=False)
                    titulo_dias = "Días trabajados por persona · todos"

                altura_dias = max(320, min(850, 34 * len(df_graf_dias_persona)))
                chart_dias_persona = (
                    alt.Chart(df_graf_dias_persona)
                    .mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5)
                    .encode(
                        y=alt.Y("Persona:N", sort="-x", title=None, axis=alt.Axis(labelLimit=240)),
                        x=alt.X("Días trabajados:Q", title="Días trabajados"),
                        color=alt.Color(
                            "Días trabajados:Q",
                            scale=alt.Scale(range=PALETA_GRAFICOS_AZUL),
                            legend=None,
                        ),
                        tooltip=["Persona", alt.Tooltip("Días trabajados:Q", format=",.0f")],
                    )
                    .properties(title=titulo_dias, height=altura_dias)
                    .configure_title(
                        font="Georgia",
                        fontSize=17,
                        fontWeight="bold",
                        color="#20384a",
                        anchor="start",
                    )
                    .configure_axis(
                        labelFont="Georgia",
                        titleFont="Georgia",
                        labelColor="#64748b",
                        titleColor="#475569",
                    )
                )
                st.altair_chart(chart_dias_persona, use_container_width=True)
            else:
                st.info("No hay datos suficientes para graficar los días trabajados por persona.")

            df_estados_general = (
                df_estados[df_estados["Estado"].notna()].copy()
                if not df_estados.empty else pd.DataFrame()
            )
            if not df_estados_general.empty:
                df_estados_general["Estado"] = df_estados_general["Estado"].astype(str).str.strip().str.upper()
                df_graf_estados = (
                    df_estados_general.groupby("Estado")
                    .size()
                    .reset_index(name="Cantidad")
                    .sort_values(by="Cantidad", ascending=False)
                )
                df_graf_estados["Etiqueta"] = df_graf_estados["Estado"].apply(lambda x: f"{x} · {NOMBRES_ESTADOS.get(x, x)}")
                dominio_estados = df_graf_estados["Estado"].tolist()
                rango_estados = [COLORES_ESTADOS_DASHBOARD.get(e, "#0b5f8f") for e in dominio_estados]
                altura_estados = max(420, min(900, 34 * len(df_graf_estados)))
                chart_estados = (
                    alt.Chart(df_graf_estados)
                    .mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5)
                    .encode(
                        y=alt.Y("Etiqueta:N", sort="-x", title=None, axis=alt.Axis(labelLimit=320)),
                        x=alt.X("Cantidad:Q", title="Registros persona-día"),
                        color=alt.Color(
                            "Estado:N",
                            scale=alt.Scale(domain=dominio_estados, range=rango_estados),
                            legend=None,
                        ),
                        tooltip=["Estado", "Etiqueta", alt.Tooltip("Cantidad:Q", format=",.0f")],
                    )
                    .properties(title="Distribución general de estados", height=altura_estados)
                    .configure_title(
                        font="Georgia",
                        fontSize=17,
                        fontWeight="bold",
                        color="#20384a",
                        anchor="start",
                    )
                    .configure_axis(
                        labelFont="Georgia",
                        titleFont="Georgia",
                        labelColor="#64748b",
                        titleColor="#475569",
                    )
                )
                st.altair_chart(chart_estados, use_container_width=True)
            else:
                st.info("No hay datos suficientes para graficar la distribución general de estados.")

            with st.expander("¿Cómo se calculan los indicadores mensuales?", expanded=False):
                st.markdown("""
                **Promedio dotación M, T y N**

                Se calcula desde la hoja `Calendario_Mensual`. Para cada día se cuenta cuántas personas regulares quedaron programadas en cada turno: **M**, **T** y **N**. Luego se obtiene el promedio diario del período seleccionado.

                **Promedio dotación libres**

                Se calcula como la cantidad diaria de personas con **L + LB**. Incluye libres ordinarios y libres biológicos. Luego se obtiene el promedio diario del período seleccionado.

                **Consistencia M, T, N y libres (%)**

                Mide qué tan estable fue la dotación diaria respecto al promedio del período seleccionado.

                `Consistencia (%) = 100 - (desviación promedio absoluta / promedio diario × 100)`

                Un valor cercano a **100%** indica que la cantidad diaria se mantuvo muy parecida al promedio. Un valor menor indica mayor variación entre días.

                **Brecha dotación M, T, N y libres**

                Corresponde a la diferencia entre el día con mayor cantidad y el día con menor cantidad para cada indicador.

                `Brecha = máximo diario - mínimo diario`

                Estos cálculos son flexibles: si se selecciona un mes, analizan ese mes; si se seleccionan varios meses, analizan esos meses juntos; si no se selecciona ninguno, utilizan todo el histórico mensual disponible.
                """)

        # -------------------------------------------------
        # 2.2 Ausentismo: solo cuando existe cierre real
        # -------------------------------------------------
        st.markdown("---")
        st.markdown("### Indicadores del cierre real del mes")
        st.caption(
            "Estos indicadores se calculan únicamente cuando el mes fue cerrado y existe la hoja Cierre_Real_Mes."
        )

        metricas_aus, df_aus_tipo, df_aus_detalle_estado, df_aus_persona = construir_ausentismo_cierre_dashboard(df_cierres)

        if df_cierres.empty:
            st.info("Todavía no hay meses cerrados en el período seleccionado. Cuando cierre un mes, aquí aparecerán los indicadores del cierre real.")
        else:
            col_aus_1, col_aus_2, col_aus_3 = st.columns(3)
            with col_aus_1:
                render_kpi(
                    "Ausentismo (%)",
                    f"{metricas_aus['ausencias_a_pct']}%",
                    f"{metricas_aus['ausencias_a']} registros A"
                )
            with col_aus_2:
                render_kpi(
                    "Incapacidades (%)",
                    f"{metricas_aus['incapacidades_pct']}%",
                    f"{metricas_aus['incapacidades']} registros INCAP"
                )
            with col_aus_3:
                render_kpi(
                    "Absentismo (%)",
                    f"{metricas_aus['otros_absentismo_pct']}%",
                    f"{metricas_aus['otros_absentismo']} permisos, licencias u otros"
                )

            if not df_aus_tipo.empty:
                df_graf_cierre = df_aus_tipo.copy()
                df_graf_cierre["Indicador"] = pd.Categorical(
                    df_graf_cierre["Indicador"],
                    categories=["Ausentismo", "Incapacidades", "Absentismo"],
                    ordered=True,
                )
                df_graf_cierre = df_graf_cierre.sort_values("Indicador")
                chart_cierre = (
                    alt.Chart(df_graf_cierre)
                    .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
                    .encode(
                        x=alt.X("Indicador:N", title=None),
                        y=alt.Y("Porcentaje:Q", title="Porcentaje (%)"),
                        color=alt.Color(
                            "Indicador:N",
                            scale=alt.Scale(
                                domain=["Ausentismo", "Incapacidades", "Absentismo"],
                                range=["#12263a", "#4f6f8d", "#9fb7cf"],
                            ),
                            legend=None,
                        ),
                        tooltip=["Indicador", "Cantidad", alt.Tooltip("Porcentaje:Q", format=",.2f")],
                    )
                    .properties(title="Distribución porcentual del cierre real", height=320)
                    .configure_title(
                        font="Georgia",
                        fontSize=17,
                        fontWeight="bold",
                        color="#20384a",
                        anchor="start",
                    )
                    .configure_axis(
                        labelFont="Georgia",
                        titleFont="Georgia",
                        labelColor="#64748b",
                        titleColor="#475569",
                    )
                )
                st.altair_chart(chart_cierre, use_container_width=True)

            with st.expander("Ver detalle del cierre real", expanded=False):
                st.markdown(
                    f"**Base operativa del período:** {metricas_aus['base_operativa']} registros "
                    f"({metricas_aus['dias_actividad_reales']} días con actividad real + "
                    f"{metricas_aus['total_no_trabajado']} registros no trabajados)."
                )
                if not df_aus_tipo.empty:
                    st.markdown("**Resumen por indicador**")
                    st.dataframe(df_aus_tipo, use_container_width=True, hide_index=True)
                if not df_aus_detalle_estado.empty:
                    st.markdown("**Detalle por estado del cierre real**")
                    st.dataframe(df_aus_detalle_estado, use_container_width=True, hide_index=True)
                if not df_aus_persona.empty:
                    st.markdown("**Detalle por persona**")
                    st.dataframe(df_aus_persona, use_container_width=True, hide_index=True)

            with st.expander("¿Cómo se calculan los indicadores del cierre real?", expanded=False):
                st.markdown("""
                El cálculo se realiza con la hoja `Cierre_Real_Mes`, generada al cerrar el mes real.

                **Ausentismo (%)**

                Mide únicamente los registros marcados con `A`.

                `Ausentismo (%) = A / (días con actividad reales + A + INCAP + absentismo) × 100`

                **Incapacidades (%)**

                Mide únicamente los registros marcados como `INCAP`.

                `Incapacidades (%) = INCAP / (días con actividad reales + A + INCAP + absentismo) × 100`

                **Absentismo (%)**

                Agrupa los demás estados del cierre real: `SSG`, `H`, `MC`, `LE`, `LM`, `LP`, `PCG` y `PSG`.

                `Absentismo (%) = absentismo / (días con actividad reales + A + INCAP + absentismo) × 100`

                La gráfica se muestra segregada por estado para identificar cuáles códigos explican el porcentaje total.
                """)


        # -------------------------------------------------
        # 2.3 Rotación de funciones
        # -------------------------------------------------
        st.markdown("---")
        st.markdown("### Indicadores de rotación de funciones")
        st.caption(
            "Estos indicadores se calculan con los archivos de asignación de funciones del período seleccionado. "
            "La unidad de conteo es persona-semana-función, no persona-día-función."
        )

        df_funciones_dash, df_sin_func_dash, df_rotacion_dash, rutas_funciones_dash, errores_funciones_dash = cargar_funciones_dashboard(
            year_app,
            meses_analisis,
        )

        if df_funciones_dash.empty and df_sin_func_dash.empty and df_rotacion_dash.empty:
            st.info("Todavía no hay archivos de funciones para el período seleccionado. Cuando ejecute la asignación de funciones, aquí aparecerán los indicadores de rotación.")
        else:
            metricas_fun, df_fun_persona, df_fun_resumen = construir_indicadores_funciones_dashboard(
                df_funciones_dash,
                df_sin_func_dash,
                df_rotacion_dash,
            )

            col_fun_1, col_fun_2, col_fun_3 = st.columns(3)
            with col_fun_1:
                render_kpi(
                    "Rotación funcional (%)",
                    f"{metricas_fun['rotacion_funcional_pct']}%",
                    metricas_fun["fuente_rotacion"]
                )
            with col_fun_2:
                render_kpi(
                    "Funciones distintas promedio",
                    metricas_fun["funciones_distintas_promedio"],
                    "Variedad funcional promedio por persona"
                )
            with col_fun_3:
                render_kpi(
                    "Repetición de funciones",
                    metricas_fun["repeticion_promedio"],
                    "Promedio de repeticiones por persona"
                )

            col_fun_4, col_fun_5 = st.columns(2)
            with col_fun_4:
                render_kpi(
                    "Balance de carga funcional (%)",
                    f"{metricas_fun['equilibrio_asignaciones_pct']}%",
                    "Qué tan pareja fue la carga entre personas"
                )
            with col_fun_5:
                render_kpi(
                    "Sin función asignada (%)",
                    f"{metricas_fun['sin_asignar_pct']}%",
                    f"{metricas_fun['sin_asignar']} registros sin asignar"
                )

            col_graf_fun_1, col_graf_fun_2 = st.columns(2)
            with col_graf_fun_1:
                if not df_fun_resumen.empty:
                    df_carga_funcion = df_fun_resumen.rename(columns={"Asignaciones": "Carga funcional"}).copy()
                    grafico_barras(
                        df_carga_funcion,
                        "Función",
                        "Carga funcional",
                        "Carga funcional por función",
                        horizontal=True,
                        altura=330,
                        y_title="Cantidad",
                    )
                else:
                    st.info("No hay datos suficientes para graficar la carga por función.")
            with col_graf_fun_2:
                if not df_fun_persona.empty:
                    st.markdown("**Rotación funcional total por persona**")
                    vista_rot = st.radio(
                        "Mostrar rotación",
                        options=["10 más altos", "10 más bajos", "Todos"],
                        horizontal=True,
                        key="vista_rotacion_funcional_dashboard",
                        label_visibility="collapsed",
                    )
                    df_rotacion_persona = df_fun_persona[["Persona", "Rotación del período (%)"]].copy()
                    if vista_rot == "10 más altos":
                        df_rotacion_persona = df_rotacion_persona.sort_values(by="Rotación del período (%)", ascending=False).head(10)
                        titulo_rot = "Rotación funcional total por persona · 10 más altos"
                    elif vista_rot == "10 más bajos":
                        df_rotacion_persona = df_rotacion_persona.sort_values(by="Rotación del período (%)", ascending=True).head(10)
                        titulo_rot = "Rotación funcional total por persona · 10 más bajos"
                    else:
                        df_rotacion_persona = df_rotacion_persona.sort_values(by="Rotación del período (%)", ascending=False)
                        titulo_rot = "Rotación funcional total por persona · todos"

                    altura_rot = max(320, min(850, 34 * len(df_rotacion_persona)))
                    chart_rot = (
                        alt.Chart(df_rotacion_persona)
                        .mark_bar(cornerRadiusTopRight=5, cornerRadiusBottomRight=5)
                        .encode(
                            y=alt.Y("Persona:N", sort="-x", title=None, axis=alt.Axis(labelLimit=240)),
                            x=alt.X("Rotación del período (%):Q", title="Rotación (%)"),
                            color=alt.Color(
                                "Rotación del período (%):Q",
                                scale=alt.Scale(range=PALETA_GRAFICOS_AZUL),
                                legend=None,
                            ),
                            tooltip=["Persona", alt.Tooltip("Rotación del período (%):Q", format=",.2f")],
                        )
                        .properties(title=titulo_rot, height=altura_rot)
                        .configure_title(
                            font="Georgia",
                            fontSize=17,
                            fontWeight="bold",
                            color="#20384a",
                            anchor="start",
                        )
                        .configure_axis(
                            labelFont="Georgia",
                            titleFont="Georgia",
                            labelColor="#64748b",
                            titleColor="#475569",
                        )
                    )
                    st.altair_chart(chart_rot, use_container_width=True)
                else:
                    st.info("No hay datos suficientes para graficar la rotación por persona.")

            with st.expander("¿Cómo se calculan los indicadores de rotación de funciones?", expanded=False):
                st.markdown("""
                La fila técnica `LIBRE` se excluye de estos indicadores porque no representa una persona real. En funciones, `LIBRE` indica que la persona originalmente asociada a esa función estaba libre y que la cobertura debe ser asumida por otra persona mediante reemplazo.

                La unidad interna de conteo es **persona-semana-función**. No se cuenta cada día por separado, porque la función se asigna semanalmente y puede repetirse en varias columnas del archivo.

                **Carga funcional por función**

                Muestra cuántas asignaciones recibió cada función durante el período seleccionado. Para cada función se cuentan las combinaciones únicas de persona, semana y función.

                `Carga funcional por función = conteo de asignaciones únicas persona-semana-función para cada función`

                Por ejemplo, si una persona aparece varios días de la misma semana en **Esteriliza**, eso cuenta como **1 asignación funcional**, no como varios días. Este gráfico permite identificar qué funciones concentran más asignaciones dentro del período analizado.

                **Rotación funcional (%)**

                Mide qué tanto ha rotado el personal entre las funciones que puede realizar. Cuando existe la hoja `Rotacion_Modelo_Usada`, se usa el porcentaje calculado por el modelo:

                `Rotación funcional (%) = funciones visitadas / funciones elegibles × 100`

                Si esa hoja no está disponible, se calcula con las asignaciones del período:

                `Rotación funcional (%) = funciones distintas asignadas / asignaciones totales de la persona × 100`

                **Funciones distintas promedio**

                Indica cuántas funciones diferentes recibió cada persona, en promedio, durante el período analizado.

                **Repetición de funciones**

                Indica cuántas repeticiones de funciones tuvo cada persona, en promedio, dentro del período. Un valor alto puede sugerir poca rotación.

                `Repetición de funciones = total de funciones recibidas por persona - funciones distintas`

                **Balance de carga funcional (%)**

                Mide si la carga de asignaciones funcionales quedó distribuida de forma parecida entre las personas.

                `Balance de carga funcional (%) = 100 - (desviación promedio absoluta / promedio de asignaciones × 100)`

                **Sin función asignada (%)**

                Mide el peso de los registros que quedaron sin función respecto al total de registros revisados.
                """)

            with st.expander("Ver detalle de rotación de funciones", expanded=False):
                st.markdown("**Archivos de funciones leídos**")
                if rutas_funciones_dash:
                    st.write(rutas_funciones_dash)
                else:
                    st.write("No se leyeron archivos de funciones.")

                if errores_funciones_dash:
                    st.markdown("**Observaciones de lectura**")
                    for err in errores_funciones_dash:
                        st.warning(err)

                if not df_fun_persona.empty:
                    st.markdown("**Detalle por persona**")
                    st.caption("La fila técnica LIBRE no se incluye porque no corresponde a una persona real.")
                    df_fun_persona_mostrar = df_fun_persona.drop(columns=["Asignaciones"], errors="ignore").rename(columns={
                        "Repeticiones": "Repetición de funciones",
                        "Rotación del período (%)": "Rotación funcional (%)",
                    })
                    st.dataframe(df_fun_persona_mostrar, use_container_width=True, hide_index=True)

                if not df_fun_resumen.empty:
                    st.markdown("**Carga por función**")
                    df_fun_resumen_mostrar = df_fun_resumen.rename(columns={
                        "Asignaciones": "Carga funcional"
                    })
                    st.dataframe(df_fun_resumen_mostrar, use_container_width=True, hide_index=True)

                if df_sin_func_dash is not None and not df_sin_func_dash.empty:
                    st.markdown("**Personas sin función asignada**")
                    st.dataframe(df_sin_func_dash, use_container_width=True, hide_index=True)

# =========================================================
# TAB 6: ARCHIVOS GUARDADOS
# =========================================================
with tab_archivos:
    st.subheader("📁 Archivos guardados internamente")
    carpeta = carpeta_year(year_app)
    archivos = sorted(carpeta.rglob("*.xlsx"))

    if not archivos:
        st.info("Todavía no hay archivos guardados para este año.")
    else:
        resumen_archivos = []
        for f in archivos:
            resumen_archivos.append({
                "Archivo": str(f.relative_to(carpeta)),
                "Tamaño KB": round(f.stat().st_size / 1024, 2),
                "Ruta interna": str(f)
            })
        st.dataframe(pd.DataFrame(resumen_archivos), use_container_width=True)

        archivo_elegido = st.selectbox("Seleccionar archivo para descargar o eliminar", options=[str(f.relative_to(carpeta)) for f in archivos])
        ruta_elegida = carpeta / archivo_elegido

        col_descargar, col_eliminar = st.columns(2)

        with col_descargar:
            st.download_button(
                "📥 Descargar archivo seleccionado",
                archivo_a_bytes(ruta_elegida),
                file_name=ruta_elegida.name,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_archivo_select"
            )

        with col_eliminar:
            st.warning("Eliminar un archivo lo borra de la carpeta interna de la aplicación.")
            confirmar_eliminacion = st.checkbox(
                f"Confirmo que quiero eliminar: {archivo_elegido}",
                key=f"confirmar_eliminar_{year_app}_{archivo_elegido}"
            )

            if st.button(
                "🗑️ Eliminar archivo seleccionado",
                key=f"btn_eliminar_{year_app}_{archivo_elegido}",
                disabled=not confirmar_eliminacion
            ):
                try:
                    ruta_elegida.unlink()
                    st.success(f"✅ Archivo eliminado: {archivo_elegido}")
                    st.rerun()
                except Exception as e:
                    st.error(f"No se pudo eliminar el archivo: {e}")
