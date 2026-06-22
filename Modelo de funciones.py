"""
Modelo de asignación de funciones CEYE
"""

import os
import re
import calendar
from datetime import datetime, timedelta, date
from collections import defaultdict

import pandas as pd
import pulp


# =========================================================
# 1. RUTAS DEL REPOSITORIO
# =========================================================
DIRECTORIO_ACTUAL = os.path.dirname(os.path.abspath(__file__))
RUTA_BASE = os.path.join(DIRECTORIO_ACTUAL, "Base de Datos", "BaseDatos.xlsx")
CARPETA_SALIDA = os.path.join(DIRECTORIO_ACTUAL, "Resultados")
RUTA_HISTORIAL = os.path.join(CARPETA_SALIDA, "historial_asignaciones.xlsx")


def obtener_ruta_mensual(anio_usuario, mes_usuario):
    return os.path.join(CARPETA_SALIDA, f"mensual_{anio_usuario}_{mes_usuario:02d}.xlsx")


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
    return datetime.fromisocalendar(int(iso_year), int(iso_week), 1)


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
    fecha_cursor = obtener_monday_iso(primer_iso_year, primera_semana) - timedelta(weeks=1)

    while len(semanas_horizonte) < HORIZONTE_EQUIDAD:
        iso_year, semana_iso, _ = fecha_cursor.isocalendar()
        key = (iso_year, semana_iso)

        if key not in semanas_horizonte:
            semanas_horizonte.append(key)

        fecha_cursor -= timedelta(weeks=1)

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

    for hoja in ["Asistentes", "Saldos"]:
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
    df = pd.read_excel(ruta_base, sheet_name="Asistentes", engine="openpyxl", header=0)
    df.columns = df.columns.str.strip()

    col_persona = df.columns[0]
    col_rol = df.columns[1]

    asistentes_2 = set()

    for _, row in df.iterrows():
        persona = str(row[col_persona]).strip()

        if pd.isna(row[col_persona]) or persona == "" or persona == "nan":
            continue

        if row[col_rol] == 2 or row[col_rol] == "2":
            asistentes_2.add(persona)

    return asistentes_2


def cargar_roles_personas(ruta_base):
    roles = {}

    for hoja in ["Asistentes", "Saldos"]:
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
        fecha = datetime(anio, mes, dia_ejemplo)
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


# =========================================================
# 7. PROGRAMA PRINCIPAL
# =========================================================
def main():
    print("MODELO DE FUNCIONES - REPOSITORIO - REEMPLAZA VARIABLE")
    print(f"Ruta base esperada: {RUTA_BASE}")
    print(f"Carpeta resultados esperada: {CARPETA_SALIDA}")

    year = int(input("Año: "))
    month = int(input("Mes: "))
    num_dias = calendar.monthrange(year, month)[1]

    if not os.path.exists(RUTA_BASE):
        raise FileNotFoundError(
            f"No se encontró BaseDatos.xlsx en:\n{RUTA_BASE}\n"
            "Coloque el archivo dentro de la carpeta 'Base de Datos' del repositorio."
        )

    ruta_mensual = obtener_ruta_mensual(year, month)

    if not os.path.exists(ruta_mensual):
        print(f"No existe {ruta_mensual}. Ejecute primero el modelo mensual.")
        return

    print("Cargando asistentes 2...")
    asistentes_2 = cargar_asistentes_2(RUTA_BASE)
    roles = cargar_roles_personas(RUTA_BASE)

    print(f"Asistentes 2 identificados: {len(asistentes_2)}")
    print(f"Roles cargados: {len(roles)}")

    print("Cargando disponibilidad desde el modelo mensual...")
    T_pst_reg, dias_por_semana_reg, turno_por_dia_reg = cargar_disponibilidad(
        year,
        month,
        ruta_mensual,
        num_dias
    )

    print(f"Regulares leídos: {len(T_pst_reg)} persona-semana")

    if not T_pst_reg:
        print("No hay personas regulares con turnos M/T/N en este mes.")
        return

    print("Cargando conjunto de elegibilidad A_pf...")
    A_pf = cargar_conjunto_A_pf(RUTA_BASE)

    print(f"Total pares (persona, función) elegibles: {len(A_pf)}")

    print("Resumen de compatibilidades por función:")
    for f in FUNCIONES:
        cant = sum(1 for (p, ff) in A_pf if ff == f)
        print(f"  {f}: {cant} personas")

    print("Cargando parámetros w_{tf}...")
    w = obtener_parametro_w_usuario()

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

    print(f"Asignaciones regulares generadas: {len(asign_reg)}")

    guardar_asignaciones_historial(
        asign_reg,
        year,
        month,
        dias_por_semana_reg_out
    )

    tablas = construir_tablas(
        asign_reg,
        dias_por_semana_reg_out,
        turno_por_dia_reg_out,
        w,
        num_dias
    )

    df_sin = pd.DataFrame(
        sin_asignar,
        columns=["Persona", "Día", "Turno", "Tipo"]
    )

    os.makedirs(CARPETA_SALIDA, exist_ok=True)

    salida = os.path.join(
        CARPETA_SALIDA,
        f"asignacion_funciones_{year}_{month:02d}.xlsx"
    )

    with pd.ExcelWriter(salida, engine="openpyxl") as writer:
        for turno, df in tablas.items():
            df.to_excel(writer, sheet_name=turno)

        df_sin.to_excel(writer, sheet_name="Personas_sin_asignar", index=False)
        df_resumen_rotacion.to_excel(writer, sheet_name="Rotacion_Modelo_Usada", index=False)

    print(f"\nArchivo guardado: {salida}")
    print(f"Faltantes diarios totales de cobertura fija: {faltantes_cobertura_total}")
    print(f"Faltantes de reserva crítica para Esteriliza: {faltantes_reserva_total}")
    print(f"Personas sin asignar: {len(sin_asignar)}")
    print("Las celdas no cubiertas en funciones fijas aparecen como 'LIBRE'.")
    print("Reemplaza aparece como función variable sin mínimo ni máximo general.")
    print("La reserva crítica procura dejar en Reemplaza a alguien que pueda cubrir Esteriliza.")
    print("Revise la hoja 'Rotacion_Modelo_Usada' para validar funciones visitadas.")
    print("Revise historial_asignaciones.xlsx para la ventana móvil de 10 semanas.")


if __name__ == "__main__":
    main()