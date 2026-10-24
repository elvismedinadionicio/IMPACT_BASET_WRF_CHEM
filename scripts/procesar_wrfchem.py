#!/usr/bin/env python3
"""Procesa concentraciones horarias de PM10 y PM2.5 desde WRF-Chem."""

import argparse
import json
import re
from pathlib import Path

import numpy as np
import xarray as xr

ROOT = Path(
    "/home/sea/WRF_CHEM/PERU_20240909/"
    "RUN_CAMS_MOZCART_20240908"
)
OUT = Path(__file__).resolve().parents[1] / "data" / "wrfchem"

CANDIDATES = {
    "PM25": ["PM2_5_DRY", "PM2_5", "PM25"],
    "PM10": ["PM10", "PM10_DRY"],
}


def find_variable(ds, requested, pollutant):
    name = requested
    if not name:
        name = next(
            (n for n in CANDIDATES[pollutant] if n in ds.variables),
            None,
        )

    if not name or name not in ds.variables:
        found = [
            n for n in ds.variables
            if any(x in n.upper() for x in ("PM25", "PM2_5", "PM10"))
        ]
        raise ValueError(
            f"No se pudo identificar {pollutant}. "
            f"Variables candidatas disponibles: {found}. "
            f"Especifica --pm25-var o --pm10-var."
        )

    var = ds[name]
    units = str(var.attrs.get("units", "")).strip().lower()
    normalized = (
        units.replace("μ", "µ")
        .replace("³", "3")
        .replace(" ", "")
        .replace("**", "")
        .replace("^", "")
    )
    allowed = {
        "ug/m3", "µg/m3", "ugm-3", "µgm-3",
        "ugm−3", "µgm−3", "microgram/m3",
        "micrograms/m3",
    }

    if normalized not in allowed:
        raise ValueError(
            f"{name} tiene unidades '{units}', no reconocidas como "
            "concentración en µg/m³. Verifica la variable y la conversión "
            "física antes de procesar."
        )

    return name


def find_latlon(ds):
    pairs = [
        ("XLAT", "XLONG"),
        ("XLAT_M", "XLONG_M"),
        ("lat", "lon"),
        ("latitude", "longitude"),
    ]

    for latname, lonname in pairs:
        if latname in ds.variables and lonname in ds.variables:
            lat = np.asarray(ds[latname].values, dtype=float)
            lon = np.asarray(ds[lonname].values, dtype=float)

            if lat.ndim == 3:
                lat = lat[0]
            if lon.ndim == 3:
                lon = lon[0]

            if lat.ndim == 2 and lon.ndim == 2 and lat.shape == lon.shape:
                return lat, lon

    raise ValueError(
        "No se encontraron coordenadas 2D compatibles "
        "(XLAT/XLONG o lat/lon)."
    )


def decode_times(ds, path):
    if "Times" in ds.variables:
        raw = np.asarray(ds["Times"].values)
        result = []

        for item in raw:
            if isinstance(item, (bytes, np.bytes_)):
                value = item.decode("ascii", errors="ignore")
            elif np.asarray(item).dtype.kind in ("S", "U"):
                value = "".join(
                    x.decode() if isinstance(x, bytes) else str(x)
                    for x in np.asarray(item).reshape(-1)
                )
            else:
                value = str(item)

            value = value.strip().replace("_", "T")
            value = value.replace("\x00", "")
            result.append(value[:19])

        if result:
            return result

    match = re.search(
        r"wrfout_d01_(\d{4}-\d{2}-\d{2})_(\d{2}:\d{2}:\d{2})",
        path.name,
    )
    if match:
        return [f"{match.group(1)}T{match.group(2)}"]

    raise ValueError(
        f"No se pudo determinar la hora del archivo {path.name}"
    )


def extract_field(ds, variable):
    var = ds[variable]

    # Las dimensiones espaciales deben ser las dos últimas.
    # Se selecciona el primer nivel vertical si existe.
    for dim in list(var.dims):
        if dim.lower() in ("bottom_top", "bottom_top_stag", "level", "lev"):
            var = var.isel({dim: 0})

    values = np.asarray(var.values, dtype=float)

    if values.ndim == 3:
        # Si hay más de un tiempo, el eje inicial es temporal.
        return [values[i] for i in range(values.shape[0])]
    if values.ndim == 2:
        return [values]

    raise ValueError(
        f"Dimensiones no compatibles para {variable}: {var.dims}, "
        f"forma={values.shape}. Revísalas antes de procesar."
    )


def concentration_json(values):
    values = np.asarray(values, dtype=float)
    values[~np.isfinite(values)] = np.nan
    values[values < 0] = np.nan

    return [
        None if not np.isfinite(v) else round(float(v), 4)
        for v in values.ravel()
    ]


