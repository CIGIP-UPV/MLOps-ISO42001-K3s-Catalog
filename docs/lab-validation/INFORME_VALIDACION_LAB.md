# Informe de validación en laboratorio del catálogo AR-MLOps-ZDM

Validación del catálogo `MLOps-ISO42001-K3s-Catalog` (rama `lab-validation`) en el clúster K3s del laboratorio, como aportación de datos reales al capítulo 7 de la tesis. Los tres criterios del capítulo se evalúan así:

- **Instanciabilidad:** instalación de los charts con `infrastructure/install.sh` (sección 4), pruebas de humo por chart y prueba de extremo a extremo de los flujos (sección 5).
- **Coherencia:** separación de niveles en nodos distintos, flujos de consolidación de datos y de propagación de versiones, y segmentación de red entre zonas (secciones 3, 4 y 5).
- **Trazabilidad:** consultas por las etiquetas `iso42001` de cada cláusula y componente (sección 6).

**Resumen de resultados en el laboratorio**

| Criterio | Resultado |
|---|---|
| Instalación | 27 charts desplegados (28 ejecuciones de Helm: cert-manager hace dos pasadas) en 2336 s de install.sh (1550 s de Helm), sin fallos; 3 charts omitidos por motivos del entorno |
| Pruebas de humo | 18 correctas, 0 fallidas y 3 no ejecutadas (Falco en el dispositivo edge, Argo CD y MongoDB, por el entorno) |
| Extremo a extremo | 16 de 16 tramos: simulador OPC UA, pasarela, ingesta validada, consolidación, entrenamiento, registro, propagación al edge, inferencia, métricas, deriva inducida, recomendación, reentrenamiento automático, nueva versión servida en el edge, registros en Loki e informes en Evidently |
| Segmentación de red | 12 correctas (incluido el control N00), 1 fallida y 1 no ejecutada; aplican NetworkPolicy 2 de los 3 nodos, y el fallo se debe a que el dispositivo edge no puede aplicarlas (kernel sin `ip_set_hash_ip`) |
| Trazabilidad | Las 19 cláusulas y 14 de los 15 componentes devuelven recursos; CMP-12 no tiene chart |

**Origen de los datos.** Todo dato de las secciones 1 a 6 procede de ejecuciones en el laboratorio con `docs/lab-validation/run-lab-validation.sh`, cuyas evidencias están en `docs/lab-validation/raw/<ejecución>/` (una línea por prueba en `results.jsonl`, con el comando). Lo que procede del clúster local de desarrollo (Docker Desktop, kind, arm64) se indica expresamente y está en `docs/lab-validation/local-evidence/`. Las ejecuciones se listan en el anexo.


## 1. Entorno

| Elemento | Valor |
|---|---|
| K3s | k3s version v1.32.6+k3s1 (eb603acd) |
| Kubernetes (servidor) | v1.32.6+k3s1 |
| kubectl (cliente en kb2) | v1.29.0 |
| Helm (en kb2) | v3.19.0+g3d8990f |
| Rancher | gestionado por un Rancher externo; agente rancher/rancher-agent:v2.13.3 (no hay servidor Rancher en el clúster) |
| cert-manager previo | ninguno (lo instala el catálogo) |
| Red | flannel (K3s) con el controlador de NetworkPolicy de K3s (kube-router), activado para la validación |
| StorageClass | local-path (por defecto), provisioner rancher.io/local-path, reclaimPolicy Delete, WaitForFirstConsumer |
| Commit del catálogo en la instalación | d7d83a7a25937449d49717daebe5760cc094cef9 (lab-validation) |

Fuente: `raw/lab-20260924T081803/env/versions.txt` (generado con `k3s --version`, `kubectl version`, `helm version --short`) y los diagnósticos `raw/diag-*.txt` (`diagnose-cluster.sh`).

| Nodo | Función | SO y kernel | Arquitectura | CPU | RAM (GiB) | Uso antes / después de instalar / final |
|---|---|---|---|---|---|---|
| kb2 | plano de control (máquina virtual Hyper-V); solo DaemonSets del catálogo (taint NoSchedule) | Ubuntu 22.04.4 LTS, 5.15.0-190-generic | amd64 | 4 | 7.8 | 1769m CPU, 4034Mi / 1654m CPU, 4661Mi / 858m CPU, 4517Mi |
| worker1-kb2 | trabajador (Dell Precision 3640); niveles plataforma y empresa | Ubuntu 22.04.4 LTS, 6.8.0-138-generic | amd64 | 16 | 31.1 | 115m CPU, 1857Mi / 610m CPU, 6632Mi / 433m CPU, 7192Mi |
| edgenode01 | dispositivo edge (NVIDIA Jetson AGX Orin); nivel edge | Ubuntu 22.04.5 LTS, 5.15.148-tegra | arm64 | 8 | 61.4 | 1404m CPU, 6532Mi / 2108m CPU, 8511Mi / 823m CPU, 8797Mi |

Fuente: `env/nodes.json` (`kubectl get nodes -o json`) y `kubectl top nodes` en `env/node-usage-before.txt`, `state/after-install-top-nodes.txt` y `raw/lab-20260924T095847/state/final-top-nodes.txt`. Entre la medida posterior a la instalación y la final se eliminaron cargas ajenas del dispositivo edge (namespace ros2exp), con confirmación del usuario.


## 2. Catálogo final

**30 charts**: 13 de edge, 13 de plataforma y 4 de empresa (en `main` había 28: 11, 13 y 4). Todos en la versión 0.3.0 de la rama `lab-validation`.

