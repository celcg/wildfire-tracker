# Plan prioritario: mapa experimental de detecciones VIIRS en Galicia

Fecha: 2026-10-09
Estado: planificación; implementación pendiente.
Prioridad: anterior al siguiente trabajo del plan principal (Milestone 1.3).
Plan general y estado global: [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md).

## 1. Objetivo y decisiones

Construir una pieza de portfolio reproducible que conecte ingeniería de datos,
evaluación de modelos y una demo geográfica dentro de Wildfire Tracker.

Decisiones confirmadas por el usuario:
- Demo histórica rigurosa primero; predicción diaria después.
- Plazo flexible. Priorizar servicios gratuitos; estudiar alternativas antes
  de asumir un coste inevitable.
- Funcionalidad separada y con prioridad superior al trabajo pendiente del plan
  principal. Sus hitos anteriores y su estado se conservan.

Etiqueta confirmada por el usuario: estimar la probabilidad de al menos una
detección válida VIIRS S-NPP por celda y día, incluyendo actividad persistente.
No equivale a probabilidad de inicio de incendio, número de incendios,
superficie quemada ni propagación. Si se requieren nuevos incendios, redefinir
etiquetas, fuentes y estimación antes de entrenar.

Ámbito inicial: Galicia, H3 resolución 5, un único instrumento (VIIRS a bordo de
S-NPP), fechas 2018–2025. Ampliar a 2012–2017 será un experimento posterior,
no un requisito para entregar el primer resultado.

## 2. Dos entregas con significado distinto

### A. Demo histórica reproducible (prioridad inmediata)

Evaluación retrospectiva con meteorología de reanálisis y datos FIRMS
archivados. Debe indicar si las variables describen el propio día objetivo
o días anteriores. Usar meteorología del propio día permite estudiar asociación,
pero el resultado se presentará como estimación retrospectiva, nunca como una
predicción que se hubiera podido emitir antes de ese día.

Para facilitar el paso a B, incluir un experimento con variables de días
anteriores. El desplazamiento temporal por sí solo no prueba disponibilidad
real: el reanálisis se publica con retraso y puede revisarse.

La UI inicial usará “Estimación histórica experimental”. Mostrar preferentemente
2025, generado por un modelo que no se haya ajustado con ese año.

### B. Predicción diaria experimental (fase posterior)

Definir primero hora de emisión, ventana objetivo y disponibilidad de cada
variable. Propuesta inicial: ejecución a las 18:00 UTC del día D, para el día
D+1 completo, 00:00–24:00 UTC. El horizonte cubre entre 6 y 30 horas desde
la emisión; no llamarlo horizonte fijo de 24 horas. La interfaz identificará
el día UTC y podrá mostrar la hora de emisión en hora local.

Temperatura, humedad y viento del día objetivo deben proceder de un pronóstico
emitido y publicado antes del corte. Para lluvia de los siete días completos
anteriores a la emisión, usar D-7 a D-1, excluyendo el día D incompleto,
y comprobar también el retraso de publicación de esos valores.

Guardar issued_at, available_at cuando exista, downloaded_at, valid_time,
modelo meteorológico y versión. Una fecha de inicialización anterior al corte
no garantiza por sí sola que el pronóstico ya estuviera publicado.

Los archivos de pronósticos de Open-Meteo no garantizan todas las variables
desde 2018. Auditar cobertura por modelo, variable y ejecución. Si no se puede
reconstruir lo disponible al emitir, limitar el periodo del experimento
operativo y reservar nuevos bloques temporales; no presentar la evaluación
con reanálisis como validación operativa. [S4–S6]

## 3. Encaje en el proyecto existente

Inspección realizada sobre la carpeta física “widlfire”:
- React 19, React Leaflet y Leaflet; conservar el mapa y el explorador accesible.
- FastAPI con módulos independientes y protección de solicitudes existente.
- Firebase Hosting, Cloud Run, Firestore y un histórico BigQuery con retención
  limitada. Ese histórico no sustituye el archivo 2018–2025 de entrenamiento.
- Los mapas actuales no dependerán del nuevo modelo, proveedor meteorológico,
  job ni almacenamiento de predicciones.

