#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT="/home/sea/proyectos/IMPACT_BASET_WRF"
cd "$PROJECT"

mkdir -p logs data/wrfchem

LOG="logs/procesamiento_$(date -u +%Y%m%dT%H%M%SZ).log"

echo "IMPACT BASET - Inicio del procesamiento WRF-Chem"
echo "Proyecto: $PROJECT"
echo "Log: $LOG"

ARGS=()

if [[ -n "${PM25_VAR:-}" ]]; then
  ARGS+=(--pm25-var "$PM25_VAR")
fi

if [[ -n "${PM10_VAR:-}" ]]; then
  ARGS+=(--pm10-var "$PM10_VAR")
fi

if ! python scripts/procesar_wrfchem.py "${ARGS[@]}" 2>&1 | tee "$LOG"; then
  echo "ERROR: falló el procesamiento. Revisa $LOG" >&2
  exit 1
fi

test -s data/wrfchem/manifest.json

echo
echo "Procesamiento finalizado."
echo "Manifest: $PROJECT/data/wrfchem/manifest.json"
echo "Visor: $PROJECT/impact.html"
echo "Log: $PROJECT/$LOG"
