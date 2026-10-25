#!/usr/bin/env python3
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "wrfchem"
SCRIPT = BASE / "scripts" / "analizar_impacto_departamental.py"
SALIDA = DATA / "resumen_aqi_departamental.json"

# Categorías de referencia EPA para concentraciones de partículas.
# Aplicadas a datos horarios: son estimaciones, no AQI oficial horario.
CATEGORIAS = {
    "PM25": [
        (9.0, "Bueno"),
        (35.4, "Moderado"),
        (55.4, "Insalubre para grupos sensibles"),
        (125.4, "Insalubre"),
        (225.4, "Muy insalubre"),
        (325.4, "Peligroso"),
        (math.inf, "Fuera del rango AQI EPA"),
    ],
    "PM10": [
        (54.0, "Bueno"),
        (154.0, "Moderado"),
        (254.0, "Insalubre para grupos sensibles"),
        (354.0, "Insalubre"),
        (424.0, "Muy insalubre"),
        (604.0, "Peligroso"),
        (math.inf, "Fuera del rango AQI EPA"),
    ],
}

def clasificar(valor, contaminante):
    for limite, categoria in CATEGORIAS[contaminante]:
        if valor <= limite:
            return categoria
    return "Sin datos"

def main():
    if not SCRIPT.exists():
        raise FileNotFoundError(f"No existe: {SCRIPT}")

    spec = importlib.util.spec_from_file_location(
        "analizador_departamental", SCRIPT
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    manifest_path = DATA / "manifest.json"
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    grid = manifest["grid"]
    lat = np.asarray(grid["lat"], dtype=float)
    lon = np.asarray(grid["lon"], dtype=float)

    if lat.shape != lon.shape:
        raise ValueError("Las matrices de latitud y longitud no coinciden.")

    atributos = mod.leer_dbf(mod.DBF)
    cache = mod.cargar_cache(lat, atributos)

    if cache is None:
        geometrías = mod.leer_shp(mod.SHP)
        mascaras, nombres, ids, poblaciones = mod.construir_mascaras(
            lat, lon, atributos, geometrías
        )
    else:
        mascaras, nombres, ids, poblaciones = cache

    horas = mod.obtener_horas(manifest)
    resultados = {
        "titulo": "Clasificación horaria estimada por departamento",
        "metodo": (
            "Puntos de corte de referencia EPA para PM2.5 y PM10. "
            "Aplicación horaria orientativa; no representa AQI oficial "
            "de 24 horas ni población realmente expuesta."
        ),
        "categorias": {
            contaminante: [nombre for _, nombre in cortes]
            for contaminante, cortes in CATEGORIAS.items()
        },
        "horas": [],
    }

    for h in horas:
        ruta = DATA / h["file"]
        if not ruta.exists():
            print(f"AVISO: se omite archivo inexistente {ruta.name}")
            continue

        with open(ruta, encoding="utf-8") as f:
            datos = json.load(f)

        hora = h.get("time") or datos.get("time") or ruta.stem
        registro_hora = {"time": hora, "file": ruta.name, "departamentos": []}

        for nombre, idd, mascara in zip(nombres, ids, mascaras):
            depto = {
                "nombre": nombre,
                "id": idd,
                "puntos_malla": int(mascara.sum()),
                "contaminantes": {},
            }

            for variable, etiqueta in (
                ("PM25", "PM2.5"),
                ("PM10", "PM10"),
            ):
                datos_variable = datos.get(variable)
                if not isinstance(datos_variable, list) or len(datos_variable) != lat.size:
                    depto["contaminantes"][variable] = {
                        "etiqueta": etiqueta,
                        "estado": "Sin datos o dimensión incompatible",
                        "puntos_validos": 0,
                        "promedio": None,
                        "maximo": None,
                        "categorias": {},
                    }
                    continue

                valores = np.asarray(datos_variable, dtype=float)[mascara]
                # Los ceros se conservan como concentraciones válidas.
                validos = valores[np.isfinite(valores) & (valores >= 0)]
                categorias = {
                    categoria: 0 for _, categoria in CATEGORIAS[variable]
                }

                for valor in validos:
                    categorias[clasificar(float(valor), variable)] += 1

                n = int(validos.size)
                porcentajes = {
                    categoria: round(100 * cantidad / n, 2) if n else None
                    for categoria, cantidad in categorias.items()
                }

                depto["contaminantes"][variable] = {
                    "etiqueta": etiqueta,
                    "estado": "OK" if n else "Sin datos válidos",
                    "puntos_validos": n,
                    "promedio": round(float(np.mean(validos)), 3) if n else None,
                    "maximo": round(float(np.max(validos)), 3) if n else None,
                    "categorias": categorias,
                    "porcentajes": porcentajes,
                }

            registro_hora["departamentos"].append(depto)

        resultados["horas"].append(registro_hora)

    if not resultados["horas"]:
        raise RuntimeError("No se generaron resultados horarios.")

    temporal = SALIDA.with_suffix(".json.tmp")
    with open(temporal, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, separators=(",", ":"))
    temporal.replace(SALIDA)

    print(f"Archivo generado: {SALIDA}")
    print(f"Horas procesadas: {len(resultados['horas'])}")
    print(f"Departamentos por hora: {len(resultados['horas'][0]['departamentos'])}")
    print("Se conservaron los ceros como valores válidos.")
    print("No se estimó población expuesta.")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
