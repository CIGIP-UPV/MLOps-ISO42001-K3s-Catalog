# Addendum: interfaz de retroalimentación (CMP-12)

Complemento del [informe de validación en laboratorio](./INFORME_VALIDACION_LAB.md). Aquel informe dejó un único componente de la arquitectura de referencia sin chart: **CMP-12 Feedback Interface**, del nivel de empresa, recomendado, con las cláusulas B.6.1.3.3 (supervisión humana y retroalimentación) y B.6.2.6.4 (reentrenamiento y ciclo de vida), y soporte del requisito RN-02 (una persona puede supervisar, interrumpir y corregir las decisiones del sistema). Este addendum recoge su diseño, su implementación en el chart `enterprise-feedback-interface` y su validación en el mismo clúster de laboratorio, rama `feat/cmp12-feedback-interface`.

**Resumen**

| Aspecto | Resultado en el laboratorio |
|---|---|
| Instalación | 9 charts instalados o actualizados sin fallos y sin reiniciar las bases de datos; después, 2 más con las correcciones |
| Interfaz (S21) | Salud correcta; sin sesión, sin rol o con contraseña errónea, acceso denegado; operario, acceso concedido |
| Bucle de retroalimentación (E17 a E21) | 5 de 5: veredicto sobre una predicción real, panel de desacuerdo en Grafana, veredictos como etiquetas del entrenamiento, suspensión y reanudación de la versión en el edge, eventos en Loki |
| Conductos de red (N14 a N18) | 5 de 5, incluida la restricción por pod dentro de un namespace |
| Trazabilidad | CMP-12 pasa de 0 a 3 recursos; las 19 cláusulas y los 15 componentes devuelven recursos |
| Pruebas unitarias (local) | 18 de 18 |

La validación destapó un fallo previo del laboratorio que el informe principal no recoge: desde que el nodo de plataforma empezó a aplicar NetworkPolicy, la consolidación programada del edge fallaba en cada ejecución. Se describe en la sección 8, con su corrección.

**Origen de los datos.** Las secciones 3 a 6 proceden de ejecuciones de `run-lab-validation.sh` en el laboratorio (`raw/<ejecución>/`, con el comando de cada prueba en `results.jsonl`) y del diagnóstico `raw/diag-conduits-20260924T194048.txt`; las pruebas unitarias, del clúster local (`local-evidence/`). Las IP públicas de los nodos se sustituyeron por marcadores, como en el informe principal.

## 1. Diseño aprobado y decisiones

| Decisión | Elegida | Alternativa descartada y motivo |
|---|---|---|
| Tecnología | FastAPI con páginas HTML generadas en el servidor (Jinja2), sin JavaScript, sobre la imagen `ghcr.io/burakince/mlflow:2.22.1` que ya usa el catálogo, con el código en un ConfigMap | Streamlit sobre `python:3.12-slim`: exige instalar paquetes al arrancar (salida a PyPI, que la denegación por defecto no permite) y usa websockets, que complican la autenticación; la imagen del catálogo ya trae FastAPI, Jinja2, psycopg2, PyJWT y prometheus_client |
| Datos | Lee las predicciones consolidadas en la plataforma (TimescaleDB) y escribe los veredictos en una tabla nueva de la plataforma, `operator_feedback`, de solo alta | Escribir en la tabla del edge y consolidarla: exigiría un conducto de empresa hacia el edge, que cruza zonas, hacia un nodo que no aplica NetworkPolicy |
| Etiquetas para el entrenamiento | Se guardan las entradas de cada predicción (`predictions.features`, en el edge y en la plataforma); el entrenamiento une el último veredicto de cada predicción con sus entradas y mide la concordancia de la versión candidata con los operarios, que puede bloquear su liberación | Unir veredictos y datos por máquina y hora: aproximado, porque la predicción no guardaba sus entradas |
| Suspensión (opcional, incluida) | Etiqueta `suspended` en la versión del registro de MLflow; `edge-mlflow-sync` la propaga y el servidor del edge responde 503 | Un conducto nuevo de empresa al edge para ordenar la suspensión: cruza zonas; el registro ya es el punto único de control de versiones |
| Autenticación | Keycloak, realm `ai-system`, cliente nuevo `feedback-interface`: la interfaz envía las credenciales desde el servidor y verifica firma y roles del token (`operator` registra veredictos; `production-manager` y `compliance-officer` también suspenden) | Flujo con redirección del navegador: necesita Keycloak publicado con TLS, que el laboratorio no tiene (Traefik desactivado); el envío de credenciales desde el servidor está desaconsejado por OAuth 2.1 y queda como limitación |
| Esquema de las bases de datos | Jobs de migración idempotentes (hooks de Helm) en `platform-timescaledb` y `edge-postgresql`, sin tocar los scripts de arranque | Cambiar los scripts de arranque: solo se ejecutan en el primer arranque y, en TimescaleDB, modificarlos reinicia la base de datos |

