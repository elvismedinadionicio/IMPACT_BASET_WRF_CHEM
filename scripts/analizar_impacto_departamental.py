#!/usr/bin/env python3
# Analisis departamental de PM2.5 y PM10 mediante mascaras reutilizables.
# No requiere geopandas, shapely ni GDAL. Requiere numpy.

import csv
import json
import math
import struct
import sys
from pathlib import Path

import numpy as np

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data" / "wrfchem"
SHP = BASE / "shape" / "PERU.shp"
DBF = BASE / "shape" / "PERU.dbf"
CACHE = DATA / "mascaras_departamentales.npz"
SALIDA = DATA / "impacto_departamental.csv"
UMBRAL = 50.0


def leer_dbf(ruta):
    """Lee atributos DBF sin dependencias GIS."""
    filas = []
    with open(ruta, "rb") as f:
        cab = f.read(32)
        if len(cab) != 32:
            raise ValueError("Cabecera DBF incompleta")

        nreg = struct.unpack("<I", cab[4:8])[0]
        hlen = struct.unpack("<H", cab[8:10])[0]
        rlen = struct.unpack("<H", cab[10:12])[0]

        campos = []
        while f.tell() < hlen:
            b = f.read(1)
            if not b or b == b"\r":
                break
            desc = b + f.read(31)
            nombre = desc[:11].split(b"\0", 1)[0].decode(
                "latin-1"
            ).strip()
            campos.append((
                nombre, chr(desc[11]), desc[16], desc[17]
            ))

        f.seek(hlen)
        for _ in range(nreg):
            raw = f.read(rlen)
            if len(raw) != rlen:
                break
            if raw[:1] == b"*":
                continue

            pos = 1
            fila = {}
            for nombre, tipo, largo, decimales in campos:
                s = raw[pos:pos + largo].decode(
                    "latin-1", errors="replace"
                ).strip()
                pos += largo

                if tipo in ("N", "F"):
                    try:
                        val = float(s) if s and "*" not in s else None
                        if val is not None and val.is_integer():
                            val = int(val)
                    except ValueError:
                        val = None
                else:
                    val = s
                fila[nombre] = val
            filas.append(fila)

    return filas


def leer_shp(ruta):
    """Lee poligonos SHP y devuelve sus anillos."""
    geometrías = []

    with open(ruta, "rb") as f:
        cab = f.read(100)
        if len(cab) != 100 or struct.unpack(">I", cab[:4])[0] != 9994:
            raise ValueError("El archivo no parece ser un SHP valido")

        while True:
            rh = f.read(8)
            if not rh:
                break
            if len(rh) != 8:
                raise ValueError("Registro SHP incompleto")

            _, words = struct.unpack(">2i", rh)
            contenido = f.read(words * 2)
            if len(contenido) != words * 2:
                raise ValueError("Geometria SHP incompleta")

            if len(contenido) < 44:
                geometrías.append([])
                continue

            tipo = struct.unpack("<i", contenido[:4])[0]
            if tipo == 0:
                geometrías.append([])
                continue
            if tipo not in (5, 15, 25):
                raise ValueError(
                    f"Tipo de geometria SHP inesperado: {tipo}"
                )

            npartes, npuntos = struct.unpack(
                "<2i", contenido[36:44]
            )
            offset = 44
            partes = list(struct.unpack(
                "<" + "i" * npartes,
                contenido[offset:offset + 4 * npartes]
            ))
            offset += 4 * npartes

            coords = np.frombuffer(
                contenido, dtype="<f8",
                count=npuntos * 2, offset=offset
            ).reshape(-1, 2)

            anillos = []
            for i, inicio in enumerate(partes):
                fin = partes[i + 1] if i + 1 < len(partes) else npuntos
                if fin - inicio >= 3:
                    anillos.append(coords[inicio:fin])

            geometrías.append(anillos)

    return geometrías


def dentro_anillo(x, y, anillo):
    """Determina por ray casting los puntos dentro de un anillo."""
    dentro = np.zeros(x.shape, dtype=bool)
    x1, y1 = anillo[-1]

    for x2, y2 in anillo:
        cruza = (y1 > y) != (y2 > y)
        if y2 != y1:
            xc = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            dentro ^= cruza & (x < xc)
        x1, y1 = x2, y2

    return dentro


