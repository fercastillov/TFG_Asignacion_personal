import os
import math
import pandas as pd
import pulp
import calendar
from datetime import date

# =========================================================
# CONFIGURACIÓN GENERAL
# =========================================================
DIRECTORIO_ACTUAL = os.path.dirname(os.path.abspath(__file__))
RUTA_BASE = os.path.join(DIRECTORIO_ACTUAL, "Base de Datos", "BaseDatos.xlsx")
RUTA_ANUAL = os.path.join(DIRECTORIO_ACTUAL, "Resultados", "solucion_final_revisada.xlsx")
CARPETA_SALIDA = os.path.join(DIRECTORIO_ACTUAL, "Resultados")

# Si True, ciertos permisos siguen acumulando en el conteo
AJ_CUENTA_COMO_TRABAJO = True

EPS = 1e-6

# Límites de resolución 
TIEMPO_MAX_ETAPA_1 = 300 
TIEMPO_MAX_ETAPA_2 = 180      
TIEMPO_MAX_ETAPA_3 = 120 
GAP_REL_ETAPA_1 = 0.05      
GAP_REL_ETAPA_2 = 0.05      
GAP_REL_ETAPA_3 = 0.05


# =========================================================
# FUNCIONES AUXILIARES
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


def nombre_archivo_mensual(year, month):
    return f"mensual_{year}_{month:02d}.xlsx"


def obtener_columnas_dias(df):
    cols = []
    for c in df.columns:
        s = str(c).strip()
        if s.startswith("D") and s[1:].isdigit():
            cols.append(s)
    return sorted(cols, key=lambda x: int(x[1:]))