Organización propuesta (crear durante la implementación):
- ml/: preparación, características, entrenamiento, evaluación e inferencia.
- ml/config/: fuentes, periodos, filtros, semilla y contrato de variables.
- ml/notebooks/: exploración y lectura de resultados; la lógica reproducible
  reside en módulos ejecutables.
- backend/risk_models.py, risk_repository.py y risk_routes.py: contrato,
  lectura de artefactos y router.
- frontend: cliente, hook y capa propios para riesgo histórico.
- data/ y artifacts/: ignorados por Git salvo pequeñas muestras de prueba;
  el código, manifiestos sin secretos y resultados agregados sí se versionan.

Separar dependencias de ML y del job de las del servidor público. Servir un
GeoJSON precomputado evita cargar XGBoost y el entorno geoespacial en cada
arranque del API. El Dockerfile del job no obliga a cambiar el despliegue
actual del backend mediante source builds.

La primera tarea tiene su diseño ejecutable en
[DATA_ENGINEERING_SUBPLAN.md](DATA_ENGINEERING_SUBPLAN.md). Ese documento fija
la arquitectura local, módulos, contratos, esquema Parquet, comandos, controles
y decisiones pendientes del piloto. En caso de discrepancia, este plan padre
define el objetivo y el subplan define la implementación de Data Engineering.

## 4. Fase 0 — Contrato del experimento (2–3 horas)

- [ ] Confirmar etiqueta y distinguir explícitamente estimación retrospectiva
  de predicción emitida por adelantado.
- [ ] Fijar calendario UTC, filtros, variables, fuentes y versiones en configuración.
- [ ] Verificar acceso al archivo FIRMS, una muestra meteorológica y límite
  administrativo oficial de Galicia con licencia y versión documentadas.
- [ ] Medir filas, celdas, peticiones y almacenamiento con una muestra pequeña.
- [ ] Comprobar condiciones y cuotas vigentes; usar caché y lotes acotados.
- [ ] Registrar las decisiones antes de consultar resultados de 2025.

Salida: ficha del experimento y muestra que demuestre que las fuentes encajan.
No lanzar descargas masivas hasta validar esta muestra.

## 5. Semana/bloque 1 — Data Engineering (8–12 horas)

Subplan técnico: [DATA_ENGINEERING_SUBPLAN.md](DATA_ENGINEERING_SUBPLAN.md).

### Fuentes y etiquetas

FIRMS permite descargar el archivo histórico en CSV, JSON y Shapefile, con
S-NPP desde el 20 de enero de 2012. Para el MVP basta CSV 2018–2025 más el
margen temporal necesario para las variables de días anteriores. Conservar
producto, colección, fecha de descarga y checksum; no mezclar NRT y producto
científico estándar sin identificarlo. El archivo requiere autenticación
mediante Earthdata o correo. [S1]

- [ ] Conservar originales inmutables y manifiesto de descargas.
- [ ] Filtrar por el polígono de Galicia, no únicamente por un rectángulo.
- [ ] Comprobar esquema, instrumento, coordenadas, fecha, hora y duplicados.
- [ ] Propuesta: confianza nominal/alta; registrar exclusiones y sensibilidad
  al umbral. Verificar el campo de tipo antes de excluir fuentes térmicas
  no vegetales; no asumir que está en todos los archivos.
- [ ] Registrar fallos de descarga y periodos conocidos sin servicio.

La etiqueta es presencia de detección aceptada; varios píxeles del mismo
incendio siguen siendo un único positivo celda/día. Un cero significa ausencia
de detección registrada, no prueba de ausencia de fuego. El archivo de puntos
no certifica cielo despejado ni observación completa de cada celda.
Días con descarga incompleta o interrupción conocida tendrán etiqueta
desconocida y se excluirán del ajuste. No inferir interrupciones únicamente
porque un día no tenga puntos.

### Malla y meteorología

H3 resolución 5 tiene área media global de unos 252,9 km², pero el área varía
con la posición. Calcular número y superficie reales de las celdas gallegas;
no prometer resolución local de 253 km² exactos. [S2]

- [ ] Incluir todas las celdas que intersecan Galicia, también costa y frontera.
  No depender exclusivamente del centro de celda para decidir inclusión.
- [ ] Mantener el identificador H3 completo y recortar la geometría de dibujo
  al territorio; guardar superficie y fracción terrestre.