**Flujo.** Predicción en el edge (con sus entradas) → consolidación a la plataforma → la interfaz la lista → el operario registra su veredicto en `operator_feedback` → el cuadro *ZDM: Operator Feedback (CMP-12)* muestra el desacuerdo por versión → el siguiente entrenamiento usa los veredictos como etiquetas. Un supervisor puede además suspender la versión en servicio: etiqueta en el registro → `edge-mlflow-sync` → el servidor del edge deja de servirla.

**Red.** Namespace nuevo `feedback`, con denegación por defecto; solo puede salir hacia los pods de TimescaleDB (5432), Keycloak (8080) y MLflow (5000), restringidos por pod, y solo recibe tráfico de `monitoring` (métricas) y `kube-system`.

## 2. Metadatos del chart

| Campo | Valor |
|---|---|
| Chart | enterprise-feedback-interface |
| Versión (app) | 0.3.0 (1.0.0) |
| Imagen | ghcr.io/burakince/mlflow:2.22.1 (la misma que el servidor del modelo y el entrenamiento; código en un ConfigMap) |
| Dependencia de terceros | ninguna (chart propio) |
| Nivel | empresa |
| Namespace | feedback |
| Categoría | Human Oversight |
| Componentes | CMP-12 |
| Cláusulas ISO/IEC 42001 | B.6.1.3.3, B.6.2.6.4 |
| Ruta | catalog/enterprise/human-oversight/feedback-interface |

**Charts modificados para el componente:**

| Chart | Cambio |
|---|---|
| platform-timescaledb | Esquema idempotente (`files/schema.sql`) aplicado por un Job tras cada instalación o actualización: columna `predictions.features`, tabla `operator_feedback`, rol `feedback` y permisos |
| edge-postgresql | Job de migración: columna `predictions.features` |
| edge-fastapi-model | Guarda las entradas de cada predicción; responde 503 mientras la versión está suspendida |
| edge-postgresql-sync | Consolida las entradas; espera a las bases de datos y detiene la tabla si falla un paso (sección 8) |
| edge-mlflow-sync | Propaga la suspensión; ejecuciones serializadas con un cerrojo (sección 8) |
| platform-training-jobs | Veredictos como etiquetas: concordancia con los operarios y criterio de liberación `releaseCriteria.feedback` |
| enterprise-keycloak | Cliente `feedback-interface`; corrección del scope inexistente `openid` (sección 8) |
| enterprise-grafana-dashboards | Cuadro *ZDM: Operator Feedback (CMP-12)* |
| infrastructure/ | Namespace `feedback`, 8 NetworkPolicy nuevas, `install.sh` en la fase de empresa y alta de claves nuevas en Secrets existentes |

## 3. Resultado de la instalación

Comando: `run-lab-validation.sh --phases "3 ..." --edge-nodes edgenode01 --skip-chart platform-argocd --skip-chart edge-mongodb --only-chart ...` (fase 3, que ejecuta `install.sh` con `--only` por chart y `--separate-tiers`). Fuente: `install.jsonl` de cada ejecución.