def dentro_poligono(x, y, anillos):
    """Regla par-impar para anillos exteriores e interiores."""
    dentro = np.zeros(x.shape, dtype=bool)
    for anillo in anillos:
        dentro ^= dentro_anillo(x, y, anillo)
    return dentro


def nombre_departamento(fila, i):
    return str(
        fila.get("DEPARTAMEN")
        or fila.get("DEPARTAMENTO")
        or f"REGION_{i + 1}"
    ).strip()


def leer_poblacion(fila):
    # POBLACION es el campo principal del DBF.
    # POBLACIO_1 se usa como alternativa si el primero no existe.
    valor = fila.get("POBLACION")
    if valor is None:
        valor = fila.get("POBLACIO_1")
    try:
        return float(valor) if valor is not None else math.nan
    except (TypeError, ValueError):
        return math.nan


def construir_mascaras(lat, lon, atributos, geometrías):
    if len(atributos) != len(geometrías):
        raise ValueError(
            f"DBF tiene {len(atributos)} registros y SHP "
            f"{len(geometrías)} geometrías."
        )

    mascaras = []
    nombres = []
    ids = []
    poblaciones = []

    x = lon.ravel()
    y = lat.ravel()

    for i, (fila, geom) in enumerate(zip(atributos, geometrías)):
        nombre = nombre_departamento(fila, i)
        idd = str(fila.get("IDDPTO") or "").strip()
        mascara = dentro_poligono(x, y, geom)

        nombres.append(nombre)
        ids.append(idd)
        poblaciones.append(leer_poblacion(fila))
        mascaras.append(mascara)

    np.savez_compressed(
        CACHE,
        masks=np.vstack(mascaras),
        nombres=np.asarray(nombres, dtype="U80"),
        ids=np.asarray(ids, dtype="U20"),
        poblaciones=np.asarray(poblaciones, dtype=float),
        grid_shape=np.asarray(lat.shape, dtype=int),
    )

    return mascaras, nombres, ids, poblaciones


def cargar_cache(lat, atributos):
    if not CACHE.exists():
        return None

    try:
        with np.load(CACHE, allow_pickle=False) as z:
            masks = z["masks"]
            nombres = z["nombres"].tolist()
            ids = z["ids"].tolist()
            poblaciones = z["poblaciones"].tolist()
            shape = tuple(z["grid_shape"].tolist())

        nombres_dbf = [
            nombre_departamento(f, i)
            for i, f in enumerate(atributos)
        ]

        if shape != lat.shape:
            return None
        if masks.shape != (len(atributos), lat.size):
            return None
        if nombres != nombres_dbf:
            return None

        return (
            [masks[i].astype(bool) for i in range(len(nombres))],
            nombres, ids, poblaciones
        )
    except Exception:
        return None


def obtener_horas(manifest):
    lista = manifest.get("hours") or manifest.get("times") or []
    horas = []

    for i, item in enumerate(lista):
        if isinstance(item, str):
            horas.append({
                "time": item,
                "file": f"hour_{i:04d}.json"
            })
        elif isinstance(item, dict):
            horas.append({
                "time": item.get("time")
                        or item.get("datetime")
                        or item.get("valid_time"),
                "file": item.get("file")
                        or item.get("filename")
                        or item.get("path")
                        or f"hour_{i:04d}.json"
            })

    if not horas:
        horas = [
            {"time": None, "file": p.name}
            for p in sorted(DATA.glob("hour_*.json"))
        ]

    return horas