| Nivel | Chart | Versión (app) | Dependencia de terceros | Namespace | Componentes | Cláusulas ISO/IEC 42001 | Laboratorio |
|---|---|---|---|---|---|---|---|
| edge | edge-fastapi-model | 0.3.0 (1.0.0) | propio | edge | CMP-04, CMP-10 | B.6.2.6.2, B.6.2.6.4 | instalado |
| edge | edge-kafka | 0.3.0 (3.6) | kafka 30.1.8 | edge | CMP-01 | B.6.2.6.4, B.6.2.8.1 | instalado |
| edge | edge-mosquitto | 0.3.0 (2.0) | propio | edge | CMP-01 | B.6.1.3.1, B.6.2.6.4 | instalado |
| edge | edge-rabbitmq | 0.3.0 (3.13) | propio | edge | CMP-01 | B.6.2.6.4, B.6.2.8.1 | instalado |
| edge | edge-node-red | 0.3.0 (3.1.3) | node-red 0.30.0 | edge | CMP-01 | B.6.2.6.4 | instalado |
| edge | edge-opc-ua-gateway | 0.3.0 (1.32.3) | propio | edge | CMP-01 | B.6.1.3.1, B.6.2.6.4 | instalado |
| edge | edge-fluent-bit | 0.3.0 (3.0) | fluent-bit 0.47.10 | logging | CMP-09 | B.6.2.8.1 | instalado |
| edge | edge-prometheus-agent | 0.3.0 (25.3) | prometheus 25.30.2 | edge | CMP-08, CMP-10 | B.6.1.2.2, B.6.2.6.1 | instalado |
| edge | edge-falco | 0.3.0 (0.37) | falco 4.22.0 | falco | CMP-15 | B.6.2.6.7, B.6.2.8.1 | instalado |
| edge | edge-mongodb | 0.3.0 (7.0) | mongodb 15.6.26 | edge | CMP-02 | B.6.2.6.1 | no instalado: el nodo edge es arm64 y las imágenes de Bitnami MongoDB solo existen para amd64 (--skip-chart edge-mongodb) |
| edge | edge-postgresql | 0.3.0 (16) | postgresql 15.5.38 | edge | CMP-02 | B.6.2.6.1, B.6.2.6.3, B.6.2.8.1 | instalado |
| edge | edge-postgresql-sync | 0.3.0 (1.0.0) | propio | edge | CMP-02 | B.6.2.6.1, B.6.2.8.1 | instalado |
| edge | edge-mlflow-sync | 0.3.0 (1.0.0) | propio | edge | CMP-03 | B.6.1.3.2, B.6.2.6.4, B.6.2.8.1 | instalado |
| plataforma | platform-mlflow | 0.3.0 (2.22.1) | mlflow 0.18.0 | mlops | CMP-03 | B.6.1.3.2, B.6.1.3.4, B.6.2.6.4 | instalado |
| plataforma | platform-training-jobs | 0.3.0 (1.0.0) | propio | mlops | CMP-04, CMP-14 | B.6.2.6.4 | instalado |
| plataforma | platform-evidently | 0.3.0 (0.4) | propio | mlops | CMP-10, CMP-14 | B.6.2.6.2, B.6.2.8.1, B.8.0.5.1 | instalado |
| plataforma | platform-minio | 0.3.0 (5.0) | minio 5.4.0 | minio | CMP-02, CMP-05 | B.6.2.3.1, B.6.2.5.1 | instalado |
| plataforma | platform-postgresql | 0.3.0 (15.0) | postgresql 15.5.38 | platform | CMP-02 | B.6.1.3.4 | instalado |
| plataforma | platform-timescaledb | 0.3.0 (2.17.2-pg16) | propio | platform | CMP-02, CMP-11 | B.6.2.6.1, B.6.2.6.3 | instalado |
| plataforma | platform-grafana | 0.3.0 (11.6.1) | grafana 8.15.0 | monitoring | CMP-06, CMP-10, CMP-11 | B.6.1.3.1, B.6.1.3.3, B.6.2.6.2 | instalado |
| plataforma | platform-loki | 0.3.0 (6.0) | loki 6.55.0 | monitoring | CMP-09 | B.6.2.8.1 | instalado |
| plataforma | platform-prometheus | 0.3.0 (61.0) | kube-prometheus-stack 61.9.0 | monitoring | CMP-08, CMP-10, CMP-11 | B.6.1.2.2, B.6.2.6.2, B.8.0.5.1 | instalado |
| plataforma | platform-rancher | 0.3.0 (2.11.3) | rancher 2.11.3 | cattle-system | - | B.6.2.5.1 | no instalado: el clúster ya lo gestiona un Rancher externo (install.sh nunca instala un segundo Rancher) |
| plataforma | platform-argocd | 0.3.0 (2.12) | argo-cd 7.9.1 | argocd | CMP-03 | B.6.2.5.1, B.6.2.6.4, B.6.2.8.1 | no instalado: el namespace argocd ya tenía otro Argo CD (--skip-chart platform-argocd) |
| plataforma | platform-openbao | 0.3.0 (2.0) | openbao 0.16.4 | openbao | CMP-07, CMP-15 | B.6.1.3.3, B.6.1.4.1, B.8.0.2.1 | instalado |
| plataforma | platform-cert-manager | 0.3.0 (v1.17.4) | cert-manager v1.17.4 | cert-manager | CMP-15 | B.6.1.4.1, B.6.2.3.1 | instalado |
| empresa | enterprise-keycloak | 0.3.0 (25.0.6) | keycloak 22.2.6 | security | CMP-07 | B.6.1.3.1, B.8.0.2.1 | instalado |
| empresa | enterprise-grafana-dashboards | 0.3.0 (1.0.0) | propio | monitoring | CMP-06, CMP-11 | B.6.1.3.3, B.6.2.6.2 | instalado |
| empresa | enterprise-minio-overlay | 0.3.0 (1.0.0) | propio | minio | CMP-05 | B.6.2.3.1, B.6.2.6.5 | instalado |
| empresa | enterprise-zammad | 0.3.0 (6.2.0-1) | zammad 10.3.4 | helpdesk | CMP-13 | B.6.2.6.6, B.8.0.4.1, B.8.0.5.1 | instalado |

Fuente: `CHART_META` de `infrastructure/publish.py`, `Chart.yaml` y `Chart.lock` de cada chart.


## 3. Correspondencia componente, chart y cláusulas (Tabla 30)

| Componente | Capa y nivel (arquitectura) | Criticidad | Chart(s) | Cláusulas (de sus charts) | Recursos en el laboratorio | Cobertura y observaciones |
|---|---|---|---|---|---|---|
| CMP-01 Input Data Monitoring | Entorno; dispositivo (en la práctica, pasarela edge) | Recomendado | edge-kafka (edge), edge-mosquitto (edge), edge-rabbitmq (edge), edge-node-red (edge), edge-opc-ua-gateway (edge) | B.6.1.3.1, B.6.2.6.4, B.6.2.8.1 | 17 | cubierto. Validación declarativa de la entrada en Node-RED (rangos, antigüedad, muestras rechazadas); transporte MQTT, Kafka y RabbitMQ; pasarela OPC UA |
| CMP-02 Data Stock | Datos; edge y plataforma | Recomendado | edge-mongodb (edge), edge-postgresql (edge), edge-postgresql-sync (edge), platform-minio (plataforma), platform-postgresql (plataforma), platform-timescaledb (plataforma) | B.6.1.3.4, B.6.2.3.1, B.6.2.5.1, B.6.2.6.1, B.6.2.6.3, B.6.2.8.1 | 21 | cubierto. Edge: PostgreSQL (y MongoDB, no desplegado en el laboratorio); plataforma: TimescaleDB, PostgreSQL de servicios y MinIO; consolidación edge a plataforma |
| CMP-03 Version Control | Integración; edge y plataforma | Obligatorio | edge-mlflow-sync (edge), platform-mlflow (plataforma), platform-argocd (plataforma) | B.6.1.3.2, B.6.1.3.4, B.6.2.5.1, B.6.2.6.4, B.6.2.8.1 | 6 | cubierto. Plataforma: registro de modelos MLflow (y Argo CD para GitOps, no desplegado en el laboratorio); edge: edge-mlflow-sync |
| CMP-04 Model | Modelo de IA; edge y plataforma | Obligatorio | edge-fastapi-model (edge), platform-training-jobs (plataforma) | B.6.2.6.2, B.6.2.6.4 | 5 | cubierto. Edge: servidor FastAPI con la versión propagada; plataforma: entrenamiento (sin servicio de inferencia propio en plataforma) |
| CMP-05 Document Store | Datos; empresa | Obligatorio | platform-minio (plataforma), enterprise-minio-overlay (empresa) | B.6.2.3.1, B.6.2.5.1, B.6.2.6.5 | 5 | cubierto. Bucket con object lock (GOVERNANCE, 365 días) y versionado para documentación y fichas de modelo |
| CMP-06 Information Centre | Entorno; empresa | Recomendado | platform-grafana (plataforma), enterprise-grafana-dashboards (empresa) | B.6.1.3.1, B.6.1.3.3, B.6.2.6.2 | 3 | cubierto. Grafana con fuentes de datos y 6 cuadros de mando ZDM |
| CMP-07 User Access & Oversight | Entorno; empresa (Control de Acceso en plataforma) | Recomendado | platform-openbao (plataforma), enterprise-keycloak (empresa) | B.6.1.3.1, B.6.1.3.3, B.6.1.4.1, B.8.0.2.1 | 10 | cubierto. Keycloak (realm ai-system); OpenBao para secretos |
| CMP-08 Infrastructure Technical Monitoring | Entorno; empresa | Recomendado | edge-prometheus-agent (edge), platform-prometheus (plataforma) | B.6.1.2.2, B.6.2.6.1, B.6.2.6.2, B.8.0.5.1 | 20 | cubierto. Prometheus y Alertmanager en plataforma; agente Prometheus en edge (remote-write) |
| CMP-09 Logger | Entorno en edge y plataforma; Datos en empresa | Recomendado | edge-fluent-bit (edge), platform-loki (plataforma) | B.6.2.8.1 | 9 | cubierto. Fluent Bit en todos los nodos hacia Loki, con almacenamiento en MinIO; configurado también para el log de auditoría del API (su llegada a Loki no se comprobó) |
| CMP-10 Model Technical Performance Monitoring | Datos en plataforma; subcomponente en edge | Obligatorio | edge-fastapi-model (edge), edge-prometheus-agent (edge), platform-evidently (plataforma), platform-grafana (plataforma), platform-prometheus (plataforma) | B.6.1.2.2, B.6.1.3.1, B.6.1.3.3, B.6.2.6.1, B.6.2.6.2, B.6.2.6.4, B.6.2.8.1, B.8.0.5.1 | 32 | cubierto. Métricas del modelo en edge (agente) y plataforma; deriva con Evidently |
| CMP-11 Goal-Oriented Monitoring | Datos en plataforma; Entorno en empresa | Recomendado | platform-timescaledb (plataforma), platform-grafana (plataforma), platform-prometheus (plataforma), enterprise-grafana-dashboards (empresa) | B.6.1.2.2, B.6.1.3.1, B.6.1.3.3, B.6.2.6.1, B.6.2.6.2, B.6.2.6.3, B.8.0.5.1 | 23 | cubierto. TimescaleDB (KPI, lotes de consolidación) y cuadros de mando de objetivos |
| CMP-12 Feedback Interface | Entorno; empresa | Recomendado | - | - | 0 | no cubierto. Sin chart: hueco no cubierto (la tabla operator_feedback existe en el almacén edge, pero no hay interfaz) |
| CMP-13 AI Helpdesk | Entorno; empresa | Obligatorio | enterprise-zammad (empresa) | B.6.2.6.6, B.8.0.4.1, B.8.0.5.1 | 14 | cubierto. Zammad |
| CMP-14 Retraining Recommendation | Modelo de IA; plataforma | Recomendado | platform-training-jobs (plataforma), platform-evidently (plataforma) | B.6.2.6.2, B.6.2.6.4, B.6.2.8.1, B.8.0.5.1 | 8 | cubierto. CronJob de deriva (Evidently) que registra la recomendación y lanza el reentrenamiento |
| CMP-15 Security Monitoring | Entorno; edge y plataforma | Recomendado | edge-falco (edge), platform-openbao (plataforma), platform-cert-manager (plataforma) | B.6.1.3.3, B.6.1.4.1, B.6.2.3.1, B.6.2.6.7, B.6.2.8.1, B.8.0.2.1 | 20 | cubierto. Falco en edge y plataforma (no en el dispositivo edge del laboratorio); cert-manager y OpenBao |