| Ejecución | Chart | Namespace | Resultado | Tiempo (s) | Pods listos |
|---|---|---|---|---|---|
| lab-20260924T175818 | enterprise-keycloak | security | correcto | 29 | 1/1 |
| lab-20260924T175818 | platform-timescaledb | platform | correcto | 47 | 1/1 |
| lab-20260924T175818 | platform-training-jobs | mlops | correcto | 1 | 0/0 |
| lab-20260924T175818 | edge-postgresql | edge | correcto | 7 | 1/1 |
| lab-20260924T175818 | edge-fastapi-model | edge | correcto | 15 | 1/1 |
| lab-20260924T175818 | edge-mlflow-sync | edge | correcto | 1 | 1/1 |
| lab-20260924T175818 | edge-postgresql-sync | edge | correcto | 0 | 0/12 |
| lab-20260924T175818 | enterprise-grafana-dashboards | monitoring | correcto | 1 | 0/0 |
| lab-20260924T175818 | enterprise-feedback-interface | feedback | correcto | 16 | 1/1 |
| lab-20260924T195147 | platform-timescaledb | platform | correcto | 9 | 1/1 |
| lab-20260924T195147 | edge-postgresql-sync | edge | correcto | 1 | 0/11 |

- Las bases de datos no se reiniciaron: tras la actualización, `platform-timescaledb-0` y `edge-postgresql-0` seguían con 0 reinicios y 9 horas de vida (`raw/lab-20260924T175818/state/final-pods.txt`); los cambios de esquema los aplicaron los Jobs de migración, que terminaron en `Completed`.
- El Secret `platform-timescaledb-auth` recibió la clave nueva `feedback-password` sin cambiar las existentes (`install.log`: «kept, added feedback-password»).
- El pod de la interfaz corre en `worker1-kb2`, el nodo de los niveles de plataforma y empresa.
- «Pods listos 0/12» y «0/11» en `edge-postgresql-sync` son pods de ejecuciones fallidas de la consolidación, anteriores a su corrección (sección 8).
- La primera ejecución se detuvo tras instalar por un fallo del propio script (una comprobación con `grep -q` bajo `pipefail`), corregido en el commit d18689c; la segunda ejecutó las fases 6 y 8.

## 4. Pruebas de la interfaz y del bucle de retroalimentación

Ejecución de referencia `raw/lab-20260924T202458` (fase 8). Pruebas unitarias de la aplicación: 18 de 18 correctas, en local (`local-evidence/cmp12-unit-tests.txt`).