def main():
    for ruta in (DATA / "manifest.json", SHP, DBF):
        if not ruta.exists():
            raise FileNotFoundError(f"No se encuentra: {ruta}")

    with open(DATA / "manifest.json", encoding="utf-8") as f:
        manifest = json.load(f)

    grid = manifest.get("grid", manifest)
    lat = np.asarray(grid.get("lat"), dtype=float)
    lon = np.asarray(grid.get("lon"), dtype=float)

    if lat.size == 0 or lon.size == 0 or lat.shape != lon.shape:
        raise ValueError(
            "No se encontraron lat/lon compatibles en manifest.json"
        )

    atributos = leer_dbf(DBF)
    cache = cargar_cache(lat, atributos)

    if cache is not None:
        mascaras, nombres, ids, poblaciones = cache
        print("Mascaras cargadas desde cache existente.")
    else:
        print("Creando mascaras departamentales...")
        geometrías = leer_shp(SHP)
        mascaras, nombres, ids, poblaciones = construir_mascaras(
            lat, lon, atributos, geometrías
        )
        print(f"Mascaras guardadas en: {CACHE}")

    print(f"\nDimensiones de la cuadricula: {lat.shape}")
    print(f"Puntos totales: {lat.size}")
    print(
        f"Latitud: {np.nanmin(lat):.3f} a {np.nanmax(lat):.3f}"
    )
    print(
        f"Longitud: {np.nanmin(lon):.3f} a {np.nanmax(lon):.3f}"
    )
    print("\nPuntos por departamento:")
    for nombre, mascara in zip(nombres, mascaras):
        print(f"  {nombre}: {int(mascara.sum())}")

    filas = []
    horas = obtener_horas(manifest)

    for h in horas:
        ruta = DATA / h["file"]
        if not ruta.exists():
            print(f"AVISO: falta {ruta.name}; se omite.")
            continue

        with open(ruta, encoding="utf-8") as f:
            datos = json.load(f)

        hora = h.get("time") or datos.get("time") or ruta.stem

        for variable, etiqueta in (
            ("PM25", "PM2.5"),
            ("PM10", "PM10"),
        ):
            datos_variable = datos.get(variable)
            if not isinstance(datos_variable, list):
                print(f"AVISO: {ruta.name} no contiene {variable}.")
                continue

            if len(datos_variable) != lat.size:
                print(
                    f"AVISO: {ruta.name} {variable} tiene "
                    f"{len(datos_variable)} valores; se esperaban "
                    f"{lat.size}. Se omite."
                )
                continue

            valores = np.asarray(datos_variable, dtype=float)

            for nombre, idd, poblacion, mascara in zip(
                nombres, ids, poblaciones, mascaras
            ):
                v = valores[mascara]
                v = v[np.isfinite(v)]

                if v.size:
                    sobre = v > UMBRAL
                    maximo = round(float(np.max(v)), 3)
                    promedio = round(float(np.mean(v)), 3)
                    n_sobre = int(sobre.sum())
                    porcentaje = round(100 * n_sobre / v.size, 2)
                else:
                    maximo = ""
                    promedio = ""
                    n_sobre = 0
                    porcentaje = ""

                filas.append({
                    "hora_utc": hora,
                    "departamento": nombre,
                    "id_dpto": idd,
                    "contaminante": etiqueta,
                    "umbral_ug_m3": UMBRAL,
                    "puntos_departamentales": int(mascara.sum()),
                    "puntos_validos": int(v.size),
                    "puntos_sobre_umbral": n_sobre,
                    "porcentaje_puntos_sobre_umbral": porcentaje,
                    "maximo_ug_m3": maximo,
                    "promedio_ug_m3": promedio,
                    "poblacion_departamental": (
                        round(poblacion) if math.isfinite(poblacion) else ""
                    ),
                })

    if not filas:
        raise RuntimeError(
            "No se generaron resultados. Revisa los JSON y el manifiesto."
        )

    with open(SALIDA, "w", newline="", encoding="utf-8-sig") as f:
        escritor = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        escritor.writeheader()
        escritor.writerows(filas)

    print(f"\nArchivo CSV generado: {SALIDA}")
    print(f"Filas generadas: {len(filas)}")
    print(f"Umbral analitico: > {UMBRAL} ug/m3")
    print(
        "NOTA: la poblacion departamental no equivale a poblacion "
        "realmente expuesta."
    )
    print(
        "VALIDACION: comprobar unidades, valores extremos y cobertura "
        "espacial antes de interpretar los resultados."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