- [ ] Elegir un punto representativo terrestre para muestrear meteorología,
  documentando que aproxima una celda extensa. Deduplicar puntos del mismo
  píxel meteorológico y conservar las coordenadas efectivas devueltas.
- [ ] Empezar con un producto de reanálisis explícito, por ejemplo ERA5 de
  Open-Meteo, evitando cambios silenciosos de proveedor mediante best_match.
  Auditar resolución, unidades, cobertura y fechas. [S3]
- [ ] Construir el producto cartesiano de celdas y días, incluyendo ceros;
  dejar valores desconocidos diferenciados de cero.
- [ ] Ajustar imputación solo con entrenamiento. No interpolar etiquetas.

Entregables:
- dataset.parquet: clave única (h3_cell, target_date).
- grid.geojson: geometrías y metadatos de la malla.
- data_manifest.json y data_quality.json: procedencia, hashes, versiones,
  completitud, exclusiones y política de ausencia de observación.

Columnas mínimas: h3_cell, target_date, label_detection, detection_count,
label_status, meteo_source, temperaturas/humedad/viento/precipitación,
flags de calidad y versión del esquema. Los timestamps detallados de
procedencia pueden estar en tablas auxiliares enlazadas.

Aceptación: cero claves duplicadas; cuadrícula estable; conteos reconciliados
con originales; ningún hueco de descarga convertido silenciosamente en negativo.

## 6. Semana/bloque 2 — Machine Learning (10–14 horas)

### Variables y modelos

- [ ] Temperatura máxima, humedad relativa mínima/media, viento máximo a 10 m,
  lluvia acumulada en una ventana de siete días definida y estacionalidad
  cíclica (seno/coseno del día del año).
- [ ] Separar en configuración variantes contemporáneas y retardadas.
  Nunca incluir detecciones, FRP u otros derivados del día objetivo como entrada.
- [ ] Baseline de prevalencia global y baseline estacional espacial:
  frecuencia celda/mes suavizada hacia la frecuencia mensual de Galicia,
  calculada exclusivamente con entrenamiento.
- [ ] Regresión logística con pipeline de imputación y escalado.
- [ ] XGBoost con búsqueda pequeña y reproducible; ajustar pesos de clase
  únicamente con entrenamiento y comprobar su efecto sobre calibración.
- [ ] Guardar orden, unidades y esquema de variables junto con el modelo.

### Separación temporal

Entrenamiento: 2018–2023. Validación: 2024. Test reservado: 2025.

Ajustar hiperparámetros con bloques temporales dentro de 2018–2023.
Generar predicciones fuera de muestra temporales para ajustar el calibrador
(por ejemplo, sigmoide); así 2024 queda disponible para elegir la variante final
sin ajustar el calibrador sobre el mismo conjunto donde se evalúa.
No hacer split aleatorio de filas ni optimizar contra 2025.

Congelar fuentes, variables, hiperparámetros y calibración antes de abrir
el test. Si después se modifica el método, registrar que 2025 ya fue consultado
y reservar otro periodo para una nueva validación independiente. Añadir una
comprobación con separación temporal entre bloques para medir cuánto favorece
la persistencia de un mismo episodio a ambos lados de un corte.

### Métricas y criterio de éxito

- [ ] Average Precision (AP) como resumen principal de precision-recall;
  especificar esta definición en vez de alternar con área trapezoidal.
- [ ] Recall@Top10% diario: ordenar celdas válidas por puntuación, elegir
  ceil(0.10 × N) y desempatar por h3_cell; sumar positivos capturados y
  dividir por todos los positivos de los días evaluables.
- [ ] Informar también promedio diario en días con positivos; recall no
  definido en días sin positivos, sin convertirlo artificialmente en 1.
- [ ] Brier score, curva de fiabilidad, prevalencia y número de positivos.
- [ ] Desgloses por mes y zona; incertidumbre mediante remuestreo de bloques
  temporales, explicando que los píxeles/días de un incendio no son independientes.
- [ ] Comparar todos los modelos con idénticas filas y reglas.

No prometer una precisión mínima antes de ver los datos. Promover XGBoost
solo si aporta una mejora defendible frente a los baselines en validación
y una calibración aceptable; si no, conservar el modelo simple o presentar
el resultado negativo como hallazgo del portfolio. Publicar el test final
aunque contradiga la hipótesis inicial.

