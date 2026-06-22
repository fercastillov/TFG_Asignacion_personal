import pandas as pd
import pulp
import datetime
import os

# Leer Ruta
DIRECTORIO_ACTUAL = os.path.dirname(os.path.abspath(__file__))
ruta_base_datos = os.path.join(DIRECTORIO_ACTUAL, "Base de Datos", "BaseDatos.xlsx")

df = pd.read_excel(ruta_base_datos)

# Normalizar nombres de columnas para evitar errores por espacios invisibles.
df.columns = [str(col).strip() for col in df.columns]

# Validar que las columnas básicas existan en la base de datos que realmente está leyendo el modelo.
columnas_requeridas = ["Persona", "Rol", "Semanas de Vacaciones"]
columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
if columnas_faltantes:
    print("\nERROR: La base de datos que está leyendo el modelo no tiene estas columnas básicas:")
    print(columnas_faltantes)
    print("\nArchivo leído:", ruta_base_datos)
    print("\nColumnas encontradas en ese archivo:")
    print(list(df.columns))
    raise KeyError(f"Faltan columnas requeridas en la base de datos: {columnas_faltantes}")

# Columna que indica quién puede esterilizar.
if "Esteriliza" in df.columns:
    columna_esteriliza = "Esteriliza"
elif "F6" in df.columns:
    columna_esteriliza = "F6"
    print("\nAVISO: No encontré la columna 'Esteriliza'. Usaré 'F6' como columna de Esteriliza.")
else:
    print("\nERROR: No encontré una columna para identificar quién puede esterilizar.")
    print("Debe existir una columna llamada 'Esteriliza' o, en la base anterior, la columna 'F6'.")
    print("\nArchivo leído:", ruta_base_datos)
    print("\nColumnas encontradas en ese archivo:")
    print(list(df.columns))
    raise KeyError("Falta la columna 'Esteriliza' o la columna alternativa 'F6'.")

# Convertir la columna de esterilización a 1/0, aceptando valores como 1, Sí, Si, X o True.
valores_positivos_esteriliza = {"1", "si", "sí", "s", "x", "true", "verdadero"}

def convertir_esteriliza(valor):
    if pd.isna(valor):
        return 0
    if isinstance(valor, str):
        return 1 if valor.strip().lower() in valores_positivos_esteriliza else 0
    try:
        return 1 if int(valor) == 1 else 0
    except Exception:
        return 0

# Crear una columna estándar interna llamada "Esteriliza" para que el resto del modelo no cambie.
df["Esteriliza"] = df[columna_esteriliza].apply(convertir_esteriliza)

df = df[df["Rol"] != 4]
df = df.set_index("Persona")

print("Datos cargados correctamente.")

# Definición de índices y semanas (calendario)
P = list(df.index)
T = ["Mañana", "Tarde", "Noche"]

year = datetime.date.today().year
last_day = datetime.date(year, 12, 31)
num_semanas = last_day.isocalendar()[1]
S = range(1, num_semanas + 1)

# Parámetros
i = df["Rol"].astype(int).to_dict()
W = df["Semanas de Vacaciones"].to_dict()

# Personas que pueden esterilizar según la base de datos.
E = df["Esteriliza"].astype(int).to_dict()
P_esteriliza = [p for p in P if E[p] == 1]

if not P_esteriliza:
    raise ValueError("No hay ninguna persona marcada como capaz de esterilizar en la columna 'Esteriliza'.")

P_rol3 = [p for p in P if i[p] == 3]
P_rol1_2 = [p for p in P if i[p] in [1, 2]]

# Funcionamiento de vacantes fijas
V = {p: [] for p in P}
for p in P:
    print(f"\nPersona: {p} (rol {i[p]}) - Vacaciones totales: {W[p]}")
    while len(V[p]) < W[p]:
        entrada = input(f"Semana fija ({len(V[p])}/{W[p]}) ENTER para terminar: ")
        if entrada == "": break
        try:
            s = int(entrada)
            if 1 <= s <= num_semanas and s not in V[p]:
                V[p].append(s)
            else:
                print("Semana inválida o repetida")
        except:
            print("Entrada inválida")

# Solver
model = pulp.LpProblem("Modelo_TFG_Final", pulp.LpMinimize)

# Variables

X = pulp.LpVariable.dicts("X", (P, S, T), 0, 1, cat='Binary')
Z = pulp.LpVariable.dicts("Z", (P, S), 0, 1, cat='Binary')
H_vac = pulp.LpVariable.dicts("H_vac", S, lowBound=0, cat='Integer')
N = pulp.LpVariable.dicts("N", (P, T), lowBound=0, cat='Integer')
C = pulp.LpVariable.dicts("C", (P, P, T), lowBound=0, cat='Continuous')
D = pulp.LpVariable("D", lowBound=0, cat='Continuous')