| ID | Prueba | Resultado | Tiempo (s) | Comando | Evidencia resumida |
|---|---|---|---|---|---|
| S21 | Feedback interface health, sign-in and denied access without credentials | PASS | 5 | GET /healthz; GET / and /api/predictions and POST /feedback without session; sign-in with a wrong password, without role, as operator | `/healthz` 200; sin sesión, `/` redirige a `/login` y la API y el envío de veredictos responden 401; contraseña errónea, 401; usuario sin rol de la interfaz (`data-scientist`), 403; `lab-operator` entra con el rol `operator` y sin permiso de suspensión; 7 de 7 |
| E17 | Operator verdict on a real prediction, stored in the platform data stock | PASS | 14 | POST edge /predict; job edge-postgresql-sync; GET /api/predictions; POST /feedback (lab-operator); psql operator_feedback | Predicción real de la versión 5 (máquina cnc-01), consolidada en el lote 98; `lab-operator` la marca como incorrecta (etiqueta corregida `anomaly`, comentario); fila 2 de `operator_feedback` con la versión, la etiqueta predicha y el operario tomados del servidor |
| E18 | Verdict in the Grafana panel of disagreement rate by model version | PASS | 2 | GET /api/dashboards/uid/zdm-operator-feedback; POST /api/ds/query with the SQL of the panel | La consulta del panel «Operator disagreement rate by model version», ejecutada por la API de Grafana, devuelve las versiones 5 y 3 con tasa de desacuerdo 1 (un veredicto incorrecto cada una) |
| E19 | Training uses the operator verdicts as labels | PASS | 16 | kubectl create job --from=cronjob/platform-training-jobs e2e-fb-train-1; feedback_labels_loaded | La plataforma tiene 7192 s de datos de cnc-01 en las últimas 2 horas; el entrenamiento carga 2 veredictos como etiquetas, mide una concordancia de 0,0 con los operarios (se informa, sin bloquear, en el laboratorio) y registra y promueve la versión 6 |
| E20 | Suspension of the version in service stops it at the edge; resuming restores it | PASS | 67 | POST /models/suspend (lab-supervisor); job edge-mlflow-sync; POST edge /predict (503); POST /models/resume; job; /predict (200) | `lab-supervisor` suspende la versión 6; el edge la marca como suspendida (la ejecución programada de `edge-mlflow-sync` se adelantó a la manual, que la encontró ya suspendida) y `/predict` responde 503; tras reanudar, 200; `model_versions` registra `suspended` y `resumed` |
| E21 | Events of the feedback loop in Loki | PASS | 26 | LogQL count_over_time per event in namespaces feedback, edge, mlops and platform | Loki contiene los 9 tipos de evento: `feedback_recorded`, `login_succeeded`, `login_failed`, `model_suspended`, `model_resumed`, `version_suspended`, `version_resumed`, `feedback_labels_loaded` y `schema_applied` |

- E19 falló en la ejecución anterior (`raw/lab-20260924T195147`): la plataforma no tenía datos de las dos últimas horas porque la consolidación acababa de reanudarse tras la caída de la sección 8. Se repitió cuando la plataforma recuperó los datos; la prueba ahora espera a que la ventana de entrenamiento tenga datos.
- La concordancia de 0,0 no es un fallo: los veredictos de prueba contradicen deliberadamente la predicción (E17 marca como anomalía una predicción normal), y en el laboratorio el criterio solo informa (`minAgreement: 0`).
- La fase 8 crea tres usuarios de prueba en el Keycloak del catálogo (`lab-operator`, `lab-supervisor` y `lab-viewer`), con contraseñas aleatorias guardadas en el Secret `feedback/feedback-lab-users`, que ninguna evidencia contiene.

## 5. Trazabilidad por etiqueta iso42001

Fase 6 completa en `raw/lab-20260924T195147` (después de CMP-12), comparada con `raw/lab-20260924T081803` (validación de la versión 2.0.0). Recursos: pods, servicios, deployments y statefulsets con la etiqueta.