Entregables: modelo y preprocesamiento serializados, model_card.md,
metrics.json/CSV, notebook de evaluación y comando reproducible de entrenamiento.
Aceptación: resultados regenerables con configuración, dependencias y semilla
fijadas, tolerancias numéricas documentadas y test sin uso durante el ajuste.

## 7. Semana/bloque 3 — API y demo histórica (6–9 horas)

- [ ] Añadir lectura de artefactos precomputados a FastAPI y contrato Pydantic.
- [ ] Contrato público propuesto: GET /api/v1/risk?date=2025-08-15.
  Una fecha solo devuelve el artefacto existente para esa fecha y modo.
- [ ] Resolver explícitamente el prefijo: Vite elimina actualmente /api.
  Una opción compatible es router /v1/risk y alias /api/v1/risk en FastAPI,
  con el cliente usando la base existente + /v1/risk. Probar ambos entornos
  antes de congelar la ruta; evitar /api/api/v1/risk.
- [ ] GeoJSON FeatureCollection en WGS84, coordenadas [longitud, latitud].
  Cada feature tendrá h3_cell, score (0–1 o null), data_status.
  Metadatos de colección: target_date, mode, generated_at, model_version,
  dataset_version, feature_schema_version y, cuando corresponda,
  issued_at, valid_from, valid_to y weather_run.
- [ ] Distinguir datos inválidos, fecha sin artefacto y almacenamiento caído
  (422, 404 y 503 respectivamente). No devolver ceros como sustituto de fallo.
- [ ] Conservar App Check, limitación por cliente, CORS y request IDs existentes.
  GET nunca descarga años de datos ni entrena modelos.
- [ ] Añadir capa “Estimación histórica experimental”, selector de fechas
  disponibles, leyenda fija y ficha con versión, modo y fecha.
- [ ] Mantener detecciones y agrupaciones existentes; cargar riesgo solo al
  seleccionarlo, con cancelación y caché separada por fecha/modo/versión.
- [ ] Extender el explorador accesible con la misma información de las celdas.
  Al salir de Galicia indicar que no hay cobertura.
- [ ] Si falla una petición, mantener visible el artefacto anterior con su
  fecha real. Nunca presentarlo como resultado de la nueva fecha solicitada.

Aceptación: demo navegable con resultados reservados de 2025; carga, ausencia,
error y datos anteriores diferenciados; ninguna avería de riesgo bloquea el mapa.

## 8. Semana/bloque 4 — Operación posterior (8–12 horas)

Esta fase empieza tras entregar A y validar fuentes para B. La reconstrucción
de pronósticos históricos puede requerir trabajo adicional a esta estimación.

- [ ] Validar la disponibilidad temporal del apartado 2 y evaluar la diferencia
  entre entrenar con reanálisis e inferir con pronósticos.
- [ ] Job contenedorizado: obtener entradas acotadas, validar, inferir y publicar.
  Sin reentrenamiento automático diario.
- [ ] Almacenar salidas inmutables por fecha objetivo, emisión y versión;
  publicar el índice latest únicamente después de validar todo el artefacto.
- [ ] Idempotencia y control de concurrencia/precondiciones de escritura;
  reintentos acotados, timeout, tamaño máximo y política de retención.
- [ ] Cloud Scheduler puede invocar Cloud Run Jobs sin servidor permanente.
  La llamada a la API de Google usa OAuth de cuenta de servicio; no copiar
  sin más el OIDC del endpoint interno de ingesta existente. [S7]
- [ ] Bucket privado; el API solo lee y el job escribe con permisos mínimos.
  Las lecturas públicas no dependen de BigQuery.
- [ ] Separar fallos, retrasos y artefactos válidos; registrar métricas agregadas
  y fecha de última ejecución correcta, sin payloads ni secretos.
- [ ] Documentar ejecución manual, rollback de modelo y reproducción local.
- [ ] Revisar el coste conjunto de Scheduler, Run, Storage, compilaciones,
  registros y tráfico. Un presupuesto con alertas no impone un límite duro.

Primera alternativa gratuita: demo con artefactos estáticos precalculados y
pipeline ejecutable localmente. Automatización en infraestructura existente
solo si cuotas y consumo previsto encajan. Si no hay alternativa gratuita
viable, presentar coste y decisión antes de contratar o ampliar servicios.
No asumir que disponer de free tier garantiza una factura cero.

