# Sistema de Planificación y Asignación - CEYE

Este repositorio contiene los códigos en Python para la planificación y asignación del personal en la Central de Esterilización y Equipo (CEYE).

---

## A. Requisitos e instalación

Antes de ejecutar cualquier archivo, instale las dependencias necesarias desde la terminal:

```bash
pip install pandas openpyxl pulp streamlit altair
```

---

## B. Cómo usar los modelos

El sistema puede ejecutarse de dos formas:

1. **Mediante la interfaz web interactiva (recomendado).**
2. **Mediante los scripts individuales desde la consola.**

---

## Opción 1: Usar la interfaz web completa

Para abrir la aplicación gráfica donde todos los modelos se encuentran integrados, ejecute:

```bash
streamlit run Sistema_CEYE_Interfaz.py
```

Esto abrirá automáticamente una pestaña en su navegador web. Desde la interfaz podrá:

- Seleccionar el año de planificación.
- Cambiar el mes de trabajo desde el panel lateral.
- Ejecutar cada modelo mediante los botones disponibles en cada pestaña.
- Visualizar los resultados de forma centralizada.

---

## Opción 2: Ejecutar los scripts por consola

Si prefiere ejecutar cada modelo de forma independiente, debe seguir el siguiente orden de precedencia:

### 1. Asignación Anual

Determina la distribución inicial de las semanas de vacaciones y los turnos de trabajo para todo el año.

**Comando:**

```bash
python "Modelo Anual.py"
```

**Entrada:**

```text
Base de Datos/BaseDatos.xlsx
```

**Salida:**

```text
Resultados/solucion_final_revisada.xlsx
```

---

### 2. Asignación Mensual

Determina la asignación de días libres y calcula los días acumulados.

**Comando:**

```bash
python "Modelo Mensual.py"
```

Al ejecutarlo, el sistema solicitará seleccionar una opción:

- **1:** Programar un mes nuevo.
- **2:** Realizar el cierre real del mes incorporando incidencias (incapacidades, ausencias, entre otros).

---

### 3. Asignación de Funciones

Toma los turnos generados en el paso anterior y distribuye al personal en las funciones específicas de la CEYE.

**Comando:**

```bash
python "Modelo de funciones.py"
```

**Salida:**

```text
Resultados/asignacion_funciones_AÑO_MES.xlsx
```

---

## Flujo de ejecución recomendado

```text
Modelo Anual
      ↓
Modelo Mensual
      ↓
Modelo de Funciones
```

Seguir este orden garantiza que cada modelo disponga de la información requerida generada por la etapa anterior.