# Restricciones
# A. Una actividad máximo 
for p in P:
    for s in S:
        model += pulp.lpSum(X[p][s][t] for t in T) + Z[p][s] == 1

# B. Vacaciones (Fijas y Totales)
for p in P:
    for s in V[p]:
        model += Z[p][s] == 1
    model += pulp.lpSum(Z[p][s] for s in S) == W[p]

# C. Cobertura de turnos 
r_min = {"Mañana": 11, "Tarde": 10, "Noche": 3}
r_max = {"Mañana": 20, "Tarde": 20, "Noche": 4}
for t in T:
    for s in S:
        total_turno = pulp.lpSum(X[p][s][t] for p in P)
        model += total_turno >= r_min[t]
        model += total_turno <= r_max[t]

# D. Asistente 2: Máximo 1 por turno y solo Mañana/Tarde
for s in S:
    for t in T:
        # Solo máximo 1 persona de rol 2 por turno
        model += pulp.lpSum(X[p][s][t] for p in P if i[p] == 2) <= 1
        
        # Prohibir Noche para Rol 2
        if t == "Noche":
            for p in P:
                if i[p] == 2:
                    model += X[p][s][t] == 0

# E. Mínimo 2 personas en vacaciones
for s in S:
    model += pulp.lpSum(Z[p][s] for p in P) + H_vac[s] >= 2

# F. Mínimo 1 persona que pueda esterilizar en el turno de Noche
for s in S:
    model += pulp.lpSum(X[p][s]["Noche"] for p in P_esteriliza) >= 2

# G. Máximo 6 semanas consecutivas mismo turno
for p in P:
    for t in T:
        for s in range(1, num_semanas - 6):
            model += pulp.lpSum(X[p][s+k][t] for k in range(7)) <= 6

# Restricciones asociadas a la definición de la función obejtivo
for p in P:
    for t in T:
        model += N[p][t] == pulp.lpSum(X[p][s][t] for s in S)

# Restricciones asociadas a la definición de la función obejtivo
for p in P:
    for p2 in P:
        if p >= p2: continue
        if i[p] == i[p2]: 
            for t in T:
                model += C[p][p2][t] >= N[p][t] - N[p2][t]
                model += C[p][p2][t] >= N[p2][t] - N[p][t]
                model += D >= C[p][p2][t]

# Función Objetivo
model += D + (pulp.lpSum(H_vac[s] for s in S) * 1000)

# Resolver
model.solve(pulp.PULP_CBC_CMD(msg=0))

# Conteo Final Consola
print("\nRESUMEN SEMANAL")
for s in S:
    vac = sum(1 for p in P if pulp.value(Z[p][s]) > 0.5)
    m = sum(1 for p in P if pulp.value(X[p][s]["Mañana"]) > 0.5)
    t = sum(1 for p in P if pulp.value(X[p][s]["Tarde"]) > 0.5)
    n = sum(1 for p in P if pulp.value(X[p][s]["Noche"]) > 0.5)
    print(f"Semana {s}: V={vac}, M={m}, T={t}, N={n}")

# Exportación
data = []
for p in P:
    fila = {"Persona": p, "Rol": i[p]}
    for s in S:
        if pulp.value(Z[p][s]) > 0.5:
            fila[f"S{s}"] = "V"
        else:
            turno = "O"
            for t in T:
                if pulp.value(X[p][s][t]) > 0.5:
                    turno = t[0]
            fila[f"S{s}"] = turno
    data.append(fila)

df_calendario = pd.DataFrame(data)
carpeta_resultados = os.path.join(DIRECTORIO_ACTUAL, "Resultados")
os.makedirs(carpeta_resultados, exist_ok=True)
ruta_fin = os.path.join(carpeta_resultados, "solucion_final_revisada.xlsx")

with pd.ExcelWriter(ruta_fin) as writer:
    df_calendario.to_excel(writer, sheet_name="Calendario", index=False)
    # Hoja de conteo para verificar 10-8-4
    conteo_data = [{"Semana": s, "M": sum(1 for p in P if pulp.value(X[p][s]["Mañana"]) > 0.5), 
                    "T": sum(1 for p in P if pulp.value(X[p][s]["Tarde"]) > 0.5), 
                    "N": sum(1 for p in P if pulp.value(X[p][s]["Noche"]) > 0.5),
                    "Vac": sum(1 for p in P if pulp.value(Z[p][s]) > 0.5)} for s in S]
    pd.DataFrame(conteo_data).to_excel(writer, sheet_name="Verificacion", index=False)

print(f"\n¡Listo! Estado: {pulp.LpStatus[model.status]}")
print(f"Archivo en: {ruta_fin}")