"Recursos en el laboratorio": pods, servicios, deployments y statefulsets con la etiqueta del componente (`kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/<CMP>`), en `trace/traceability.tsv`.


**Subcomponentes y flujos**

| Subcomponente o flujo | Chart(s) | Cobertura | Evidencia |
|---|---|---|---|
| Flujo de consolidación de datos (Data Stock edge a plataforma) | edge-postgresql-sync | cubierto | E04 y E11 |
| Flujo de propagación de versiones (Version Control plataforma a edge) | edge-mlflow-sync | cubierto | E07 y E14 |
| Industrial Protocol Gateway | edge-opc-ua-gateway (Telegraf, OPC UA a MQTT) | cubierto | E02 |
| Model Training Pipeline | platform-training-jobs | cubierto | E05 y E13 |
| Access Control (plataforma) | enterprise-keycloak, platform-openbao, NetworkPolicies de infrastructure/ | cubierto | S11, S13b, N01 a N13 |
| Business Dashboard | enterprise-grafana-dashboards | cubierto | S08 |
| RAW Data | platform-minio (bucket datasets), tema sensor-raw de edge-kafka | parcial: almacenamiento disponible, sin flujo que lo alimente | S02, S03 |
| Dataset Catalogue | sin chart; procedencia de datos en las etiquetas de cada versión de MLflow | parcial | E06 |
| Feature Engineering Pipeline | sin chart propio; agregación por intervalos en el job de entrenamiento | parcial | E05 |
| API Gateway | sin chart | no cubierto | - |
| ERP/MES Integration | sin chart | no cubierto | - |

## 4. Resultados del despliegue por nivel (Tabla 31)

Comando (ejecutado por `run-lab-validation.sh`, fase 3): `infrastructure/install.sh --values-dir docs/lab-validation/lab-values --site-id lab-edge-01 --skip platform-argocd --skip edge-mongodb --separate-tiers`. Duración de `install.sh`: 2336 s (unos 39 min); de ellos, 1550 s en las 28 ejecuciones de `helm upgrade --install --wait` (la mayor parte, descarga de imágenes) y el resto en la fase base, el registro de repositorios y la construcción de dependencias de cada chart. Fuente: `raw/lab-20260924T081803/install.jsonl` e `install.log`.

"Pods listos" es la muestra tomada al terminar `helm upgrade --install --wait` de cada chart; el estado final de todos los pods está en `state/final-pods.txt`.


**Nivel edge** (12 instalados; 1 omitido). Sus pods corren en `edgenode01`, salvo los DaemonSets (Fluent Bit en los tres nodos; Falco en los dos amd64) y una réplica de falcosidekick.

| Chart | Namespace | Resultado | Tiempo (s) | Pods listos | Observaciones |
|---|---|---|---|---|---|
| edge-postgresql | edge | correcto | 36 | 1/1 |  |
| edge-mosquitto | edge | correcto | 19 | 1/1 |  |
| edge-rabbitmq | edge | correcto | 50 | 1/1 |  |
| edge-kafka | edge | correcto | 88 | 1/1 | KRaft de un nodo en el dispositivo edge (arm64) |
| edge-opc-ua-gateway | edge | correcto | 19 | 1/1 |  |
| edge-node-red | edge | correcto | 51 | 1/1 |  |
| edge-fastapi-model | edge | correcto | 52 | 1/1 |  |
| edge-mlflow-sync | edge | correcto | 1 | 0/0 | Solo CronJob |
| edge-postgresql-sync | edge | correcto | 1 | 0/0 | Solo CronJob |
| edge-prometheus-agent | edge | correcto | 62 | 1/1 |  |
| edge-fluent-bit | logging | correcto | 11 | 2/3 | DaemonSet en los 3 nodos (2/3 en el instante de la medida, 3/3 al final) |
| edge-falco | falco | parcial | 74 | 3/4 | Solo en los nodos amd64 (el kernel del dispositivo edge no tiene BTF); 3/4 en el instante de la medida, todo en Running al final |
| edge-mongodb | edge | omitido | - | - | no instalado: el nodo edge es arm64 y las imágenes de Bitnami MongoDB solo existen para amd64 (--skip-chart edge-mongodb) |

**Nivel plataforma** (12 instalados; 2 omitidos). Sus pods corren en `worker1-kb2`, salvo el DaemonSet de node-exporter (tres nodos).

| Chart | Namespace | Resultado | Tiempo (s) | Pods listos | Observaciones |
|---|---|---|---|---|---|
| platform-cert-manager | cert-manager | correcto | 111 | 3/3 | Dos pasadas por diseño: la segunda crea los emisores de la CA de plataforma cuando ya existen los CRD |
| platform-cert-manager (2.ª pasada) | cert-manager | correcto | 11 | 3/3 | Segunda pasada (emisores) |
| platform-openbao | openbao | correcto | 2 | 0/1 | 0/1 listo al terminar Helm porque OpenBao arranca sellado; S13b lo inicializa y desella (1/1) |
| platform-postgresql | platform | correcto | 35 | 1/1 |  |
| platform-minio | minio | correcto | 19 | 1/1 |  |
| platform-timescaledb | platform | correcto | 65 | 1/1 |  |
| platform-prometheus | monitoring | parcial | 42 | 5/7 | 5/7 en el instante de la medida; al final, todo en Running. El node-exporter del dispositivo edge responde 503 (1 de 30 targets caído) |
| platform-loki | monitoring | correcto | 56 | 1/1 |  |
| platform-grafana | monitoring | correcto | 34 | 1/1 |  |
| platform-mlflow | mlops | correcto | 280 | 1/1 | El más lento de plataforma (descarga de la imagen de MLflow) |
| platform-training-jobs | mlops | correcto | 1 | 0/0 | Solo CronJob (sin pods permanentes) |
| platform-evidently | mlops | correcto | 52 | 1/1 |  |
| platform-rancher | cattle-system | omitido | - | - | no instalado: el clúster ya lo gestiona un Rancher externo (install.sh nunca instala un segundo Rancher) |
| platform-argocd | argocd | omitido | - | - | no instalado: el namespace argocd ya tenía otro Argo CD (--skip-chart platform-argocd) |

**Nivel empresa** (4 instalados; 0 omitidos). Sus pods corren en `worker1-kb2`.

| Chart | Namespace | Resultado | Tiempo (s) | Pods listos | Observaciones |
|---|---|---|---|---|---|
| enterprise-keycloak | security | correcto | 120 | 1/1 | Imagen 25.0.6 con proxyHeaders xforwarded |
| enterprise-minio-overlay | minio | correcto | 1 | 0/1 | 0/1: el pod es el Job de aprovisionamiento, que termina en Completed |
| enterprise-grafana-dashboards | monitoring | correcto | 1 | 0/0 | Solo ConfigMaps |
| enterprise-zammad | helpdesk | correcto | 256 | 4/4 | El más lento del catálogo; 4/4 pods listos |

## 5. Pruebas de humo y de extremo a extremo


### 5.1 Pruebas de humo