def aqi_from_concentration(value, pollutant):
    """AQI estimado EPA para un promedio válido de 24 horas."""
    if value is None or not np.isfinite(value) or value < 0:
        return None

    if pollutant == "PM25":
        # PM2.5: truncar a una décima antes de aplicar los puntos de corte.
        c = np.floor(value * 10) / 10
        breaks = [
            (0.0, 9.0, 0, 50),
            (9.1, 35.4, 51, 100),
            (35.5, 55.4, 101, 150),
            (55.5, 125.4, 151, 200),
            (125.5, 225.4, 201, 300),
            (225.5, 325.4, 301, 500),
        ]
    else:
        # PM10: truncar a entero.
        c = np.floor(value)
        breaks = [
            (0, 54, 0, 50),
            (55, 154, 51, 100),
            (155, 254, 101, 150),
            (255, 354, 151, 200),
            (355, 424, 201, 300),
            (425, 604, 301, 500),
        ]

    for clo, chi, ilo, ihi in breaks:
        if clo <= c <= chi:
            return int(round((ihi - ilo) / (chi - clo) * (c - clo) + ilo))

    if pollutant == "PM25" and c > 325.4:
        return 500
    if pollutant == "PM10" and c > 604:
        return 500

    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=ROOT)
    parser.add_argument("--pm25-var", default=None)
    parser.add_argument("--pm10-var", default=None)
    args = parser.parse_args()

    files = sorted(args.input.glob("wrfout_d01_*"))
    if not files:
        raise SystemExit(f"No se encontraron archivos en {args.input}")

    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    reference_lat = reference_lon = None
    reference_shape = None

    print(f"Archivos de entrada: {len(files)}")

    for path in files:
        print(f"Leyendo {path.name}")

        with xr.open_dataset(path, decode_times=False) as ds:
            pm25_name = find_variable(ds, args.pm25_var, "PM25")
            pm10_name = find_variable(ds, args.pm10_var, "PM10")
            lat, lon = find_latlon(ds)

            if reference_shape is None:
                reference_shape = lat.shape
                reference_lat = lat
                reference_lon = lon
            elif (
                lat.shape != reference_shape
                or not np.allclose(lat, reference_lat, equal_nan=True)
                or not np.allclose(lon, reference_lon, equal_nan=True)
            ):
                raise ValueError(
                    f"La grilla de {path.name} no coincide con la grilla "
                    "de referencia. No se combinarán grillas distintas."
                )

            t25 = extract_field(ds, pm25_name)
            t10 = extract_field(ds, pm10_name)
            times = decode_times(ds, path)

            if not (len(t25) == len(t10) == len(times)):
                raise ValueError(
                    f"Número de tiempos y campos incompatible en {path.name}"
                )

            for stamp, f25, f10 in zip(times, t25, t10):
                if f25.shape != reference_shape or f10.shape != reference_shape:
                    raise ValueError(
                        f"Dimensiones espaciales incompatibles en {path.name}"
                    )

                records.append({
                    "time": stamp,
                    "pm25": np.asarray(f25, dtype=float),
                    "pm10": np.asarray(f10, dtype=float),
                    "source": path.name,
                })

    records.sort(key=lambda r: r["time"])

    timestamps = [r["time"] for r in records]
    if len(set(timestamps)) != len(timestamps):
        raise ValueError(
            "Hay marcas temporales duplicadas. Revísalas antes de generar "
            "productos horarios."
        )

    # Los campos de concentración se conservan por hora.
    # El AQI solo se calcula con 24 horas consecutivas válidas por celda.
    manifest = {
        "product": "IMPACT BASET",
        "source_model": "WRF-Chem",
        "units": "µg/m³",
        "timezone": "UTC",
        "grid": {
            "ny": int(reference_shape[0]),
            "nx": int(reference_shape[1]),
            "lat": reference_lat.tolist(),
            "lon": reference_lon.tolist(),
        },
        "variables": {
            "PM25": args.pm25_var or CANDIDATES["PM25"],
            "PM10": args.pm10_var or CANDIDATES["PM10"],
        },
        "times": [],
        "note": (
            "Concentraciones de modelo; verificar unidades, configuración "
            "y calidad antes de interpretación ambiental."
        ),
    }

    # Validación de continuidad temporal en intervalos de una hora.
    parsed_times = []
    from datetime import datetime

    for stamp in timestamps:
        parsed_times.append(datetime.fromisoformat(stamp))

    for i, rec in enumerate(records):
        hourly = {
            "time": rec["time"],
            "source": rec["source"],
            "PM25": concentration_json(rec["pm25"]),
            "PM10": concentration_json(rec["pm10"]),
            "AQI_PM25": None,
            "AQI_PM10": None,
            "aqi_status": "Se requieren 24 horas consecutivas válidas",
        }

        if i >= 23:
            window = records[i - 23:i + 1]
            expected = [
                parsed_times[i] - __import__("datetime").timedelta(hours=h)
                for h in range(23, -1, -1)
            ]
            actual = parsed_times[i - 23:i + 1]

            if actual == expected:
                for key in ("pm25", "pm10"):
                    cube = np.stack([r[key] for r in window], axis=0)
                    valid = np.isfinite(cube) & (cube >= 0)
                    # No se sustituye ningún dato ausente por cero.
                    count = valid.sum(axis=0)
                    sums = np.where(valid, cube, 0).sum(axis=0)
                    means = np.divide(
                        sums, count,
                        out=np.full(reference_shape, np.nan),
                        where=count == 24,
                    )
                    aqi_key = "AQI_PM25" if key == "pm25" else "AQI_PM10"
                    hourly[aqi_key] = [
                        aqi_from_concentration(v, key.upper())
                        for v in means.ravel()
                    ]

                hourly["aqi_status"] = (
                    "AQI estimado a partir del promedio modelado de 24 horas"
                )

        out_file = OUT / f"hour_{i:04d}.json"
        out_file.write_text(
            json.dumps(hourly, separators=(",", ":"), allow_nan=False),
            encoding="utf-8",
        )

        manifest["times"].append({
            "time": rec["time"],
            "file": out_file.name,
            "source": rec["source"],
            "aqi_available": hourly["AQI_PM25"] is not None,
        })

        print(f"  -> {out_file.name}: {rec['time']}")

    manifest_path = OUT / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, separators=(",", ":"), allow_nan=False),
        encoding="utf-8",
    )

    print(f"\nManifest: {manifest_path}")
    print(f"Horas procesadas: {len(records)}")
    print(f"Grilla: {reference_shape[0]} filas x {reference_shape[1]} columnas")
    print("Proceso terminado.")


if __name__ == "__main__":
    main()