| Clave | Descripción | Antes | Después | Comando |
|---|---|---|---|---|
| B.6.1.2.2 | Resources: Monitoring Performance | 20 | 20 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.6.1.2.2 --no-headers |
| B.6.1.3.1 | Resources: Access Control | 14 | 14 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.6.1.3.1 --no-headers |
| B.6.1.3.2 | Resources: Version Control | 6 | 6 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.6.1.3.2 --no-headers |
| B.6.1.3.3 | Resources: Human Oversight / Feedback | 8 | 11 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.6.1.3.3 --no-headers |
| B.6.1.3.4 | Resources: Inventory / Registry | 8 | 8 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.6.1.3.4 --no-headers |
| B.6.1.4.1 | Resources: Security of AI Assets | 14 | 14 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.6.1.4.1 --no-headers |
| B.6.2.3.1 | Planning: System Documentation | 14 | 14 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.6.2.3.1 --no-headers |
| B.6.2.5.1 | Planning: Deployment Plan | 4 | 4 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.6.2.5.1 --no-headers |
| B.6.2.6.1 | Operation: Infrastructure Monitoring | 15 | 27 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.6.2.6.1 --no-headers |
| B.6.2.6.2 | Operation: Model Performance | 29 | 29 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.6.2.6.2 --no-headers |
| B.6.2.6.3 | Operation: KPI Assessment (OEE) | 8 | 10 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.6.2.6.3 --no-headers |
| B.6.2.6.4 | Operation: Retraining / Lifecycle | 28 | 32 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.6.2.6.4 --no-headers |
| B.6.2.6.5 | Operation: Update & Repair Plan | 1 | 1 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.6.2.6.5 --no-headers |
| B.6.2.6.6 | Operation: Incident Communication | 14 | 14 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.6.2.6.6 --no-headers |
| B.6.2.6.7 | Operation: Security Monitoring | 6 | 6 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.6.2.6.7 --no-headers |
| B.6.2.8.1 | Operation: Logging / Audit Trail | 41 | 52 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.6.2.8.1 --no-headers |
| B.8.0.2.1 | Continual Improvement: Roles | 10 | 10 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.8.0.2.1 --no-headers |
| B.8.0.4.1 | Continual Improvement: Helpdesk | 14 | 14 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.8.0.4.1 --no-headers |
| B.8.0.5.1 | Continual Improvement: Alerts | 37 | 37 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.8.0.5.1 --no-headers |
| CMP-01 | Input Data Monitoring | 17 | 17 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/CMP-01 --no-headers |
| CMP-02 | Data Stock | 21 | 33 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/CMP-02 --no-headers |
| CMP-03 | Version Control | 6 | 6 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/CMP-03 --no-headers |
| CMP-04 | Model | 5 | 6 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/CMP-04 --no-headers |
| CMP-05 | Document Store | 5 | 5 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/CMP-05 --no-headers |
| CMP-06 | Information Centre | 3 | 3 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/CMP-06 --no-headers |
| CMP-07 | User Access & Oversight | 10 | 10 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/CMP-07 --no-headers |
| CMP-08 | Infrastructure Technical Monitoring | 20 | 20 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/CMP-08 --no-headers |
| CMP-09 | Logger | 9 | 9 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/CMP-09 --no-headers |
| CMP-10 | Model Technical Performance Monitoring | 32 | 32 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/CMP-10 --no-headers |
| CMP-11 | Goal-Oriented Monitoring | 23 | 24 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/CMP-11 --no-headers |
| CMP-12 | Feedback Interface | 0 | 3 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/CMP-12 --no-headers |
| CMP-13 | AI Helpdesk | 14 | 14 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/CMP-13 --no-headers |
| CMP-14 | Retraining Recommendation | 8 | 9 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/CMP-14 --no-headers |
| CMP-15 | Security Monitoring | 20 | 20 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/CMP-15 --no-headers |
| iso42001=true | all catalog resources | 127 | 143 | kubectl get pods,svc,deploy,sts -A -l iso42001=true --no-headers |

CMP-12 pasa de 0 a 3 recursos (el pod, el Deployment y el Service de la interfaz) y B.6.1.3.3 de 8 a 11. Otras cuentas también crecen por motivos ajenos al componente: las consultas cuentan los pods de los Jobs, y entre las dos ejecuciones se acumularon pods de la consolidación (muchos de ellos de ejecuciones fallidas, sección 8), de los Jobs de migración y de las pruebas. En los namespaces del catálogo llevan `iso42001=true` 341 de 438 objetos (78 %); en el namespace nuevo `feedback`, 9 de 12; por la clasificación hecha en el clúster local, los objetos sin etiqueta de un namespace así son `kube-root-ca.crt`, la ServiceAccount `default` y el registro de la release de Helm, que no crea el chart.

## 6. Pruebas de red

Ejecución `raw/lab-20260924T202458`. Clientes en un nodo que aplica NetworkPolicy, tras esperar 15 s a la sincronización del controlador.

```
edgenode01: pod 10.42.2.63:8080 from another namespace: without policy CONNECTED, with a deny-all ingress policy CONNECTED
kb2: pod 10.42.0.107:8080 from another namespace: without policy CONNECTED, with a deny-all ingress policy NOT-CONNECTED
worker1-kb2: pod 10.42.1.51:8080 from another namespace: without policy CONNECTED, with a deny-all ingress policy NOT-CONNECTED
```

