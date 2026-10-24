#!/usr/bin/env python3

import csv
import math
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
ENTRADA = BASE / "data/wrfchem/impacto_departamental.csv"
SALIDA = BASE / "data/wrfchem/impacto_departamental_aqi_horario.csv"

# Puntos de corte de referencia EPA.
# IMPORTANTE: se aplican a valores horarios como categorias estimadas,
# no como AQI oficial, porque los puntos de corte de particulas
# corresponden a promedios de 24 horas.

CATEGORIAS_PM25 = [
    (9.0, "Bueno"),
    (35.4, "Moderado"),
    (55.4, "Insalubre para grupos sensibles"),
    (125.4, "Insalubre"),
    (225.4, "Muy insalubre"),
    (math.inf, "Peligroso"),
]

CATEGORIAS_PM10 = [
    (54, "Bueno"),
    (154, "Moderado"),
    (254, "Insalubre para grupos sensibles"),
    (354, "Insalubre"),
    (424, "Muy insalubre"),
    (math.inf, "Peligroso"),
]


def clasificar(valor, contaminante):
    if valor is None or valor == "":
        return "Sin datos"

    try:
        valor = float(valor)
    except (TypeError, ValueError):
        return "Sin datos"

    if not math.isfinite(valor):
        return "Sin datos"

    if valor < 0:
        return "Valor invalido"
    if valor == 0:
        return "Bueno"

    cortes = (
        CATEGORIAS_PM25
        if contaminante == "PM2.5"
        else CATEGORIAS_PM10
    )

    for limite, categoria in cortes:
        if valor <= limite:
            return categoria

    return "Peligroso"


if not ENTRADA.exists():
    raise SystemExit(f"No existe el archivo de entrada: {ENTRADA}")

with open(ENTRADA, newline="", encoding="utf-8-sig") as f:
    lector = csv.DictReader(f)
    filas = list(lector)
    columnas = list(lector.fieldnames or [])

if not filas:
    raise SystemExit("El CSV de entrada no contiene registros.")

nuevas = [
    "categoria_maximo_horaria",
    "categoria_promedio_horaria",
    "metodo_clasificacion",
]

for columna in nuevas:
    if columna not in columnas:
        columnas.append(columna)

for fila in filas:
    contaminante = fila.get("contaminante", "")

    fila["categoria_maximo_horaria"] = clasificar(
        fila.get("maximo_ug_m3"), contaminante
    )
    fila["categoria_promedio_horaria"] = clasificar(
        fila.get("promedio_ug_m3"), contaminante
    )
    fila["metodo_clasificacion"] = (
        "Categoria horaria estimada; puntos de corte EPA de PM "
        "definidos para promedio de 24 horas"
    )

with open(SALIDA, "w", newline="", encoding="utf-8-sig") as f:
    escritor = csv.DictWriter(f, fieldnames=columnas)
    escritor.writeheader()
    escritor.writerows(filas)

print(f"Archivo generado: {SALIDA}")
print(f"Registros clasificados: {len(filas)}")
print("Clasificacion aplicada por hora, departamento y contaminante.")
print("Las categorias son estimadas, no un AQI oficial horario.")
