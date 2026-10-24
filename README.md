# IMPACT_BASET_WRF_CHEM

### Plataforma de Pronóstico Basado en Impactos mediante WRF-Chem

## Descripción

Plataforma web para visualizar pronósticos de calidad del aire y analizar impactos potenciales en la población y el territorio, a partir de resultados del modelo WRF-Chem (*Weather Research and Forecasting Model coupled with Chemistry*).

La aplicación permite visualizar concentraciones modeladas de PM10 y PM2.5 mediante datos horarios procesados previamente.

## Estructura del proyecto

- `index.html`: página principal.
- `impact.html`: interfaz de visualización.
- `data/wrfchem/manifest.json`: metadatos y horas disponibles.
- `data/wrfchem/hour_XXXX.json`: datos procesados por hora.
- `scripts/diagnosticar_wrfchem.py`: diagnóstico de variables, unidades y dimensiones.
- `scripts/procesar_wrfchem.py`: procesamiento de grillas horarias.
- `scripts/ejecutar.sh`: ejecución del procesamiento.

## Datos de entrada

Directorio local de procesamiento:

`/home/sea/WRF_CHEM/PERU_20240909/RUN_CAMS_MOZCART_20240908`

Esta ruta corresponde al entorno de NUNA y no forma parte de los archivos estáticos publicados en GitHub Pages.

## Procesamiento

1. Revisar las variables disponibles mediante el diagnóstico.
2. Verificar las variables seleccionadas y sus unidades.
3. Ejecutar `scripts/ejecutar.sh`.
4. Comprobar los archivos horarios generados.
5. Probar la aplicación mediante un servidor HTTP local.

Si los nombres de las variables no se detectan automáticamente, pueden configurarse así:

```bash
PM25_VAR=nombre_variable_pm25 \
PM10_VAR=nombre_variable_pm10 \
bash scripts/ejecutar.sh
```

Los nombres anteriores son ejemplos y deben sustituirse por los nombres reales confirmados en el diagnóstico.

## Publicación web

GitHub Pages publica archivos estáticos. No ejecuta directamente los scripts Python ni los procesos de modelamiento. Para actualizar la aplicación, primero se procesan los datos en NUNA y luego se publican los archivos actualizados.

## Consideraciones sobre el AQI

El AQI estimado requiere 24 horas consecutivas válidas por celda. Los datos faltantes no se sustituyen por cero. Los resultados del modelamiento no constituyen, por sí solos, mediciones oficiales de calidad del aire.

## Seguridad

- No modificar los archivos del proyecto SORIAN.
- No ejecutar procesos con privilegios de administrador sin una necesidad operativa justificada.
- Verificar que los archivos publicados no contengan información sensible ni archivos internos innecesarios.