| ID | Prueba | Resultado | Nodo cliente | Nodo destino | Salida |
|---|---|---|---|---|---|
| N-CANARY | NetworkPolicies are enforced on every node (pod behind a deny-all policy) | FAIL | - | - | ver el bloque del canario |
| N14 | feedback -> platform TimescaleDB (feedback conduit) (expected: allow) | PASS | worker1-kb2 | worker1-kb2 | CONNECTED |
| N15 | feedback -> edge PostgreSQL (no conduit into the edge) (expected: deny) | PASS | worker1-kb2 | edgenode01 | destination on edgenode01, which does not enforce NetworkPolicies (N-CANARY); BLOCKED |
| N16 | feedback -> platform service PostgreSQL (same namespace as TimescaleDB, not allowed) (expected: deny) | PASS | worker1-kb2 | worker1-kb2 | BLOCKED |
| N17 | feedback -> Keycloak (sign-in conduit) (expected: allow) | PASS | worker1-kb2 | worker1-kb2 | CONNECTED |
| N18 | feedback -> MLflow (suspension tags) (expected: allow) | PASS | worker1-kb2 | worker1-kb2 | CONNECTED |

N15 queda bloqueada aunque su destino, la PostgreSQL del edge, corre en el nodo que no aplica NetworkPolicy: lo bloquea la regla de salida del namespace `feedback`, aplicada en el nodo del cliente. N16 muestra la restricción por pod: TimescaleDB y la PostgreSQL de servicios comparten el namespace `platform`, y la interfaz solo alcanza la primera.

## 7. Totales del catálogo y fila de la Tabla 30

**31 charts**: 13 de edge, 13 de plataforma y 5 de empresa. Desplegados en el laboratorio: 28 (los 27 de la validación de la versión 2.0.0 más `enterprise-feedback-interface`); siguen sin desplegar `platform-rancher`, `platform-argocd` y `edge-mongodb`, por los motivos del informe principal. Con este chart, los 15 componentes de la arquitectura tienen al menos un chart.

| Componente | Capa y nivel (arquitectura) | Criticidad | Chart(s) | Cláusulas | Recursos en el laboratorio | Cobertura |
|---|---|---|---|---|---|---|
| CMP-12 Feedback Interface | Entorno; empresa | Recomendado | enterprise-feedback-interface (empresa) | B.6.1.3.3, B.6.2.6.4 | 3 | cubierto: veredictos del operario sobre las predicciones consolidadas, usados como etiquetas por el entrenamiento, y suspensión de la versión en servicio |

## 8. Incidencias encontradas y correcciones

| Incidencia | Evidencia | Causa | Corrección |
|---|---|---|---|
| La consolidación programada fallaba en cada ejecución | Ejecuciones de `edge-postgresql-sync` en error desde las 10:00 UTC (`raw/lab-20260924T095847/state/final-pods.txt`) hasta las 19:52; `Connection refused` hacia TimescaleDB en `raw/diag-conduits-20260924T194048.txt`, mientras un pod de prueba del mismo namespace y nodo sí conectaba | Desde que `worker1-kb2` aplica NetworkPolicy (reinicio de su agente K3s por la mañana), su controlador tarda un instante en reconocer cada pod nuevo; la consolidación conectaba en los primeros milisegundos y se rechazaba. Además, un paso fallido no detenía el script, que seguía con valores vacíos | Espera de hasta un minuto a las dos bases de datos y parada de la tabla ante un paso fallido (commit 2da398c); las ejecuciones terminan bien desde la corrección |
| Dos sincronizaciones de versión simultáneas se pisaban | `download_failed` entre `downloaded` y `active` en E07 del informe principal y en el clúster local | La ejecución manual y la programada descargaban la misma versión en el mismo directorio temporal | Cerrojo sobre el almacén de modelos y directorio temporal propio de cada ejecución (commit 321288e) |
| Toda actualización de `enterprise-keycloak` fallaba | Job de importación del realm con `NullPointerException ... defaultClientScope is null` en el clúster local | El cliente de Grafana declaraba el scope `openid`, que no existe en Keycloak; solo falla cuando el realm ya existe | Scopes `profile` y `email` (commit 0b9ae33); la actualización del laboratorio pasó |
| El Job de migración de TimescaleDB se ejecutó en el nodo edge | `platform-timescaledb-schema` en `edgenode01` (`raw/lab-20260924T175818/state/final-pods.txt`) | Los hooks de Helm no pasan por el post-renderer, así que `--separate-tiers` no los alcanza | Preferencia por nodos sin la etiqueta edge en el propio Job (commit 58f9fba) |
| El script de validación se detuvo tras una instalación correcta, y E19 esperó 900 s a un Job ya fallido | `install.sh did not install any release` en `raw/lab-20260924T175818/run.log`; E19 de `raw/lab-20260924T195147` | `grep -q` bajo `pipefail` puede cortar la salida del comando anterior; la espera de los Jobs solo miraba la condición de completado | Recuento en lugar de `grep -q` y espera que termina también ante un fallo (commits d18689c y 1f53703) |