Aceptación: ejecuciones repetidas no duplican resultados; fallo meteorológico
no publica una nueva predicción falsa; modelo y datos de cada salida trazables;
recuperación probada y consumo documentado.

### Puerta obligatoria de autorización

Las fases 0–3 y la preparación local de la fase 4 no autorizan ningún despliegue
ni cambio en servicios externos. Se puede dejar lista y revisable la
infraestructura, los contenedores, los comandos y las pruebas, pero antes de
cualquier despliegue, activación o escritura cloud se preguntará directamente
al usuario. Esta puerta incluye Cloud Run, Firebase, Cloud Run Jobs, Cloud
Scheduler, Cloud Storage, BigQuery, Firestore, IAM, Secret Manager y workflows
de publicación. La autorización será específica para la acción preparada; una
aprobación para probar localmente no cuenta como aprobación de despliegue.

## 9. Verificación proporcionada

Durante esta planificación: inspección documental y git diff --check.

En implementación:
- Transformaciones: duplicados, costa/frontera, UTC, años bisiestos, ventanas,
  datos ausentes y separación temporal.
- Modelo: esquema idéntico al inferir, ausencia de variables futuras,
  serialización y cálculos de métricas sobre ejemplos conocidos.
- API/UI: contrato GeoJSON, fechas disponibles, seguridad existente,
  cancelación, navegación accesible y aislamiento de fallos.
- Job: reintentos, idempotencia, publicación completa y recuperación.
- Servicios externos simulados: las pruebas no consumen NASA ni escriben en
  Firestore, BigQuery o Cloud Storage.

Respetar TESTING.md. El backend existente usa unittest: no introducir Pytest
solo por aparecer en el plan inicial; valorar su uso aislado en ML si aporta
ventajas. Suites completas solo para cambios críticos o cierre de hitos.

## 10. Esfuerzo, alcance y siguiente acción

Estimación orientativa propia, no plazo comprometido:
- Fase 0 + datos + modelos + demo: 26–38 horas.
- Operación posterior: 8–12 horas adicionales.
- Total base: 34–50 horas, más esperas de proveedores o reconstrucción compleja
  de pronósticos. Los bloques no obligan a cuatro semanas naturales.

Fuera del MVP: inicios confirmados, propagación, perímetros, alertas,
multisatélite, H3 más fino, toda la península, reentrenamiento automático y
nuevas capas de vegetación. Cada ampliación necesita su propio experimento.

Siguiente acción al iniciar implementación: formalizar la etiqueta acordada, obtener una
muestra pequeña FIRMS + meteorología, generar la malla y publicar el primer
informe de calidad. No comenzar por XGBoost ni por infraestructura.

## 11. Fuentes técnicas contrastadas (2026-10-09)

- [S1: NASA FIRMS Archive Download](https://firms.modaps.eosdis.nasa.gov/download/)
  — cobertura temporal, formatos, acceso y distinción NRT/estándar.
- [S2: H3, estadísticas por resolución](https://h3geo.org/docs/core-library/restable/)
  — área media y variación espacial.
- [S3: Open-Meteo Historical Weather](https://open-meteo.com/en/docs/historical-weather-api)
  — reanálisis y selección de producto.
- [S4: Open-Meteo Historical Forecast](https://open-meteo.com/en/docs/historical-forecast-api)
  — archivo de pronósticos y cobertura por modelo.
- [S5: Open-Meteo Previous Runs](https://open-meteo.com/en/docs/previous-runs-api)
  — desfase de pronóstico y disponibilidad histórica limitada.
- [S6: Open-Meteo Single Runs](https://open-meteo.com/en/docs/single-runs-api)
  — recuperación de una ejecución meteorológica concreta.
- [S7: Cloud Run Jobs con Scheduler](https://docs.cloud.google.com/run/docs/execute/jobs-on-schedule)
  — ejecución programada y autenticación.
- [S8: Condiciones de Open-Meteo](https://open-meteo.com/en/terms)
  — uso gratuito sujeto a finalidad y cuotas; verificar encaje antes de descargar.

Los detalles de diseño, criterios y estimaciones de este documento son
propuestas para este proyecto, no garantías de los proveedores.
