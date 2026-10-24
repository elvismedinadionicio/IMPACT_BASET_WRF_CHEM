# IMPACT_BASET_WRF_CHEM

### Plataforma de Pronóstico Basado en Impactos mediante WRF-Chem

## Descripción

**IMPACT_BASET_WRF_CHEM** es una plataforma web orientada a la visualización de pronósticos de calidad del aire y al análisis de impactos potenciales en la población y el territorio, utilizando los resultados del modelo numérico de predicción meteorológica y química atmosférica WRF-Chem (*Weather Research and Forecasting Model coupled with Chemistry*).

El proyecto busca transformar las salidas del modelamiento atmosférico en productos de información ambiental que faciliten la interpretación de escenarios de contaminación y apoyen la toma de decisiones.

## Objetivo general

Desarrollar una plataforma web interactiva para visualizar los pronósticos de contaminantes atmosféricos generados por WRF-Chem, analizar su evolución espacio-temporal e incorporar progresivamente indicadores de exposición y pronóstico basado en impactos.

## Funcionalidades previstas

- **Visualización cartográfica:** mapas interactivos de las concentraciones pronosticadas de contaminantes atmosféricos.
- **Consulta temporal:** selección de fechas, horas y periodos de pronóstico.
- **Análisis de contaminantes:** visualización de PM₂.₅, PM₁₀ y otras variables disponibles en las simulaciones.
- **Series temporales:** gráficos de la evolución de las concentraciones en ubicaciones seleccionadas.
- **Evaluación de impactos potenciales:** identificación de zonas expuestas y análisis territorial mediante información geográfica complementaria.
- **Pronóstico basado en impactos:** generación de indicadores y productos orientados a la interpretación de escenarios de riesgo ambiental.
- **Publicación de resultados:** disponibilidad de productos seleccionados mediante una interfaz web accesible.

Las funcionalidades se implementarán progresivamente, de acuerdo con la disponibilidad de datos, las capacidades del modelo y los criterios técnicos aplicables.

## Arquitectura del sistema

La arquitectura prevista contempla tres componentes principales:

1. **Procesamiento en NUNA:** ejecución de WRF-Chem y procesamiento de sus salidas.
2. **Generación de productos:** preparación de mapas, series temporales e indicadores de impacto en formatos adecuados para su publicación.
3. **Plataforma web:** visualización interactiva de los productos mediante una aplicación web estática, con GitHub Pages como opción de alojamiento.

Los archivos de salida completos del modelo se mantendrán en el entorno de procesamiento. Solo se publicarán los productos necesarios y autorizados.

## Tecnologías previstas

- WRF-Chem para el modelamiento meteorológico y químico atmosférico.
- Python para el procesamiento y análisis de resultados.
- HTML, CSS y JavaScript para el desarrollo de la interfaz web.
- Leaflet para la visualización cartográfica interactiva.
- GitHub para el control de versiones y la gestión del código fuente.
- GitHub Pages para el alojamiento de la plataforma web.

La selección definitiva de tecnologías y formatos de datos podrá ajustarse durante el desarrollo.

## Estructura prevista

```text
IMPACT_BASET_WRF_CHEM/
├── index.html
├── assets/
│   ├── css/
│   ├── js/
│   └── img/
├── data/
│   └── products/
├── scripts/
│   └── processing/
└── README.md
```

Esta estructura es referencial y podrá modificarse conforme se implementen los componentes de la plataforma.

## Alcance y consideraciones

Los resultados presentados corresponderán a productos derivados de un modelo numérico y estarán sujetos a sus incertidumbres y limitaciones. La identificación de impactos requerirá información complementaria, criterios de evaluación documentados y, cuando corresponda, datos de exposición y vulnerabilidad.

La plataforma no sustituye las evaluaciones sanitarias, las alertas oficiales ni los procedimientos institucionales de emisión de pronósticos.

## Estado del proyecto

**En desarrollo.** Se encuentra en la etapa inicial de diseño de la arquitectura y construcción de la interfaz web.

## Licencia

La licencia y las condiciones de reutilización del código y los datos se definirán de acuerdo con las autorizaciones correspondientes.