def validar_archivo_existe(ruta, nombre):
    if not os.path.exists(ruta):
        raise FileNotFoundError(f"No existe el archivo {nombre}:\n{ruta}")


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
# MODO 1: PROGRAMAR MES
# ====================================ç=====================
def programar_mes(year, month):
    num_dias = calendar.monthrange(year, month)[1]
    D = list(range(1, num_dias + 1))
    domingos = [d for d in D if date(year, month, d).weekday() == 6]
    cant_domingos = len(domingos)

    print(f"\nMes: {month:02d}/{year}")
    print(f"Días del mes: {num_dias}")
    print(f"Domingos del mes: {cant_domingos}")

    validar_archivo_existe(RUTA_BASE, "base")
    validar_archivo_existe(RUTA_ANUAL, "anual")

    # ---------------------------------------------
    # Detectar hojas del archivo base
    # ---------------------------------------------
    xls_base = pd.ExcelFile(RUTA_BASE, engine="openpyxl")
    hojas_base = xls_base.sheet_names

    if "Saldo" in hojas_base:
        hoja_personas = "Saldo"
    elif "Asistentes" in hojas_base:
        hoja_personas = "Asistentes"
    else:
        raise ValueError("No se encontró ni Hoja3 ni Hoja1 en BaseDatos.xlsx")

    if "Asistentes" not in hojas_base:
        raise ValueError("No se encontró Hoja1 en BaseDatos.xlsx. Se necesita para leer Esteriliza.")

    # ---------------------------------------------
    # Leer archivos
    # ---------------------------------------------
    df_p = leer_excel_seguro(RUTA_BASE, hoja_personas)   
    df_info = leer_excel_seguro(RUTA_BASE, "Asistentes")      
    df_anual = leer_excel_seguro(RUTA_ANUAL, "Calendario")

    df_p.columns = df_p.columns.str.strip()
    df_info.columns = df_info.columns.str.strip()
    df_anual.columns = df_anual.columns.str.strip()

    col_persona_p = buscar_columna(df_p, ["Persona"])
    col_persona_info = buscar_columna(df_info, ["Persona"])
    col_persona_anual = buscar_columna(df_anual, ["Persona"])

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
        ["Esteriliza"],
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


   #total de L requeridos del mes
    total_req_l_mes = sum(cant_domingos + libres_disp[p] for p in P)

    # ---------------------------------------------
    # Leer arrastre del mes anterior e historial
    # ---------------------------------------------
    year_prev, month_prev = obtener_mes_anterior(year, month)
    ruta_mes_anterior = os.path.join(CARPETA_SALIDA, nombre_archivo_mensual(year_prev, month_prev))

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

            # --- NUEVA LECTURA DEL HISTORIAL PARA CONSECUTIVIDAD ---
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

            total_req_l_mes = sum(cant_domingos + libres_disp[p] for p in P)

            print(f"\nSe encontró arrastre del mes anterior: {ruta_mes_anterior}")
            print(f"Hoja utilizada: {hoja_arrastre}")
            print("Se aplicó correctamente el arrastre y el historial de consecutividad.")

        except Exception as e:
            print(f"\nNo se pudo leer el arrastre o el calendario anterior. Se usará la base original sin historial.")
            print("Detalle:", e)
    else:
        print(f"\nNo existe archivo del mes anterior ({ruta_mes_anterior}). Se usará la base original sin historial.")

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

    

    # ---------------------------------------------
    # Indicadores base
    # ---------------------------------------------
    es_trabajable = {(p, d): 1 if base_turn[p][d] in ["M", "T", "N"] else 0 for p in P for d in D}
    es_N = {(p, d): 1 if base_turn[p][d] == "N" else 0 for p in P for d in D}
    total_trabajables = {p: sum(es_trabajable[p, d] for d in D) for p in P}

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

        # Conteo de saldo con días con actividad
        model += saldo_inicial[p] + total_trabajables[p] == 12 * G[p] + R[p]

        # Libres ordinarios exactos
        req_libres = cant_domingos + libres_disp[p]
        dias_elegibles = [d for d in D if es_trabajable[p, d] == 1]
        model += pulp.lpSum(L[p][d] for d in dias_elegibles) == req_libres

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


    # ---------------------------------------------

    print("\nResolviendo modelo - etapa 1 (minimizar Dmax)...")
    model.solve(pulp.PULP_CBC_CMD(
    msg=0,
    timeLimit=TIEMPO_MAX_ETAPA_1,
    gapRel=GAP_REL_ETAPA_1
))

    estado1, sol1 = obtener_estado_modelo(model)
    print("Estado del modelo etapa 1:", estado1, "| Solución:", sol1)

    if not solucion_aceptable(model):
        print("\nNo se encontró solución válida en etapa 1.")
        return

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
        print("\nNo se encontró solución válida en etapa 2.")
        return

    if estado2 != "Optimal":
        print(
            "Etapa 2 terminada con la mejor solución factible encontrada "
            "dentro del límite de tiempo."
        )

    best_dev_total = pulp.value(dev_total_expr)

    # ---------------------------------------------
    # ETAPA 3: reducir brecha pico-valle
    # ---------------------------------------------
    model += dev_total_expr <= best_dev_total + EPS, "Fijar_Desviacion_Optima"
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
        print("\nNo se encontró solución válida en etapa 3.")
        return

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
        racha_max = round(pulp.value(C[p]), 2)

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
    # Arrastre al siguiente mes
    # ---------------------------------------------
    arrastre = []

    for p in P:
        lb_sig = 0
        if base_turn[p][num_dias] == "N" and pulp.value(L[p][num_dias]) < 0.5:
            lb_sig = 1

        arrastre.append({
            "Persona": p,
            "Saldo acumulado siguiente mes": int(round(pulp.value(R[p]))),
            "LB inicial siguiente mes": lb_sig,
            "Libres acumulados disponibles siguiente mes": int(round(pulp.value(G[p])))
        })

    df_arrastre = pd.DataFrame(arrastre)

    # ---------------------------------------------
    # Guardar
    # ---------------------------------------------
    os.makedirs(CARPETA_SALIDA, exist_ok=True)
    nombre_archivo_salida = nombre_archivo_mensual(year, month)
    ruta_salida = os.path.join(CARPETA_SALIDA, nombre_archivo_salida)

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


# =========================================================
# MODO 2: CERRAR MES REAL
# =========================================================
def cerrar_mes_real(year, month):
    ruta_archivo = os.path.join(CARPETA_SALIDA, nombre_archivo_mensual(year, month))
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


# =========================================================
# MENÚ PRINCIPAL
# =========================================================
if __name__ == "__main__":
    print("Seleccione modo:")
    print("1 = Programar mes")
    print("2 = Cerrar mes real")
    modo = input("Opción: ").strip()

    year = int(input("Ingrese el año (ej. 2026): "))
    month = int(input("Ingrese el mes (1-12): "))

    if modo == "1":
        programar_mes(year, month)
    elif modo == "2":
        cerrar_mes_real(year, month)
    else:
        print("Opción no válida.")