Ejecución de referencia `raw/lab-20260924T092125` (fase 4 repetida tras corregir S04). Resultado: 18 PASS, 0 FAIL, 3 SKIP.

| ID | Prueba | Resultado | Comando | Salida resumida |
|---|---|---|---|---|
| S01 | MLflow tracking API | PASS | POST /api/2.0/mlflow/experiments/search (port-forward svc/platform-mlflow) | experiments: ['zdm-drift-monitoring', 'zdm-anomaly-detection', 'Default'] |
| S02 | MinIO buckets, versioning and document store retention | PASS | mc ls; mc retention info --default s/iso42001-docs; mc version info s/model-cards (pod in minio) | [2026-09-24 08:29:03 UTC]     0B mlflow-artifacts/ [2026-09-24 08:52:46 UTC]     0B model-cards/ Object locking 'GOVERNANCE' is configured for 365DAYS. s/model-cards versioning is enabled |
| S03 | Kafka produce and consume | PASS | kafka-console-producer.sh / kafka-console-consumer.sh on topic alerts | predictions sensor-raw sensor-validated consumed lab-smoke-1790241698 |
| S04 | Mosquitto authenticated publish/subscribe, anonymous refused | PASS | mosquitto_sub (nodered) + mosquitto_pub (gateway); anonymous mosquitto_pub | received: hello (after 1 publish attempts) anonymous refused |
| S05 | RabbitMQ running and listeners | PASS | rabbitmq-diagnostics check_running; listeners | Interface: [::], port: 15672, protocol: http, purpose: HTTP API Interface: [::], port: 15692, protocol: http/prometheus, purpose: Prometheus exporter API over HTTP Interface: [::], port: 25672, protocol: clustering, purpose: inter-node and CLI tool communicati |
| S06 | Node-RED ingestion metrics and protected editor | PASS | GET /metrics; GET /admin/flows (expect 401) | ingest_values_written_total 9780 ingest_db_errors_total 5 ingest_last_sample_timestamp_seconds 1790241750 editor /admin/flows without credentials: HTTP 401 |
| S07 | Prometheus scrape targets | PASS | GET /api/v1/targets (port-forward svc/platform-prometheus-prometheus) | up         2  platform-prometheus-prometheus up         1  platform-timescaledb up 29 of 30 targets down: node-exporter http://<ip-edgenode01>:9101/metrics server returned HTTP status 503 Service Unavailable |
| S08 | Grafana health, data sources and dashboards | PASS | GET /api/health; /api/datasources/uid/<uid>/health; /api/search?query=ZDM | data source timescaledb: {"message":"Database Connection OK","status":"OK"} data source edgepg: {"message":"Database Connection OK","status":"OK"} 6 ZDM dashboards: ['ZDM AI System', 'ZDM: Data Consolidation, KPIs and Drift (CMP-02, CMP-11, CMP-14)', 'ZDM: Edg |
| S09 | Loki write and query | PASS | POST /loki/api/v1/push; GET /loki/api/v1/query_range | pushed read back: lab smoke line 1790241756000000000 |
| S10 | Falco runtime event (shell in the model server) | SKIP | kubectl exec deploy/edge-fastapi-model -- sh -c id; kubectl logs falco | model server node: edgenode01 not run: no Falco pod on edgenode01 (the Falco driver cannot run there, see lab-values/edge-falco.yaml) |
| S11 | Keycloak realm ai-system | PASS | GET /realms/ai-system/.well-known/openid-configuration | issuer: http://127.0.0.1:18080/realms/ai-system |
| S12 | Zammad web and API | PASS | GET /; GET /api/v1/getting_started | web: HTTP 200 {"setup_done":false,"import_mode":false,"import_backend":"","system_online_service":false} |
| S13 | OpenBao status over TLS (platform CA) | PASS | kubectl exec platform-openbao-0 -- bao status | Cluster Name    vault-cluster-946f1225 Cluster ID      523286c1-1a1b-4be3-a030-a6a8bbe114e8 HA Enabled      false (bao status exit 0: 0 unsealed, 2 sealed, 1 error) |
| S13b | OpenBao init, unseal, KV write/read, audit device | PASS | bao operator init/unseal; bao secrets enable kv; bao audit enable file; bao kv put/get | Sealed          false Path     Type    Description ----     ----    ----------- file/    file    n/a |
| S14 | cert-manager test certificate from the platform CA | PASS | kubectl apply Certificate (issuer platform-ca); kubectl wait --for=condition=Ready | lab-smoke-cert   True    lab-smoke-cert   2s subject= issuer=CN = ZDM MLOps platform CA notAfter=Dec 23 09:22:48 2026 GMT |
| S15 | Argo CD sync of a catalog chart from git (lab-validation) | SKIP | kubectl apply Application lab-smoke-dashboards; wait Synced/Healthy | not run: release platform-argocd is not installed in namespace argocd (skipped in this laboratory, see the run options) |
| S16 | TimescaleDB hypertables and roles | PASS | psql: timescaledb_information.hypertables; pg_roles | sensor_readings grafana ml sync |
| S17 | Edge PostgreSQL schema | PASS | psql: information_schema.tables | operator_feedback predictions sensor_features system_events |
| S18 | MongoDB edge buffer collections | SKIP | mongosh: getCollectionNames() | not run: release edge-mongodb is not installed in namespace edge (skipped in this laboratory, see the run options) |
| S19 | Platform PostgreSQL service databases | PASS | psql: pg_database | grafana keycloak mlflow zammad |
| S20 | Evidently UI API | PASS | GET /api/version | {"application":"Evidently UI","version":"0.4.33","commit":"-"} |

En la primera ejecución (`raw/lab-20260924T081803`) S04 falló: el test publicaba una sola vez a los 2 s y el suscriptor, con el broker en otro nodo, aún no estaba suscrito. El flujo real sí funcionaba con autenticación (E03). Se corrigió el test para publicar hasta recibir (commit 0fc2b13) y en la repetición pasa.


### 5.2 Prueba de extremo a extremo

Ejecución `raw/lab-20260924T081803`, fase 5: 16 de 16 tramos correctos.

| Tramo | Prueba | Resultado | Tiempo (s) | Comando | Evidencia resumida |
|---|---|---|---|---|---|
| E01 | OPC UA simulator (OPC PLC) in the edge namespace | PASS | 1 | kubectl apply -f docs/lab-validation/manifests/opc-plc-simulator.yaml | Simulador OPC PLC (mcr.microsoft.com/iotedge/opc-plc:2.15.5) desplegado en el namespace edge |
| E02 | OPC UA gateway reads the simulator | PASS | 30 | wget localhost:9273/metrics in edge-opc-ua-gateway | Telegraf lee el simulador por OPC UA: 3548 métricas recogidas, 0 errores |
| E03 | Ingestion: MQTT -> Node-RED validation -> edge data stock | PASS | 31 | psql: count(*) FROM sensor_features, 30 s apart | Node-RED valida y escribe en el almacén edge: sensor_features pasa de 3181 a 3299 filas en 30 s (4 variables de cnc-01) |
| E04 | Data consolidation edge -> platform (batch log) | PASS | 8 | kubectl create job --from=cronjob/edge-postgresql-sync; psql consolidation_batches | edge-postgresql-sync consolida en TimescaleDB: lote 15, filas 3181 a 3320, 139 leídas y 139 escritas, estado ok |
| E05 | Training job registers and promotes a model version | PASS | 16 | kubectl create job --from=cronjob/platform-training-jobs e2e-train-1 | Entrenamiento con 831 muestras de TimescaleDB; versión 1 registrada y promovida (tasa de anomalías 0,0205, criterio de liberación cumplido) |
| E06 | MLflow registry: version, alias and provenance tags | PASS | 1 | GET /api/2.0/mlflow/registered-models/get; model-versions/get | Registro MLflow: alias champion a la versión 1, con etiquetas de procedencia (origen, ventana, intervalo, filas, lote de consolidación) |
| E07 | Version propagation platform -> edge (edge-mlflow-sync) | PASS | 26 | kubectl create job --from=cronjob/edge-mlflow-sync e2e-vsync-1; psql model_versions | edge-mlflow-sync detecta la versión 1, la descarga (sha256 8ce9e011...) y la activa; model_versions registra downloaded, download_failed (ejecución concurrente del CronJob) y active |
| E08 | Inference with the propagated version | PASS | 2 | GET /version; POST /predict (port-forward svc/edge-fastapi-model) | Inferencia con la versión 1: una muestra normal (0,5732) y una anómala (0,7076), registradas en predictions |
| E09 | Edge metrics in the platform Prometheus (remote-write) | PASS | 46 | PromQL on platform-prometheus: model_predictions_total, model_info, ingest_messages_valid_total | Prometheus de plataforma recibe por remote-write model_predictions_total, model_info (versión 1), ingest_messages_valid_total (3688) y métricas de la pasarela: 4 de 4 consultas con datos |
| E10 | Induced drift: shifted samples of machine cnc-02 through MQTT | PASS | 400 | mosquitto_pub 300 s of shifted samples (pod in edge) | 300 s de muestras desplazadas de la máquina cnc-02 publicadas por MQTT con el usuario de la pasarela |
| E11 | Consolidation of the drifted data | PASS | 10 | kubectl create job --from=cronjob/edge-postgresql-sync e2e-sync-2 | Segunda consolidación: lotes 23 y 25 (854 y 366 filas); cnc-01 con 5320 filas y cnc-02 con 1200 en plataforma |
| E12 | Evidently drift check and retraining recommendation | PASS | 15 | kubectl create job --from=cronjob/platform-evidently-drift e2e-drift-1; psql retraining_recommendations | Evidently: deriva en las 4 variables (proporción 1,0 frente al umbral 0,5); recomendación 1 registrada y Job de reentrenamiento creado |
| E13 | Retraining job started by the recommendation | PASS | 31 | kubectl get jobs (platform-training-jobs-drift-*); kubectl wait | Reentrenamiento lanzado por la recomendación con 1631 muestras; versión 2 registrada y promovida |
| E14 | New version propagated to the edge and served | PASS | 28 | kubectl create job --from=cronjob/edge-mlflow-sync e2e-vsync-2; GET /version; POST /predict | edge-mlflow-sync activa la versión 2 (antes 1); la inferencia responde con model_version 2 |
| E15 | MLOps events collected by Fluent Bit in Loki | PASS | 22 | LogQL count_over_time({namespace=~"edge\|mlops"} \|= <event> [3h]) | Loki (vía Fluent Bit) contiene los eventos model_registered, version_activated, recommendation, drift_computed, prediction y los del job de consolidación (6 de 7 tipos; sample_rejected no se produjo porque no se enviaron muestras inválidas) |
| E16 | Drift reports stored in the Evidently UI | PASS | 1 | GET /api/projects (port-forward svc/platform-evidently) | La interfaz de Evidently contiene el proyecto zdm-anomaly-detector con los informes de deriva |

### 5.3 NetworkPolicy

Ejecución de referencia `raw/lab-20260924T095847`. Cada prueba lanza un pod cliente con `nc -z -w 5` en el namespace de origen, en un nodo que aplica políticas, tras esperar 15 s a que el controlador lo incluya en sus reglas.


Canario (un pod con `httpd` en cada nodo; accesible desde otro namespace sin política y bloqueado con una política de denegación total):

```
edgenode01: pod 10.42.2.151:8080 from another namespace: without policy CONNECTED, with a deny-all ingress policy CONNECTED
kb2: pod 10.42.0.103:8080 from another namespace: without policy CONNECTED, with a deny-all ingress policy NOT-CONNECTED
worker1-kb2: pod 10.42.1.212:8080 from another namespace: without policy CONNECTED, with a deny-all ingress policy NOT-CONNECTED
```

| ID | Prueba | Resultado | Nodo cliente | Nodo destino | Salida |
|---|---|---|---|---|---|
| N-CANARY | NetworkPolicies are enforced on every node (pod behind a deny-all policy) | FAIL | - | - | ver el bloque del canario |
| N00 | namespace outside the catalog -> Internet (control, no policy) (expected: allow) | PASS | worker1-kb2 | n/a | CONNECTED |
| N01 | edge -> platform TimescaleDB (consolidation conduit) (expected: allow) | PASS | worker1-kb2 | worker1-kb2 | CONNECTED |
| N02 | edge -> MLflow (version sync conduit) (expected: allow) | PASS | worker1-kb2 | worker1-kb2 | CONNECTED |
| N03 | edge -> edge PostgreSQL (same namespace) (expected: allow) | PASS | worker1-kb2 | edgenode01 | destination on edgenode01, which does not enforce NetworkPolicies (N-CANARY); CONNECTED |
| N04 | edge -> MinIO (no conduit) (expected: deny) | PASS | worker1-kb2 | worker1-kb2 | BLOCKED |
| N05 | edge -> Zammad (no conduit) (expected: deny) | PASS | worker1-kb2 | worker1-kb2 | BLOCKED |
| N06 | namespace outside the catalog -> edge PostgreSQL (default deny ingress) (expected: deny) | FAIL | worker1-kb2 | edgenode01 | destination on edgenode01, which does not enforce NetworkPolicies (N-CANARY); CONNECTED |
| N07 | mlops -> MinIO (artefact conduit) (expected: allow) | PASS | worker1-kb2 | worker1-kb2 | CONNECTED |
| N08 | mlops -> Internet (default deny egress) (expected: deny) | PASS | worker1-kb2 | n/a | BLOCKED |
| N09 | security -> platform PostgreSQL (Keycloak database) (expected: allow) | PASS | worker1-kb2 | worker1-kb2 | CONNECTED |
| N10 | helpdesk -> MLflow (no conduit) (expected: deny) | PASS | worker1-kb2 | worker1-kb2 | BLOCKED |
| N11 | argocd -> Internet 443 (Git and Helm repositories) (expected: allow) | SKIP | - | - | not run: platform-argocd is not installed; the argocd namespace belongs to another deployment |
| N12 | logging -> Loki (log conduit) (expected: allow) | PASS | worker1-kb2 | worker1-kb2 | CONNECTED |
| N13 | mlops -> edge PostgreSQL (no conduit; egress rule of mlops) (expected: deny) | PASS | worker1-kb2 | edgenode01 | destination on edgenode01, which does not enforce NetworkPolicies (N-CANARY); BLOCKED |

**Lectura de los resultados.**

- `kb2` y `worker1-kb2` aplican NetworkPolicy; `edgenode01` no. Su controlador (kube-router, integrado en K3s) falla en bucle con `ipset restore: set type not supported`, porque el kernel `5.15.148-tegra` de JetPack no incluye el módulo `ip_set_hash_ip` (`raw/diag-ubuntu-20260924T113108.txt`).
- Las denegaciones hacia servicios de plataforma (N04, N05 y N10) y todos los conductos permitidos funcionan.
- N08 comprueba la denegación de salida hacia Internet desde `mlops`.
- N13 comprueba una regla de salida por sí sola: el destino está en el dispositivo edge, que no filtra, y aun así la conexión se bloquea en origen.
- N06 falla porque su protección depende de la regla de entrada del pod de destino, que corre en el dispositivo edge.
- N11 no se ejecutó porque el namespace `argocd` pertenece a otro despliegue.

**Historia de las ejecuciones de red.** La segmentación solo pudo medirse tras varios ajustes, todos con evidencia:

1. **Controlador desactivado.** K3s tenía `disable-network-policy: true`. El script lo quitó y reinició `k3s` en el primer intento (PREP-04 correcto en `lab-20260924T075022`; en `lab-20260924T081803` ya no estaba, según `state/enable-network-policy.txt`), pero los agentes de `worker1-kb2` y `edgenode01` necesitaban también reiniciarse (canarios de `lab-20260924T081803` y `lab-20260924T092125`).
2. **Clientes en un nodo que aplica políticas.** En `lab-20260924T093809` los clientes ya iban a un nodo que aplica políticas, pero N08 dio CONNECTED: el controlador tarda unos segundos en incluir un pod recién creado en sus reglas, y el cliente conectaba antes.
3. **Espera de sincronización.** Con la espera de 15 s (commit a3b8999), N08 queda bloqueada en la ejecución de referencia.

Las ejecuciones anteriores se conservan como historial.


## 6. Consultas por etiqueta iso42001

Ejecución `raw/lab-20260924T081803`, fase 6 (`tools/traceability.py`). Esquema de etiquetas: `iso42001=true` en todo recurso del catálogo y `mlops-iso42001.cigip-upv.es/<cláusula>=true` y `mlops-iso42001.cigip-upv.es/<CMP>=true` según `CHART_META`.

| Clave | Descripción | Recursos (pods, svc, deploy, sts) | Comando |
|---|---|---|---|
| B.6.1.2.2 | Resources: Monitoring Performance | 20 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.6.1.2.2 --no-headers |
| B.6.1.3.1 | Resources: Access Control | 14 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.6.1.3.1 --no-headers |
| B.6.1.3.2 | Resources: Version Control | 6 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.6.1.3.2 --no-headers |
| B.6.1.3.3 | Resources: Human Oversight / Feedback | 8 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.6.1.3.3 --no-headers |
| B.6.1.3.4 | Resources: Inventory / Registry | 8 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.6.1.3.4 --no-headers |
| B.6.1.4.1 | Resources: Security of AI Assets | 14 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.6.1.4.1 --no-headers |
| B.6.2.3.1 | Planning: System Documentation | 14 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.6.2.3.1 --no-headers |
| B.6.2.5.1 | Planning: Deployment Plan | 4 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.6.2.5.1 --no-headers |
| B.6.2.6.1 | Operation: Infrastructure Monitoring | 15 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.6.2.6.1 --no-headers |
| B.6.2.6.2 | Operation: Model Performance | 29 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.6.2.6.2 --no-headers |
| B.6.2.6.3 | Operation: KPI Assessment (OEE) | 8 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.6.2.6.3 --no-headers |
| B.6.2.6.4 | Operation: Retraining / Lifecycle | 28 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.6.2.6.4 --no-headers |
| B.6.2.6.5 | Operation: Update & Repair Plan | 1 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.6.2.6.5 --no-headers |
| B.6.2.6.6 | Operation: Incident Communication | 14 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.6.2.6.6 --no-headers |
| B.6.2.6.7 | Operation: Security Monitoring | 6 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.6.2.6.7 --no-headers |
| B.6.2.8.1 | Operation: Logging / Audit Trail | 41 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.6.2.8.1 --no-headers |
| B.8.0.2.1 | Continual Improvement: Roles | 10 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.8.0.2.1 --no-headers |
| B.8.0.4.1 | Continual Improvement: Helpdesk | 14 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.8.0.4.1 --no-headers |
| B.8.0.5.1 | Continual Improvement: Alerts | 37 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/B.8.0.5.1 --no-headers |
| CMP-01 | Input Data Monitoring | 17 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/CMP-01 --no-headers |
| CMP-02 | Data Stock | 21 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/CMP-02 --no-headers |
| CMP-03 | Version Control | 6 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/CMP-03 --no-headers |
| CMP-04 | Model | 5 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/CMP-04 --no-headers |
| CMP-05 | Document Store | 5 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/CMP-05 --no-headers |
| CMP-06 | Information Centre | 3 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/CMP-06 --no-headers |
| CMP-07 | User Access & Oversight | 10 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/CMP-07 --no-headers |
| CMP-08 | Infrastructure Technical Monitoring | 20 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/CMP-08 --no-headers |
| CMP-09 | Logger | 9 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/CMP-09 --no-headers |
| CMP-10 | Model Technical Performance Monitoring | 32 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/CMP-10 --no-headers |
| CMP-11 | Goal-Oriented Monitoring | 23 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/CMP-11 --no-headers |
| CMP-12 | Feedback Interface | 0 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/CMP-12 --no-headers |
| CMP-13 | AI Helpdesk | 14 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/CMP-13 --no-headers |
| CMP-14 | Retraining Recommendation | 8 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/CMP-14 --no-headers |
| CMP-15 | Security Monitoring | 20 | kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/CMP-15 --no-headers |
| iso42001=true | all catalog resources | 127 | kubectl get pods,svc,deploy,sts -A -l iso42001=true --no-headers |

**Cobertura de la etiqueta por namespace** (todos los tipos de objeto; se cuentan aparte los de otros releases de Helm en namespaces compartidos):

| Namespace | Objetos | Con iso42001=true | De otros releases |
|---|---|---|---|
| argocd | 49 | 0 | 0 |
| cert-manager | 18 | 12 | 0 |
| edge | 92 | 75 | 0 |
| falco | 22 | 19 | 0 |
| helpdesk | 33 | 28 | 0 |
| logging | 16 | 13 | 0 |
| minio | 18 | 14 | 0 |
| mlops | 38 | 32 | 0 |
| monitoring | 97 | 72 | 6 |
| openbao | 19 | 12 | 0 |
| platform | 22 | 17 | 0 |
| security | 16 | 13 | 0 |

En los namespaces del catálogo (sin `argocd`, que es de otro despliegue) llevan la etiqueta 307 de 391 objetos (79 %). La verificación estática (`verify_charts.py --post-render`, `local-evidence/verify-charts.txt`) etiqueta 387 de 394 recursos renderizados y 52 de 53 plantillas de pod; los 7 recursos restantes son hooks de Helm, que no pasan por el post-renderer. Casi todos los objetos sin etiqueta en el clúster no los renderiza ningún chart (análisis en el clúster local, `local-evidence/unlabelled-objects.txt`): registros de release de Helm, `kube-root-ca.crt` y la ServiceAccount `default` que crea Kubernetes, PVC generados desde `volumeClaimTemplates`, objetos que generan los operadores (Prometheus, Alertmanager, cert-manager) y el simulador de pruebas; la excepción es un hook de Helm.


## 7. Refinamientos

| Cambio | Hueco o problema | Efecto | Detectado en | Commits |
|---|---|---|---|---|
| Chart nuevo edge-postgresql-sync | Flujo de consolidación de datos (Data Stock edge a plataforma) sin soporte | CronJob con marca de agua y lotes idempotentes registrados en consolidation_batches; validado en E04 y E11 | Fase 1 (auditoría) | 41eb9d7 |
| Chart nuevo edge-mlflow-sync y servidor de modelo funcional | Flujo de propagación de versiones y CMP-03 en edge sin chart; edge-fastapi-model sin imagen utilizable | Sigue el alias champion de MLflow, descarga, verifica sha256, activa y recarga el servidor; validado en E07, E08 y E14 | Fase 1 | a37727f |
| Pipeline de entrenamiento y recomendación de reentrenamiento | CMP-14 sin implementación operativa | Entrenamiento con criterios de liberación y CronJob de deriva (Evidently) que recomienda y lanza el reentrenamiento; validado en E05, E12 y E13 | Fase 1 | cd6711d |
| Flujo declarativo de validación de entrada en Node-RED | CMP-01 solo tenía transporte, sin validación de datos de entrada | Rangos, antigüedad y muestras rechazadas con métricas; validado en E03 y S06 | Fase 1 | 74a4af5 |
| Pasarela OPC UA con Telegraf en lugar de Neuron | La edición libre de Neuron no tiene controlador OPC UA (subcomponente Industrial Protocol Gateway) | OPC UA a MQTT con autenticación; validado en E02 | Fase 1 | e34129b |
| TimescaleDB con plantillas propias | timescaledb-single está obsoleto; almacén de plataforma y KPI (CMP-02, CMP-11) | Hipertablas, roles y tablas de consolidación y recomendaciones; validado en S16 | Fase 1 | 057e418 |
| Almacén documental con object lock | El overlay de MinIO no aplicaba el bloqueo ni lo consumía nadie (CMP-05) | Job de aprovisionamiento con object lock GOVERNANCE 365 días y versionado; validado en S02 | Fase 1 | 2ca5579 |
| Cuadros de mando importables y reglas de alerta reales | Cuadros de mando en pseudo-JSON y reglas sobre métricas inexistentes (CMP-06, CMP-08, CMP-11) | 6 cuadros de mando ZDM y 8 reglas; validado en S07 y S08 | Fase 1 | 1601171 |
| Correcciones de charts de terceros (Kafka, MongoDB, PostgreSQL, MLflow, RabbitMQ, Keycloak, Zammad, Argo CD, cert-manager, OpenBao, Rancher, Falco, agente Prometheus) | Imágenes retiradas, secretos inexistentes, claves de values ignoradas, plantillas ausentes y reglas de Falco que no compilaban | Los 30 charts pasan lint, render y kubeconform (1.32); 27 charts desplegados sin fallos en el laboratorio | Fase 1 y pruebas locales | 5dab858, 19b88cd, 609c926, 07f33a0, a59efca, e93c232, f960157, ba644a6, af8fd35 |
| Imágenes oficiales desde el espejo público de ECR | Límite de descargas anónimas de Docker Hub (429) durante las pruebas | Menos dependencia de Docker Hub | Pruebas locales | 95a75d7 |
| Política de auditoría del API y enable-audit.sh | setup-ubuntu.sh activaba la auditoría sin política, sin registrar nada (B.6.2.8.1) | Log de auditoría activo en el laboratorio (7429 eventos al comprobarlo); Fluent Bit está configurado para enviarlo a Loki, sin comprobación en esta validación | Fase 1 | 26a92cd |
| NetworkPolicy por zonas en todos los namespaces | platform, minio, falco, logging y cattle-system sin políticas; egress de mlops solo DNS UDP | Denegación por defecto y conductos explícitos; validado en N01 a N13 en los nodos que aplican políticas | Fase 1 | 26a92cd |
| install.sh por fases con los charts propios | Instalaba charts de terceros, manifiestos inexistentes y dejaba fuera 10 charts | Fases base, seguridad, datos, edge y empresa con secretos generados, post-renderer de etiquetas y registro JSON; validado en el laboratorio (27 charts, 28 ejecuciones de Helm) | Fase 1 | 4f17e2d, 2712b1e |
| publish.py con helm dependency build y paquetes publicados por CI | index.yaml apuntaba a .tgz inexistentes (404) y los envolventes salían sin subcharts | 30 paquetes con dependencias; repositorio validado en local (30/30) | Fase 1 | c8cab72, 8d83879 |
| verify_charts.py e iso42001-postrender.py | Sin verificación automática ni etiquetas en recursos de subcharts sin gancho de etiquetas | 387 de 394 recursos renderizados etiquetados (los 7 restantes son hooks de Helm) | Fase 1 | c02a7b4 |
| Documentación alineada (README, catalog/README.md, index.html, CITATION.cff 1.0.1) | Deriva documental y etiquetas ISO distintas en tres sitios | Una sola fuente (CHART_META) para tablas y metadatos | Fase 1 | d7a3202, 3d90b41, 39eb2a5 |
| Fichero de contraseñas de Mosquitto propiedad del broker | El broker (uid 1883) no podía leer el fichero y el pod no arrancaba | Mosquitto arranca con autenticación; S04 y E03 | Pruebas locales (Kubernetes) | d7048db |
| Paso de preparación de Node-RED con el usuario de Node-RED | Las credenciales escritas por el init container no eran legibles | Node-RED arranca y se conecta al broker | Pruebas locales (Kubernetes) | 5473a3f |
| Métricas de Keycloak en el puerto de gestión 9000 | El ServiceMonitor apuntaba a 8080, donde /metrics da 404 | Target de Keycloak activo | Pruebas locales (Kubernetes) | 02838e8 |
| NetworkPolicies de los subcharts de Bitnami desactivadas | Kafka, MongoDB, las dos PostgreSQL y Keycloak creaban políticas que admitían tráfico desde cualquier namespace y anulaban la denegación por defecto | Un pod de fuera del catálogo ya no alcanza la PostgreSQL del edge (N06 en el clúster local) | Pruebas locales (Kubernetes) | 8b7937e |
| Regla del API server solo en el puerto 6443 | La regla abría 443 hacia 0.0.0.0/0 en todos los namespaces (salida HTTPS a Internet) | mlops ya no sale a Internet (N08 en el laboratorio) | Pruebas locales (análisis de N08) | 5202b6a |
| install.sh registra los repositorios de las dependencias | Con Helm sin repositorios, helm dependency build fallaba y la instalación se detenía en la fase base | Instalación completa en el laboratorio | Laboratorio (primer intento) | 0a4cc19 |
| install.sh --separate-tiers y namespaces ajenos intactos | El planificador podía colocar pods de plataforma en el dispositivo edge; un namespace argocd ajeno habría recibido nuestras políticas | Pods edge en edgenode01, plataforma y empresa en worker1-kb2, kb2 solo con DaemonSets | Diagnóstico del laboratorio | 693b349 |
| appVersion de Keycloak alineado con la imagen | Chart.yaml declaraba 24.0.0 y se despliega 25.0.6 | Metadatos coherentes | Redacción del informe | d5428ea |

No se aplicó ningún cambio "por completitud": CMP-12 (Feedback Interface) sigue sin chart porque su propuesta no se aprobó en la fase 1. También se añadieron herramientas de validación que no forman parte del catálogo: `run-lab-validation.sh`, `diagnose-cluster.sh` y `tools/`.


## 8. Respuestas a las preguntas del capítulo 7

**Número total de charts**

30 charts en la rama `lab-validation`: 13 de edge, 13 de plataforma y 4 de empresa. En `main` había 28 (11, 13 y 4); los dos nuevos son `edge-postgresql-sync` (consolidación de datos) y `edge-mlflow-sync` (propagación de versiones). En el laboratorio se desplegaron 27: no se instalaron `platform-rancher` (el clúster ya lo gestiona un Rancher externo), `platform-argocd` (había otro Argo CD en su namespace) ni `edge-mongodb` (sin imagen arm64 para el dispositivo edge).

*Evidencia:* `CHART_META` de `infrastructure/publish.py`; `raw/lab-20260924T081803/install.jsonl`.

**Qué charts materializan CMP-01, CMP-08 y CMP-12**

CMP-01 (Input Data Monitoring): `edge-node-red`, con el flujo declarativo de validación de la entrada, sobre el transporte de `edge-mosquitto`, `edge-kafka`, `edge-rabbitmq` y la pasarela `edge-opc-ua-gateway`. CMP-08 (Infrastructure Technical Monitoring): `platform-prometheus` (Prometheus, Alertmanager, node-exporter y kube-state-metrics) y `edge-prometheus-agent` (remote-write desde el edge). CMP-12 (Feedback Interface): ningún chart; es un hueco no cubierto, y la consulta de su etiqueta devuelve 0 recursos.

*Evidencia:* Sección 3; `trace/traceability.tsv` (CMP-01: 17, CMP-08: 20, CMP-12: 0 recursos); pruebas E03, S06, S07 y E09.

**Si la instalación es reproducible desde el repositorio Helm publicado**

Hoy no. El repositorio publicado en GitHub Pages se construyó desde `main` (commit cb20350, 3 de junio de 2026): su `index.yaml` lista 28 charts en la versión 0.2.0 y los 28 paquetes devuelven HTTP 404. La rama corrige la causa: `publish.py` construye las dependencias y empaqueta, y el flujo de Pages publica los paquetes al fusionar en `main`. Esa vía se validó en el clúster local, no en el laboratorio: un repositorio generado con `publish.py` y servido por HTTP devuelve los 30 charts, los 30 se descargan y renderizan con el post-renderer, y 29 se actualizan con `--dry-run=server` sobre las releases instaladas (Rancher no estaba instalado). La instalación del laboratorio usó los charts del repositorio git (`install.sh --source local`); falta repetirla con `--source repo` una vez fusionada la rama.

*Evidencia:* `local-evidence/published-helm-repository.txt` (curl del índice y de los paquetes); `local-evidence/helm-repository.txt`; `install.jsonl`.

**Si install.sh funciona de principio a fin**

Sí, en el laboratorio, con las opciones que exige el entorno (`--values-dir` de laboratorio, `--skip platform-argocd`, `--skip edge-mongodb` y `--separate-tiers`): 28 ejecuciones de Helm correctas (1550 s de Helm; 2336 s de `install.sh` completo), con las fases base, seguridad, datos, edge y empresa. El primer intento se detuvo en la fase base porque `install.sh` no registraba los repositorios de las dependencias antes de `helm dependency build` y Helm no tenía ninguno en `kb2`; se corrigió (commit 0a4cc19) y el segundo intento completó la instalación.

*Evidencia:* `raw/lab-20260924T081803/install.log`, `install.jsonl` y `state/install-summary.txt`; anexo.

**Si todos los recursos llevan la etiqueta iso42001**

Todos los recursos que definen los charts sí, salvo los hooks de Helm: 387 de 394 recursos renderizados (los 7 restantes son hooks, que Helm no pasa por el post-renderer) y 52 de 53 plantillas de pod. En el clúster, 307 de 391 objetos de los namespaces del catálogo (79 %) llevan `iso42001=true`; casi todo el resto no lo renderiza ningún chart: registros de release de Helm, `kube-root-ca.crt` y la ServiceAccount `default` de cada namespace, PVC generados desde `volumeClaimTemplates` y objetos generados por los operadores; la excepción son los hooks de Helm. La consulta `kubectl get pods,svc,deploy,sts -A -l iso42001=true` devuelve 127 recursos.

*Evidencia:* `local-evidence/verify-charts.txt` (verificación estática); `trace/traceability.json`; `local-evidence/unlabelled-objects.txt` (clasificación en el clúster local).

**Si el orden de instalación recomendado queda validado**

Sí. El orden base (namespaces, NetworkPolicy, CRD de Prometheus y Secrets), seguridad, datos, edge y empresa instaló cada chart con `--wait` a la primera, sin fallos de dependencias. Algunas dependencias que el orden respeta: PostgreSQL de plataforma antes que Keycloak (su base de datos); los CRD antes de los ServiceMonitor; las dos pasadas de cert-manager (la CA de plataforma) antes del TLS de OpenBao; MinIO antes que MLflow, Loki y el overlay documental; y la plataforma antes que los jobs del edge que escriben en ella. La fase de seguridad se validó sin Argo CD, que no se instaló.

*Evidencia:* `raw/lab-20260924T081803/install.log` e `install.jsonl` (orden y resultado de cada chart).


## 9. Discrepancias entre la tesis y el repositorio

| Tema | Tesis o enunciado | Repositorio y laboratorio | Propuesta |
|---|---|---|---|
| Número de charts | 28 charts, aunque sus listas suman 27 (según el enunciado) | `main`: 28 (11 edge, 13 plataforma, 4 empresa); rama: 30 (13, 13, 4) | Citar 30 y actualizar las listas con los dos charts nuevos |
| Gestor de secretos | HashiCorp Vault | OpenBao 2.0 (bifurcación de Vault con licencia MPL); el inyector, que usaba la imagen `hashicorp/vault-k8s`, está desactivado | Nombrar OpenBao y mencionar su origen |
| Edge Version Control | Chart con ese nombre | No existía en `main`; ahora es `edge-mlflow-sync` (nombre visible «Edge Version Control (MLflow Sync)») | Usar el nombre del chart |
| Edge Model Monitor | Chart con ese nombre | No existe; la monitorización del modelo en el edge (CMP-10) la hacen `edge-prometheus-agent` y las métricas de `edge-fastapi-model` | Sustituir por esos dos charts |
| Topología del laboratorio | Dos nodos amd64 (kb2 como plano de control y trabajo, worker1-kb2) sin nodo edge físico | Tres nodos: kb2 (VM, 4 vCPU, 8 GiB, solo plano de control y DaemonSets), worker1-kb2 (16 hilos, 31 GiB) y edgenode01 (Jetson AGX Orin, arm64, 8 núcleos, 61 GiB) como dispositivo edge | Describir la topología real; el edge sí es un dispositivo físico |
| Versiones | Helm 3.16.4 | Helm 3.19.0 y kubectl 1.29.0 en kb2 (fuera del desfase soportado respecto a 1.32; `install.log` lo advierte); K3s 1.32.6 coincide | Actualizar |
| Rancher | Clúster gestionado con Rancher | Gestionado por un Rancher externo (agente 2.13.3); no hay servidor Rancher en el clúster. `platform-rancher` (Rancher 2.11.3) no se desplegó ni validó | Indicar que el chart de Rancher no se validó |
| cert-manager | Se suponía instalado con Rancher | No había ninguno; el catálogo instala el suyo (v1.17.4) | Sin cambios en la tesis |
| Nivel de CMP-08 | Empresa | Prometheus en plataforma y agente en edge; los cuadros de mando, en empresa | Explicar que la recogida está en plataforma y la consulta en empresa |
| CMP-12 Feedback Interface | Componente recomendado de la arquitectura | Sin chart; solo existe la tabla `operator_feedback` en el almacén edge | Declararlo como hueco o trabajo futuro |
| Nivel edge sobre arm64 | Implementaciones de referencia sin restricción de arquitectura | Bitnami MongoDB no publica imágenes arm64; Falco no funciona sin BTF y NetworkPolicy no se aplica sin `ip_set_hash_ip` en el kernel de JetPack | Añadir requisitos del dispositivo edge (arquitectura y opciones del kernel) |

## 10. Limitaciones

- **Dispositivo edge.** El kernel de JetPack (`5.15.148-tegra`) no tiene BTF ni `ip_set_hash_ip`: Falco no se desplegó en `edgenode01` (S10 no se ejecutó) y las NetworkPolicy no se aplican en él (N06). Además, su node-exporter responde HTTP 503 (1 de 30 targets caído; el node-exporter previo de ese nodo acumulaba 2396 reinicios), y MongoDB no se instaló por falta de imagen arm64.
- **Componentes no validados.** `platform-argocd` (S15 y N11), `platform-rancher` y `edge-mongodb` no se instalaron; CMP-12 no tiene chart.
- **Repositorio Helm.** La instalación del laboratorio usó los charts del repositorio git; la instalación desde el repositorio publicado solo se validó en el clúster local, porque el publicado sigue construido desde `main`.
- **GPU.** La GPU de la Jetson no se usó: el modelo (Isolation Forest de scikit-learn) se sirve en CPU.
- **Datos.** Los datos de planta proceden de un simulador (OPC PLC), y la deriva se indujo con muestras desplazadas; las ventanas de laboratorio son cortas (intervalos de 1 s, ventana actual de 4 min, histórico de 2 h, espera entre reentrenamientos de 15 min) frente a los valores por defecto de los charts.
- **Pocas ejecuciones.** La instalación y la prueba de extremo a extremo se ejecutaron una vez, las pruebas de humo dos y las de red cuatro (hasta aislar sus causas); no hay repeticiones ni medidas estadísticas. Los consumos de CPU y memoria son muestras puntuales de `kubectl top`, y los pods listos, muestras al terminar cada `helm --wait`.
- **Caminos no ejercitados.** No se enviaron muestras inválidas, así que el rechazo de entrada (`sample_rejected`) no se observó en Loki; la llegada del log de auditoría del API a Loki no se comprobó; SSO con Keycloak en los demás servicios está desactivado por defecto; no se probaron alta disponibilidad, copias de seguridad ni recuperación.
- **OpenBao.** Se inicializó con una sola clave de desellado guardada en un Secret del laboratorio; al reiniciarse vuelve a quedar sellado (S13 lo muestra sellado antes de S13b) porque no hay desellado automático.
- **Imágenes.** Las imágenes de Bitnami proceden de `bitnamilegacy`, congeladas y sin parches de seguridad; las oficiales de Docker, del espejo público de ECR.
- **Concurrencia.** El job manual de sincronización y el CronJob de `edge-mlflow-sync` coincidieron una vez (E07: un `download_failed` entre `downloaded` y `active`); el estado final fue correcto, pero un job lanzado a mano no respeta la política de concurrencia del CronJob.
- **Pruebas de red.** Los clientes se lanzaron en `worker1-kb2` (el nodo sin plano de control que aplica políticas) y esperan 15 s a la sincronización del controlador; la protección de entrada de los pods del edge no se pudo comprobar.
- **Entorno compartido.** El clúster tenía cargas y despliegues ajenos (Argo CD, node-exporter y kube-state-metrics en `monitoring`, GPU operator); se retiró `ros2exp` con la confirmación del usuario y el resto se dejó intacto, compartiendo el namespace `monitoring`.

## Anexo. Ejecuciones y evidencias

| Ejecución | Contenido |
|---|---|
| lab-20260924T081803 | fases 1 a 7: entorno, preparación, instalación completa, humo, extremo a extremo, trazabilidad y red (red no evaluable: canario fallido) |
| lab-20260924T092125 | fases 4 y 7: humo de referencia tras corregir S04 |
| lab-20260924T093809 | fase 7: clientes en un nodo que aplica políticas, sin espera de sincronización |
| lab-20260924T095847 | fase 7 de referencia: canario con control positivo, espera de sincronización y N13 |
| raw/diag-*.txt | diagnóstico de cada nodo (diagnose-cluster.sh); tres de edgenode01 (hostname ubuntu): el inicial y los de antes y después de reiniciar k3s-agent |
| raw/node-exporter-logs.txt | log del node-exporter del catálogo en los tres nodos |
| local-evidence/ | pruebas en el clúster local (Docker Desktop, kind, arm64), no en el laboratorio: repositorio Helm, verificación estática y objetos sin etiqueta |

Un primer intento de instalación (`lab-20260924T075022`) se detuvo en la fase base por el error `no repository definition for https://prometheus-community.github.io/helm-charts` (salida de `install.log` comunicada por el usuario); su directorio se eliminó antes de repetir la ejecución. La corrección es el commit 0a4cc19.
