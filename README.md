# IMPACT BASET - WRF-Chem

Aplicación independiente para visualizar concentraciones modeladas
de PM10 y PM2.5.

## Estructura

- impact.html: interfaz web independiente.
- scripts/diagnosticar_wrfchem.py: inventario de variables, unidades y dimensiones.
- scripts/procesar_wrfchem.py: procesamiento de grillas horarias.
- scripts/ejecutar.sh: ejecución controlada del procesamiento.
- data/wrfchem/manifest.json: metadatos y lista de horas.
- data/wrfchem/hour_XXXX.json: datos por hora.
- logs/: registros de ejecución.

## Entrada

/home/sea/WRF_CHEM/PERU_20240909/RUN_CAMS_MOZCART_20240908

## Ejecución

1. Revisar las variables con el diagnóstico.
2. Verificar que las variables seleccionadas están expresadas en µg/m³.
3. Ejecutar scripts/ejecutar.sh.
4. Abrir el visor mediante un servidor HTTP local.

Si los nombres de las variables no se detectan automáticamente:

PM25_VAR=nombre_variable_pm25 \
PM10_VAR=nombre_variable_pm10 \
bash scripts/ejecutar.sh

Los nombres anteriores son ejemplos: sustituirlos por los nombres
reales confirmados en el diagnóstico.

## AQI

El AQI estimado requiere 24 horas consecutivas válidas por celda.
Los datos faltantes no se sustituyen por cero. El producto de modelamiento
no constituye una medición oficial de calidad del aire.

## Seguridad

Este proyecto no modifica los archivos de SORIAN.
No ejecutar con privilegios de administrador salvo que exista
una necesidad operativa justificada.
