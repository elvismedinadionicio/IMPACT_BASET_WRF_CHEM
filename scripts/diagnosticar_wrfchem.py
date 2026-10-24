#!/usr/bin/env python3
from pathlib import Path
import xarray as xr

ROOT = Path(
    "/home/sea/WRF_CHEM/PERU_20240909/"
    "RUN_CAMS_MOZCART_20240908"
)

files = sorted(ROOT.glob("wrfout_d01_*"))

if not files:
    raise SystemExit(f"No se encontraron archivos en {ROOT}")

print(f"Archivos encontrados: {len(files)}")

for path in files:
    print(f"\n{'=' * 75}\n{path.name}")

    try:
        with xr.open_dataset(path, decode_times=False) as ds:
            print("\nDimensiones:")
            print(dict(ds.sizes))

            print("\nVariables relacionadas con partículas:")
            for name, var in ds.data_vars.items():
                key = name.upper()
                if any(word in key for word in (
                    "PM25", "PM2_5", "PM10", "DUST",
                    "AER", "P25", "P10"
                )):
                    print(
                        f"{name}: dims={var.dims}, "
                        f"shape={var.shape}, "
                        f"units={var.attrs.get('units', 'NO DEFINIDA')}, "
                        f"description={var.attrs.get('description', '')}"
                    )

            print("\nVariables temporales y geográficas:")
            for name in ("Times", "XTIME", "XLAT", "XLONG"):
                if name in ds.variables:
                    var = ds[name]
                    print(
                        f"{name}: dims={var.dims}, shape={var.shape}, "
                        f"units={var.attrs.get('units', 'NO DEFINIDA')}"
                    )

    except Exception as exc:
        print(f"ERROR al leer el archivo: {exc}")