**Consecuencia para el informe principal.** Su prueba de extremo a extremo (a las 08:18–09:14 UTC) pasó antes de que el nodo de plataforma aplicara NetworkPolicy, y sus pruebas de red se hicieron con clientes que esperan antes de conectar. La combinación de ambas, la consolidación programada con políticas aplicadas en la plataforma, falló hasta esta corrección. El problema no está en las políticas del catálogo, que permiten el conducto, sino en la latencia del controlador de K3s ante pods de vida corta; el mismo retraso explica el resultado inicial de N08 descrito en aquel informe.

## 9. Limitaciones

- **Autenticación.** La interfaz envía las credenciales a Keycloak desde el servidor (concesión de contraseña), desaconsejada por OAuth 2.1; el flujo con redirección del navegador exige publicar Keycloak con TLS, que el laboratorio no tiene. La cookie de sesión no se marca como segura porque la interfaz se usó sin TLS, por port-forward.
- **Retraso de la retroalimentación.** El operario solo ve predicciones ya consolidadas: hasta 5 min con los valores por defecto (2 min en el laboratorio); la suspensión llega al edge en la siguiente sincronización (2 min por defecto, 1 en el laboratorio).
- **Etiquetas.** El modelo no es supervisado: los veredictos evalúan y pueden bloquear una versión, pero no entrenan el modelo. En el laboratorio se usaron 2 veredictos y el criterio solo informa; no se probó un bloqueo real de la liberación.
- **Dispositivo edge.** La suspensión se probó con el servidor del modelo en `edgenode01`; la tabla `operator_feedback` del edge sigue sin interfaz, reservada para una futura interfaz en planta.
- **Usuarios de prueba.** Los tres usuarios de prueba permanecen en el Keycloak del laboratorio y sus contraseñas en un Secret; conviene borrarlos si el clúster se usa para otra cosa.
- **Sin interfaz de usuario probada con navegador.** Las pruebas usan la API JSON de la misma aplicación, con la misma sesión y protección de formularios; las páginas HTML se probaron en las pruebas unitarias, no con un navegador en el laboratorio.

## Anexo. Ejecuciones

| Ejecución | Contenido |
|---|---|
| lab-20260924T175818 | fase 3: instalación o actualización de los nueve charts afectados; el script se detuvo después por un fallo propio (sección 8) |
| diag-conduits-20260924T194048.txt | diagnóstico de los conductos del edge nodo a nodo y registros de la consolidación fallida |
| lab-20260924T195147 | fases 3, 6 y 8: actualización de las dos correcciones, trazabilidad completa y primera ejecución de la fase 8 (E19 falló por falta de datos recientes en la plataforma) |
| lab-20260924T202458 | fase 8 de referencia: S21, E17 a E21, canario y N14 a N18 |
