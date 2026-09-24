#!/usr/bin/env python3
"""Builds docs/lab-validation/INFORME_VALIDACION_LAB.md and results.json from
the laboratory evidence (raw/), the local evidence (local-evidence/) and the
catalog metadata (CHART_META, Chart.yaml, Chart.lock).

The texts of the report are in tools/report/: intro.md, netpol_note.md and
sections.py (sections 8 to 10). Usage, from the repository root:

    python3 docs/lab-validation/tools/build_report.py
"""
from __future__ import annotations

import json, pathlib, re, subprocess, sys, types

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[3]
LAB = ROOT / "docs/lab-validation"
TEXTS = LAB / "tools/report"


# The report describes the catalog that was validated (release 2.0.0), not
# the current working tree: its metadata is read from that commit.
CATALOG_REF = "c326de3"   # tip of lab-validation, released as v2.0.0


def git_show(path: str) -> str | None:
    r = subprocess.run(["git", "-C", str(ROOT), "show", f"{CATALOG_REF}:{path}"], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def catalog():
    p = types.ModuleType("publish_validated")
    p.__file__ = str(ROOT / "infrastructure/publish.py")
    exec(compile(git_show("infrastructure/publish.py"), "publish.py", "exec"), p.__dict__)
    out = {"iso_reqs": p.ISO_REQS, "components": p.COMPONENTS, "charts": []}
    for name, m in p.CHART_META.items():
        d = m["path"] + "/manifests"
        ch = yaml.safe_load(git_show(f"{d}/Chart.yaml"))
        lock_text = git_show(f"{d}/Chart.lock")
        lock = yaml.safe_load(lock_text) if lock_text else {}
        deps = [{"name": x["name"], "version": x["version"], "repository": x.get("repository", "")}
                for x in (lock or {}).get("dependencies", [])]
        out["charts"].append({
            "name": name, "tier": m.get("tier"), "namespace": m.get("namespace"),
            "display": ch["annotations"].get("mlops-iso42001.cigip-upv.es/display-name"),
            "version": ch["version"], "appVersion": str(ch.get("appVersion")), "deps": deps,
            "components": m.get("components", []),
            "clauses": [c.strip() for c in ch["annotations"].get("mlops-iso42001.cigip-upv.es/iso42001-clauses", "").split(",") if c.strip()]})
    return out


CAT = catalog()
RAW = LAB / "raw"
RUN_MAIN = RAW / "lab-20260924T081803"   # phases 1-7, full installation
RUN_SMOKE = RAW / "lab-20260924T092125"  # phases 4 and 7 (smoke reference)
RUN_NET = RAW / "lab-20260924T095847"    # phase 7 reference

def results(run):
    return [json.loads(l) for l in open(run / "results.jsonl")]

def esc(s):
    return str(s).replace("|", "\\|").replace("\n", " ")

charts = {c["name"]: c for c in CAT["charts"]}
TIER_ES = {"edge": "edge", "platform": "plataforma", "enterprise": "empresa"}

# ---------------------------------------------------------------------------
# 1. Environment
# ---------------------------------------------------------------------------
versions = dict(l.split(": ", 1) for l in (RUN_MAIN / "env/versions.txt").read_text().splitlines() if ": " in l)
nodes = json.load(open(RUN_MAIN / "env/nodes.json"))
def gib(ki): return round(int(ki.rstrip("Ki")) / 1024 / 1024, 1)
def top(path):
    rows = {}
    for l in (path).read_text().splitlines()[1:]:
        f = l.split()
        if len(f) >= 5 and f[0] != "NODE":
            rows[f[0]] = {"cpu": f[1], "cpu_pct": f[2], "memory": f[3], "memory_pct": f[4]}
    return rows
usage_before = top(RUN_MAIN / "env/node-usage-before.txt")
usage_after = top(RUN_MAIN / "state/after-install-top-nodes.txt")
usage_final = top(RUN_NET / "state/final-top-nodes.txt")
NODE_ROLE = {"kb2": "plano de control (máquina virtual Hyper-V); solo DaemonSets del catálogo (taint NoSchedule)",
             "worker1-kb2": "trabajador (Dell Precision 3640); niveles plataforma y empresa",
             "edgenode01": "dispositivo edge (NVIDIA Jetson AGX Orin); nivel edge"}
env = {
    "k3s": versions.get("k3s"), "kubernetes_server": versions.get("kubernetes server"),
    "kubectl_client": versions.get("kubectl client"), "helm": versions.get("helm"),
    "rancher": "gestionado por un Rancher externo; agente rancher/rancher-agent:v2.13.3 (no hay servidor Rancher en el clúster)",
    "cert_manager_before": "ninguno (lo instala el catálogo)",
    "storage_class": "local-path (por defecto), provisioner rancher.io/local-path, reclaimPolicy Delete, WaitForFirstConsumer",
    "cni": "flannel (K3s) con el controlador de NetworkPolicy de K3s (kube-router), activado para la validación",
    "catalog_commit_install": versions.get("catalog commit"),
    "nodes": [{"name": n["name"], "role": NODE_ROLE.get(n["name"], ""), "os": n["os"], "kernel": n["kernel"], "arch": n["arch"],
               "kubelet": n["kubelet"], "runtime": n["runtime"], "cpu": int(n["cpu"]), "memory_gib": gib(n["memory"]),
               "usage_before_install": usage_before.get(n["name"]), "usage_after_install": usage_after.get(n["name"]),
               "usage_final": usage_final.get(n["name"])} for n in sorted(nodes, key=lambda x: ["kb2", "worker1-kb2", "edgenode01"].index(x["name"]))],
}

# ---------------------------------------------------------------------------
# 2. Catalogue and laboratory status
# ---------------------------------------------------------------------------
SKIPPED = {
    "platform-rancher": "no instalado: el clúster ya lo gestiona un Rancher externo (install.sh nunca instala un segundo Rancher)",
    "platform-argocd": "no instalado: el namespace argocd ya tenía otro Argo CD (--skip-chart platform-argocd)",
    "edge-mongodb": "no instalado: el nodo edge es arm64 y las imágenes de Bitnami MongoDB solo existen para amd64 (--skip-chart edge-mongodb)",
}
catalog_rows = []
for tier in ("edge", "platform", "enterprise"):
    for c in [x for x in CAT["charts"] if x["tier"] == tier]:
        catalog_rows.append({**c, "tier_es": TIER_ES[tier], "lab": SKIPPED.get(c["name"], "instalado")})

# ---------------------------------------------------------------------------
# 3. Component -> chart -> clauses (Table 30)
# ---------------------------------------------------------------------------
ARCH = {  # from the task statement (annex A of the thesis)
    "CMP-01": ("Entorno; dispositivo (en la práctica, pasarela edge)", "Recomendado"),
    "CMP-02": ("Datos; edge y plataforma", "Recomendado"),
    "CMP-03": ("Integración; edge y plataforma", "Obligatorio"),
    "CMP-04": ("Modelo de IA; edge y plataforma", "Obligatorio"),
    "CMP-05": ("Datos; empresa", "Obligatorio"),
    "CMP-06": ("Entorno; empresa", "Recomendado"),
    "CMP-07": ("Entorno; empresa (Control de Acceso en plataforma)", "Recomendado"),
    "CMP-08": ("Entorno; empresa", "Recomendado"),
    "CMP-09": ("Entorno en edge y plataforma; Datos en empresa", "Recomendado"),
    "CMP-10": ("Datos en plataforma; subcomponente en edge", "Obligatorio"),
    "CMP-11": ("Datos en plataforma; Entorno en empresa", "Recomendado"),
    "CMP-12": ("Entorno; empresa", "Recomendado"),
    "CMP-13": ("Entorno; empresa", "Obligatorio"),
    "CMP-14": ("Modelo de IA; plataforma", "Recomendado"),
    "CMP-15": ("Entorno; edge y plataforma", "Recomendado"),
}
trace = {}
for l in (RUN_MAIN / "trace/traceability.tsv").read_text().splitlines()[1:]:
    k, label, n, cmd = l.split("\t")
    trace[k] = {"label": label, "resources": int(n), "command": cmd}
COMPONENT_NOTES = {
    "CMP-01": "Validación declarativa de la entrada en Node-RED (rangos, antigüedad, muestras rechazadas); transporte MQTT, Kafka y RabbitMQ; pasarela OPC UA",
    "CMP-02": "Edge: PostgreSQL (y MongoDB, no desplegado en el laboratorio); plataforma: TimescaleDB, PostgreSQL de servicios y MinIO; consolidación edge a plataforma",
    "CMP-03": "Plataforma: registro de modelos MLflow (y Argo CD para GitOps, no desplegado en el laboratorio); edge: edge-mlflow-sync",
    "CMP-04": "Edge: servidor FastAPI con la versión propagada; plataforma: entrenamiento (sin servicio de inferencia propio en plataforma)",
    "CMP-05": "Bucket con object lock (GOVERNANCE, 365 días) y versionado para documentación y fichas de modelo",
    "CMP-06": "Grafana con fuentes de datos y 6 cuadros de mando ZDM",
    "CMP-07": "Keycloak (realm ai-system); OpenBao para secretos",
    "CMP-08": "Prometheus y Alertmanager en plataforma; agente Prometheus en edge (remote-write)",
    "CMP-09": "Fluent Bit en todos los nodos hacia Loki, con almacenamiento en MinIO; configurado también para el log de auditoría del API (su llegada a Loki no se comprobó)",
    "CMP-10": "Métricas del modelo en edge (agente) y plataforma; deriva con Evidently",
    "CMP-11": "TimescaleDB (KPI, lotes de consolidación) y cuadros de mando de objetivos",
    "CMP-12": "Sin chart: hueco no cubierto (la tabla operator_feedback existe en el almacén edge, pero no hay interfaz)",
    "CMP-13": "Zammad",
    "CMP-14": "CronJob de deriva (Evidently) que registra la recomendación y lanza el reentrenamiento",
    "CMP-15": "Falco en edge y plataforma (no en el dispositivo edge del laboratorio); cert-manager y OpenBao",
}
component_rows = []
for cmp_id, name in CAT["components"].items():
    cs = [c for c in CAT["charts"] if cmp_id in c["components"]]
    clauses = sorted({cl for c in cs for cl in c["clauses"]})
    component_rows.append({"id": cmp_id, "name": name, "layer_level": ARCH[cmp_id][0], "criticality": ARCH[cmp_id][1],
                           "charts": [f'{c["name"]} ({TIER_ES[c["tier"]]})' for c in cs], "clauses": clauses,
                           "lab_resources": trace.get(cmp_id, {}).get("resources"), "notes": COMPONENT_NOTES[cmp_id],
                           "coverage": "cubierto" if cs else "no cubierto"})
SUBCOMPONENTS = [
    ("Flujo de consolidación de datos (Data Stock edge a plataforma)", "edge-postgresql-sync", "cubierto", "E04 y E11"),
    ("Flujo de propagación de versiones (Version Control plataforma a edge)", "edge-mlflow-sync", "cubierto", "E07 y E14"),
    ("Industrial Protocol Gateway", "edge-opc-ua-gateway (Telegraf, OPC UA a MQTT)", "cubierto", "E02"),
    ("Model Training Pipeline", "platform-training-jobs", "cubierto", "E05 y E13"),
    ("Access Control (plataforma)", "enterprise-keycloak, platform-openbao, NetworkPolicies de infrastructure/", "cubierto", "S11, S13b, N01 a N13"),
    ("Business Dashboard", "enterprise-grafana-dashboards", "cubierto", "S08"),
    ("RAW Data", "platform-minio (bucket datasets), tema sensor-raw de edge-kafka", "parcial: almacenamiento disponible, sin flujo que lo alimente", "S02, S03"),
    ("Dataset Catalogue", "sin chart; procedencia de datos en las etiquetas de cada versión de MLflow", "parcial", "E06"),
    ("Feature Engineering Pipeline", "sin chart propio; agregación por intervalos en el job de entrenamiento", "parcial", "E05"),
    ("API Gateway", "sin chart", "no cubierto", "-"),
    ("ERP/MES Integration", "sin chart", "no cubierto", "-"),
]

# ---------------------------------------------------------------------------
# 4. Deployment by level (Table 31)
# ---------------------------------------------------------------------------
install = [json.loads(l) for l in open(RUN_MAIN / "install.jsonl")]
INSTALL_NOTES = {
    "platform-cert-manager": "Dos pasadas por diseño: la segunda crea los emisores de la CA de plataforma cuando ya existen los CRD",
    "platform-openbao": "0/1 listo al terminar Helm porque OpenBao arranca sellado; S13b lo inicializa y desella (1/1)",
    "platform-prometheus": "5/7 en el instante de la medida; al final, todo en Running. El node-exporter del dispositivo edge responde 503 (1 de 30 targets caído)",
    "platform-mlflow": "El más lento de plataforma (descarga de la imagen de MLflow)",
    "enterprise-keycloak": "Imagen 25.0.6 con proxyHeaders xforwarded",
    "edge-fluent-bit": "DaemonSet en los 3 nodos (2/3 en el instante de la medida, 3/3 al final)",
    "edge-falco": "Solo en los nodos amd64 (el kernel del dispositivo edge no tiene BTF); 3/4 en el instante de la medida, todo en Running al final",
    "enterprise-minio-overlay": "0/1: el pod es el Job de aprovisionamiento, que termina en Completed",
    "platform-training-jobs": "Solo CronJob (sin pods permanentes)",
    "edge-mlflow-sync": "Solo CronJob", "edge-postgresql-sync": "Solo CronJob", "enterprise-grafana-dashboards": "Solo ConfigMaps",
    "edge-kafka": "KRaft de un nodo en el dispositivo edge (arm64)",
    "enterprise-zammad": "El más lento del catálogo; 4/4 pods listos",
}
seen = {}
deploy_rows = []
for r in install:
    seen[r["chart"]] = seen.get(r["chart"], 0) + 1
    c = charts[r["chart"]]
    deploy_rows.append({"chart": r["chart"] + (" (2.ª pasada)" if seen[r["chart"]] == 2 else ""), "tier": c["tier"], "tier_es": TIER_ES[c["tier"]],
                        "namespace": r["namespace"], "result": "correcto" if r["result"] == "ok" else "fallido",
                        "seconds": r["seconds"], "pods_ready_at_end_of_helm": r["pods_ready"],
                        "notes": INSTALL_NOTES.get(r["chart"], "") if seen[r["chart"]] == 1 or r["chart"] != "platform-cert-manager" else "Segunda pasada (emisores)"})
for name, why in SKIPPED.items():
    c = charts[name]
    deploy_rows.append({"chart": name, "tier": c["tier"], "tier_es": TIER_ES[c["tier"]], "namespace": c["namespace"], "result": "omitido",
                        "seconds": None, "pods_ready_at_end_of_helm": None, "notes": why})
PARTIAL = {"edge-falco": "parcial", "platform-prometheus": "parcial"}
PLACEMENT = {
    "edge": "Sus pods corren en `edgenode01`, salvo los DaemonSets (Fluent Bit en los tres nodos; Falco en los dos amd64) y una réplica de falcosidekick.",
    "platform": "Sus pods corren en `worker1-kb2`, salvo el DaemonSet de node-exporter (tres nodos).",
    "enterprise": "Sus pods corren en `worker1-kb2`.",
}
for d in deploy_rows:
    if d["chart"] in PARTIAL:
        d["result"] = PARTIAL[d["chart"]]
install_total = sum(r["seconds"] for r in install)
install_script_seconds = next(r["seconds"] for r in results(RUN_MAIN) if r["id"] == "INST-00")

# ---------------------------------------------------------------------------
# 5. Smoke, end to end and network
# ---------------------------------------------------------------------------
smoke = [r for r in results(RUN_SMOKE) if r["phase"] == "smoke"]
smoke_first = {r["id"]: r for r in results(RUN_MAIN) if r["phase"] == "smoke"}
e2e = [r for r in results(RUN_MAIN) if r["phase"] == "e2e"]
E2E_SUMMARY = {
    "E01": "Simulador OPC PLC (mcr.microsoft.com/iotedge/opc-plc:2.15.5) desplegado en el namespace edge",
    "E02": "Telegraf lee el simulador por OPC UA: 3548 métricas recogidas, 0 errores",
    "E03": "Node-RED valida y escribe en el almacén edge: sensor_features pasa de 3181 a 3299 filas en 30 s (4 variables de cnc-01)",
    "E04": "edge-postgresql-sync consolida en TimescaleDB: lote 15, filas 3181 a 3320, 139 leídas y 139 escritas, estado ok",
    "E05": "Entrenamiento con 831 muestras de TimescaleDB; versión 1 registrada y promovida (tasa de anomalías 0,0205, criterio de liberación cumplido)",
    "E06": "Registro MLflow: alias champion a la versión 1, con etiquetas de procedencia (origen, ventana, intervalo, filas, lote de consolidación)",
    "E07": "edge-mlflow-sync detecta la versión 1, la descarga (sha256 8ce9e011...) y la activa; model_versions registra downloaded, download_failed (ejecución concurrente del CronJob) y active",
    "E08": "Inferencia con la versión 1: una muestra normal (0,5732) y una anómala (0,7076), registradas en predictions",
    "E09": "Prometheus de plataforma recibe por remote-write model_predictions_total, model_info (versión 1), ingest_messages_valid_total (3688) y métricas de la pasarela: 4 de 4 consultas con datos",
    "E10": "300 s de muestras desplazadas de la máquina cnc-02 publicadas por MQTT con el usuario de la pasarela",
    "E11": "Segunda consolidación: lotes 23 y 25 (854 y 366 filas); cnc-01 con 5320 filas y cnc-02 con 1200 en plataforma",
    "E12": "Evidently: deriva en las 4 variables (proporción 1,0 frente al umbral 0,5); recomendación 1 registrada y Job de reentrenamiento creado",
    "E13": "Reentrenamiento lanzado por la recomendación con 1631 muestras; versión 2 registrada y promovida",
    "E14": "edge-mlflow-sync activa la versión 2 (antes 1); la inferencia responde con model_version 2",
    "E15": "Loki (vía Fluent Bit) contiene los eventos model_registered, version_activated, recommendation, drift_computed, prediction y los del job de consolidación (6 de 7 tipos; sample_rejected no se produjo porque no se enviaron muestras inválidas)",
    "E16": "La interfaz de Evidently contiene el proyecto zdm-anomaly-detector con los informes de deriva",
}
net = [r for r in results(RUN_NET) if r["phase"] == "netpol"]
canary = (RUN_NET / "netpol/N-CANARY.txt").read_text()
def np_nodes(tid):
    f = RUN_NET / f"netpol/{tid}.txt"
    if not f.exists():
        return "", ""
    m = re.search(r"client node: (\S+); destination node\(s\): (.+)", f.read_text())
    return (m.group(1), m.group(2).strip()) if m else ("", "")

# ---------------------------------------------------------------------------
# 6. Traceability
# ---------------------------------------------------------------------------
coverage = json.load(open(RUN_MAIN / "trace/traceability.json"))["coverage_by_namespace"]
static = json.load(open(LAB / "local-evidence/verify-charts.json"))
static_items = static if isinstance(static, list) else list(static.values())
static_summary = {"charts": len(static_items),
                  "resources": sum(x["resources"] for x in static_items),
                  "labelled_resources": sum(x["labelled_resources"] for x in static_items),
                  "workloads": sum(x["workloads"] for x in static_items),
                  "labelled_pod_templates": sum(x["labelled_pod_templates"] for x in static_items),
                  "unlabelled": {x["chart"]: x["unlabelled_resources"] for x in static_items if x["unlabelled_resources"]}}
cov_catalog = {ns: v for ns, v in coverage.items() if ns != "argocd"}
cov_obj = sum(v["objects"] for v in cov_catalog.values())
cov_lab = sum(v["with_iso42001_label"] for v in cov_catalog.values())

# ---------------------------------------------------------------------------
# 7. Refinements
# ---------------------------------------------------------------------------
REFINEMENTS = [
    # (change, gap or problem, effect, where detected, commits)
    ("Chart nuevo edge-postgresql-sync", "Flujo de consolidación de datos (Data Stock edge a plataforma) sin soporte", "CronJob con marca de agua y lotes idempotentes registrados en consolidation_batches; validado en E04 y E11", "Fase 1 (auditoría)", "41eb9d7"),
    ("Chart nuevo edge-mlflow-sync y servidor de modelo funcional", "Flujo de propagación de versiones y CMP-03 en edge sin chart; edge-fastapi-model sin imagen utilizable", "Sigue el alias champion de MLflow, descarga, verifica sha256, activa y recarga el servidor; validado en E07, E08 y E14", "Fase 1", "a37727f"),
    ("Pipeline de entrenamiento y recomendación de reentrenamiento", "CMP-14 sin implementación operativa", "Entrenamiento con criterios de liberación y CronJob de deriva (Evidently) que recomienda y lanza el reentrenamiento; validado en E05, E12 y E13", "Fase 1", "cd6711d"),
    ("Flujo declarativo de validación de entrada en Node-RED", "CMP-01 solo tenía transporte, sin validación de datos de entrada", "Rangos, antigüedad y muestras rechazadas con métricas; validado en E03 y S06", "Fase 1", "74a4af5"),
    ("Pasarela OPC UA con Telegraf en lugar de Neuron", "La edición libre de Neuron no tiene controlador OPC UA (subcomponente Industrial Protocol Gateway)", "OPC UA a MQTT con autenticación; validado en E02", "Fase 1", "e34129b"),
    ("TimescaleDB con plantillas propias", "timescaledb-single está obsoleto; almacén de plataforma y KPI (CMP-02, CMP-11)", "Hipertablas, roles y tablas de consolidación y recomendaciones; validado en S16", "Fase 1", "057e418"),
    ("Almacén documental con object lock", "El overlay de MinIO no aplicaba el bloqueo ni lo consumía nadie (CMP-05)", "Job de aprovisionamiento con object lock GOVERNANCE 365 días y versionado; validado en S02", "Fase 1", "2ca5579"),
    ("Cuadros de mando importables y reglas de alerta reales", "Cuadros de mando en pseudo-JSON y reglas sobre métricas inexistentes (CMP-06, CMP-08, CMP-11)", "6 cuadros de mando ZDM y 8 reglas; validado en S07 y S08", "Fase 1", "1601171"),
    ("Correcciones de charts de terceros (Kafka, MongoDB, PostgreSQL, MLflow, RabbitMQ, Keycloak, Zammad, Argo CD, cert-manager, OpenBao, Rancher, Falco, agente Prometheus)", "Imágenes retiradas, secretos inexistentes, claves de values ignoradas, plantillas ausentes y reglas de Falco que no compilaban", "Los 30 charts pasan lint, render y kubeconform (1.32); 27 charts desplegados sin fallos en el laboratorio", "Fase 1 y pruebas locales", "5dab858, 19b88cd, 609c926, 07f33a0, a59efca, e93c232, f960157, ba644a6, af8fd35"),
    ("Imágenes oficiales desde el espejo público de ECR", "Límite de descargas anónimas de Docker Hub (429) durante las pruebas", "Menos dependencia de Docker Hub", "Pruebas locales", "95a75d7"),
    ("Política de auditoría del API y enable-audit.sh", "setup-ubuntu.sh activaba la auditoría sin política, sin registrar nada (B.6.2.8.1)", "Log de auditoría activo en el laboratorio (7429 eventos al comprobarlo); Fluent Bit está configurado para enviarlo a Loki, sin comprobación en esta validación", "Fase 1", "26a92cd"),
    ("NetworkPolicy por zonas en todos los namespaces", "platform, minio, falco, logging y cattle-system sin políticas; egress de mlops solo DNS UDP", "Denegación por defecto y conductos explícitos; validado en N01 a N13 en los nodos que aplican políticas", "Fase 1", "26a92cd"),
    ("install.sh por fases con los charts propios", "Instalaba charts de terceros, manifiestos inexistentes y dejaba fuera 10 charts", "Fases base, seguridad, datos, edge y empresa con secretos generados, post-renderer de etiquetas y registro JSON; validado en el laboratorio (27 charts, 28 ejecuciones de Helm)", "Fase 1", "4f17e2d, 2712b1e"),
    ("publish.py con helm dependency build y paquetes publicados por CI", "index.yaml apuntaba a .tgz inexistentes (404) y los envolventes salían sin subcharts", "30 paquetes con dependencias; repositorio validado en local (30/30)", "Fase 1", "c8cab72, 8d83879"),
    ("verify_charts.py e iso42001-postrender.py", "Sin verificación automática ni etiquetas en recursos de subcharts sin gancho de etiquetas", "387 de 394 recursos renderizados etiquetados (los 7 restantes son hooks de Helm)", "Fase 1", "c02a7b4"),
    ("Documentación alineada (README, catalog/README.md, index.html, CITATION.cff) y versión 2.0.0 con CHANGELOG", "Deriva documental y etiquetas ISO distintas en tres sitios", "Una sola fuente (CHART_META) para tablas y metadatos", "Fase 1", "d7a3202, 3d90b41, 39eb2a5"),
    ("Fichero de contraseñas de Mosquitto propiedad del broker", "El broker (uid 1883) no podía leer el fichero y el pod no arrancaba", "Mosquitto arranca con autenticación; S04 y E03", "Pruebas locales (Kubernetes)", "d7048db"),
    ("Paso de preparación de Node-RED con el usuario de Node-RED", "Las credenciales escritas por el init container no eran legibles", "Node-RED arranca y se conecta al broker", "Pruebas locales (Kubernetes)", "5473a3f"),
    ("Métricas de Keycloak en el puerto de gestión 9000", "El ServiceMonitor apuntaba a 8080, donde /metrics da 404", "Target de Keycloak activo", "Pruebas locales (Kubernetes)", "02838e8"),
    ("NetworkPolicies de los subcharts de Bitnami desactivadas", "Kafka, MongoDB, las dos PostgreSQL y Keycloak creaban políticas que admitían tráfico desde cualquier namespace y anulaban la denegación por defecto", "Un pod de fuera del catálogo ya no alcanza la PostgreSQL del edge (N06 en el clúster local)", "Pruebas locales (Kubernetes)", "8b7937e"),
    ("Regla del API server solo en el puerto 6443", "La regla abría 443 hacia 0.0.0.0/0 en todos los namespaces (salida HTTPS a Internet)", "mlops ya no sale a Internet (N08 en el laboratorio)", "Pruebas locales (análisis de N08)", "5202b6a"),
    ("install.sh registra los repositorios de las dependencias", "Con Helm sin repositorios, helm dependency build fallaba y la instalación se detenía en la fase base", "Instalación completa en el laboratorio", "Laboratorio (primer intento)", "0a4cc19"),
    ("install.sh --separate-tiers y namespaces ajenos intactos", "El planificador podía colocar pods de plataforma en el dispositivo edge; un namespace argocd ajeno habría recibido nuestras políticas", "Pods edge en edgenode01, plataforma y empresa en worker1-kb2, kb2 solo con DaemonSets", "Diagnóstico del laboratorio", "693b349"),
    ("appVersion de Keycloak alineado con la imagen", "Chart.yaml declaraba 24.0.0 y se despliega 25.0.6", "Metadatos coherentes", "Redacción del informe", "d5428ea"),
]

# ---------------------------------------------------------------------------
# JSON
# ---------------------------------------------------------------------------
data = {
    "report": "docs/lab-validation/INFORME_VALIDACION_LAB.md",
    "runs": {
        "lab-20260924T081803": "fases 1 a 7: entorno, preparación, instalación completa, humo, extremo a extremo, trazabilidad y red (red no evaluable: canario fallido)",
        "lab-20260924T092125": "fases 4 y 7: humo de referencia tras corregir S04",
        "lab-20260924T093809": "fase 7: clientes en un nodo que aplica políticas, sin espera de sincronización",
        "lab-20260924T095847": "fase 7 de referencia: canario con control positivo, espera de sincronización y N13",
    },
    "environment": env,
    "catalog": {"total": len(CAT["charts"]), "by_tier": {t: sum(1 for c in CAT["charts"] if c["tier"] == t) for t in ("edge", "platform", "enterprise")},
                "charts": catalog_rows},
    "component_map": component_rows,
    "subcomponents_and_flows": [dict(zip(("item", "charts", "coverage", "evidence"), s)) for s in SUBCOMPONENTS],
    "deployment": {"rows": deploy_rows, "helm_seconds_total": install_total, "install_script_seconds": install_script_seconds, "run": "lab-20260924T081803",
                   "command": "infrastructure/install.sh --values-dir docs/lab-validation/lab-values --site-id lab-edge-01 --skip platform-argocd --skip edge-mongodb --separate-tiers"},
    "smoke": {"run": "lab-20260924T092125", "tests": smoke,
              "first_run_differences": {k: v for k, v in smoke_first.items() if v["result"] != next((s["result"] for s in smoke if s["id"] == k), None)}},
    "end_to_end": {"run": "lab-20260924T081803", "tests": [{**r, "summary": E2E_SUMMARY[r["id"]]} for r in e2e]},
    "network_policies": {"run": "lab-20260924T095847", "canary": canary, "tests": [{**r, "client_node": np_nodes(r["id"])[0], "destination_nodes": np_nodes(r["id"])[1]} for r in net]},
    "traceability": {"run": "lab-20260924T081803", "queries": [{"key": k, **v} for k, v in trace.items()], "coverage_by_namespace": coverage,
                     "coverage_catalog_namespaces": {"objects": cov_obj, "with_iso42001_label": cov_lab}, "static_verification": static_summary},
    "refinements": [dict(zip(("change", "gap", "effect", "detected_in", "commits"), r)) for r in REFINEMENTS],
}

# ---------------------------------------------------------------------------
# Markdown helpers
# ---------------------------------------------------------------------------
def table(headers, rows):
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(esc(x) for x in r) + " |" for r in rows]
    return "\n".join(out)

def deps(c):
    return ", ".join(f'{d["name"]} {d["version"]}' for d in c["deps"]) or "propio"

md = []
A = md.append
A((TEXTS / "intro.md").read_text().replace("{{INSTALL_TOTAL}}", f"{install_script_seconds} s de install.sh ({install_total} s de Helm)"))

# 1
A("\n## 1. Entorno\n")
A(table(["Elemento", "Valor"], [
    ["K3s", env["k3s"]], ["Kubernetes (servidor)", env["kubernetes_server"]], ["kubectl (cliente en kb2)", env["kubectl_client"]],
    ["Helm (en kb2)", env["helm"]], ["Rancher", env["rancher"]], ["cert-manager previo", env["cert_manager_before"]],
    ["Red", env["cni"]], ["StorageClass", env["storage_class"]], ["Commit del catálogo en la instalación", env["catalog_commit_install"]]]))
A("\nFuente: `raw/lab-20260924T081803/env/versions.txt` (generado con `k3s --version`, `kubectl version`, `helm version --short`) y los diagnósticos `raw/diag-*.txt` (`diagnose-cluster.sh`).\n")
A(table(["Nodo", "Función", "SO y kernel", "Arquitectura", "CPU", "RAM (GiB)", "Uso antes / después de instalar / final"], [
    [n["name"], n["role"], f'{n["os"]}, {n["kernel"]}', n["arch"], n["cpu"], n["memory_gib"],
     " / ".join(f'{u["cpu"]} CPU, {u["memory"]}' if u else "-" for u in (n["usage_before_install"], n["usage_after_install"], n["usage_final"]))]
    for n in env["nodes"]]))
A("\nFuente: `env/nodes.json` (`kubectl get nodes -o json`) y `kubectl top nodes` en `env/node-usage-before.txt`, `state/after-install-top-nodes.txt` y `raw/lab-20260924T095847/state/final-top-nodes.txt`. Entre la medida posterior a la instalación y la final se eliminaron cargas ajenas del dispositivo edge (namespace ros2exp), con confirmación del usuario.\n")

# 2
A("\n## 2. Catálogo final\n")
bt = data["catalog"]["by_tier"]
A(f'**{data["catalog"]["total"]} charts**: {bt["edge"]} de edge, {bt["platform"]} de plataforma y {bt["enterprise"]} de empresa (en `main` había 28: 11, 13 y 4). Todos en la versión 0.3.0 de la rama `lab-validation`.\n')
A(table(["Nivel", "Chart", "Versión (app)", "Dependencia de terceros", "Namespace", "Componentes", "Cláusulas ISO/IEC 42001", "Laboratorio"], [
    [r["tier_es"], r["name"], f'{r["version"]} ({r["appVersion"]})', deps(r), r["namespace"], ", ".join(r["components"]) or "-", ", ".join(r["clauses"]), r["lab"]]
    for r in catalog_rows]))
A("\nFuente: `CHART_META` de `infrastructure/publish.py`, `Chart.yaml` y `Chart.lock` de cada chart.\n")

# 3
A("\n## 3. Correspondencia componente, chart y cláusulas (Tabla 30)\n")
A(table(["Componente", "Capa y nivel (arquitectura)", "Criticidad", "Chart(s)", "Cláusulas (de sus charts)", "Recursos en el laboratorio", "Cobertura y observaciones"], [
    [f'{r["id"]} {r["name"]}', r["layer_level"], r["criticality"], ", ".join(r["charts"]) or "-", ", ".join(r["clauses"]) or "-",
     r["lab_resources"], f'{r["coverage"]}. {r["notes"]}'] for r in component_rows]))
A("\n\"Recursos en el laboratorio\": pods, servicios, deployments y statefulsets con la etiqueta del componente (`kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/<CMP>`), en `trace/traceability.tsv`.\n")
A("\n**Subcomponentes y flujos**\n")
A(table(["Subcomponente o flujo", "Chart(s)", "Cobertura", "Evidencia"], [list(s) for s in SUBCOMPONENTS]))

# 4
A("\n## 4. Resultados del despliegue por nivel (Tabla 31)\n")
A(f'Comando (ejecutado por `run-lab-validation.sh`, fase 3): `{data["deployment"]["command"]}`. Duración de `install.sh`: {install_script_seconds} s (unos {round(install_script_seconds/60)} min); de ellos, {install_total} s en las 28 ejecuciones de `helm upgrade --install --wait` (la mayor parte, descarga de imágenes) y el resto en la fase base, el registro de repositorios y la construcción de dependencias de cada chart. Fuente: `raw/lab-20260924T081803/install.jsonl` e `install.log`.\n')
A('"Pods listos" es la muestra tomada al terminar `helm upgrade --install --wait` de cada chart; el estado final de todos los pods está en `state/final-pods.txt`.\n')
for tier in ("edge", "platform", "enterprise"):
    rows = [d for d in deploy_rows if d["tier"] == tier]
    ok = sum(1 for d in rows if d["result"] in ("correcto", "parcial"))
    om = sum(1 for d in rows if d["result"] == "omitido")
    A(f'\n**Nivel {TIER_ES[tier]}** ({ok} instalados; {om} {"omitido" if om == 1 else "omitidos"}). {PLACEMENT[tier]}\n')
    A(table(["Chart", "Namespace", "Resultado", "Tiempo (s)", "Pods listos", "Observaciones"],
            [[d["chart"], d["namespace"], d["result"], d["seconds"] if d["seconds"] is not None else "-", d["pods_ready_at_end_of_helm"] or "-", d["notes"]] for d in rows]))

# 5
A("\n## 5. Pruebas de humo y de extremo a extremo\n")
A("\n### 5.1 Pruebas de humo\n")
A("Ejecución de referencia `raw/lab-20260924T092125` (fase 4 repetida tras corregir S04). Resultado: "
  + ", ".join(f'{sum(1 for s in smoke if s["result"] == k)} {k}' for k in ("PASS", "FAIL", "SKIP")) + ".\n")
A(table(["ID", "Prueba", "Resultado", "Comando", "Salida resumida"], [[s["id"], s["name"], s["result"], s["command"], s["detail"][:260]] for s in smoke]))
A("\nEn la primera ejecución (`raw/lab-20260924T081803`) S04 falló: el test publicaba una sola vez a los 2 s y el suscriptor, con el broker en otro nodo, aún no estaba suscrito. El flujo real sí funcionaba con autenticación (E03). Se corrigió el test para publicar hasta recibir (commit 0fc2b13) y en la repetición pasa.\n")
A("\n### 5.2 Prueba de extremo a extremo\n")
A("Ejecución `raw/lab-20260924T081803`, fase 5: 16 de 16 tramos correctos.\n")
A(table(["Tramo", "Prueba", "Resultado", "Tiempo (s)", "Comando", "Evidencia resumida"], [[r["id"], r["name"], r["result"], r["seconds"], r["command"], E2E_SUMMARY[r["id"]]] for r in e2e]))
A("\n### 5.3 NetworkPolicy\n")
A("Ejecución de referencia `raw/lab-20260924T095847`. Cada prueba lanza un pod cliente con `nc -z -w 5` en el namespace de origen, en un nodo que aplica políticas, tras esperar 15 s a que el controlador lo incluya en sus reglas.\n")
A("\nCanario (un pod con `httpd` en cada nodo; accesible desde otro namespace sin política y bloqueado con una política de denegación total):\n")
A("```\n" + "\n".join(l for l in canary.splitlines() if l.startswith(("edgenode01", "kb2", "worker1"))) + "\n```\n")
A(table(["ID", "Prueba", "Resultado", "Nodo cliente", "Nodo destino", "Salida"], [[r["id"], r["name"], r["result"], np_nodes(r["id"])[0] or "-", np_nodes(r["id"])[1] or "-", "ver el bloque del canario" if r["id"] == "N-CANARY" else r["detail"][:160]] for r in net]))
A((TEXTS / "netpol_note.md").read_text())

# 6
A("\n## 6. Consultas por etiqueta iso42001\n")
A("Ejecución `raw/lab-20260924T081803`, fase 6 (`tools/traceability.py`). Esquema de etiquetas: `iso42001=true` en todo recurso del catálogo y `mlops-iso42001.cigip-upv.es/<cláusula>=true` y `mlops-iso42001.cigip-upv.es/<CMP>=true` según `CHART_META`.\n")
A(table(["Clave", "Descripción", "Recursos (pods, svc, deploy, sts)", "Comando"], [[k, v["label"], v["resources"], v["command"]] for k, v in trace.items()]))
A("\n**Cobertura de la etiqueta por namespace** (todos los tipos de objeto; se cuentan aparte los de otros releases de Helm en namespaces compartidos):\n")
A(table(["Namespace", "Objetos", "Con iso42001=true", "De otros releases"], [[ns, v["objects"], v["with_iso42001_label"], v["other_releases"]] for ns, v in coverage.items()]))
A(f'\nEn los namespaces del catálogo (sin `argocd`, que es de otro despliegue) llevan la etiqueta {cov_lab} de {cov_obj} objetos ({round(100*cov_lab/cov_obj)} %). '
  f'La verificación estática (`verify_charts.py --post-render`, `local-evidence/verify-charts.txt`) etiqueta {static_summary["labelled_resources"]} de {static_summary["resources"]} recursos renderizados '
  f'y {static_summary["labelled_pod_templates"]} de {static_summary["workloads"]} plantillas de pod; los 7 recursos restantes son hooks de Helm, que no pasan por el post-renderer. '
  'Casi todos los objetos sin etiqueta en el clúster no los renderiza ningún chart (análisis en el clúster local, `local-evidence/unlabelled-objects.txt`): registros de release de Helm, `kube-root-ca.crt` y la ServiceAccount `default` que crea Kubernetes, PVC generados desde `volumeClaimTemplates`, objetos que generan los operadores (Prometheus, Alertmanager, cert-manager) y el simulador de pruebas; la excepción es un hook de Helm.\n')

# 7
A("\n## 7. Refinamientos\n")
A(table(["Cambio", "Hueco o problema", "Efecto", "Detectado en", "Commits"], [list(r) for r in REFINEMENTS]))
A("\nNo se aplicó ningún cambio \"por completitud\": CMP-12 (Feedback Interface) sigue sin chart porque su propuesta no se aprobó en la fase 1. También se añadieron herramientas de validación que no forman parte del catálogo: `run-lab-validation.sh`, `diagnose-cluster.sh` y `tools/`.\n")

exec((TEXTS / "sections.py").read_text())   # ANSWERS, DISCREPANCIES, LIMITATIONS

A("\n## 8. Respuestas a las preguntas del capítulo 7\n")
for q, ans, ev in ANSWERS:
    A(f"**{q}**\n\n{ans}\n\n*Evidencia:* {ev}\n")
A("\n## 9. Discrepancias entre la tesis y el repositorio\n")
A(table(["Tema", "Tesis o enunciado", "Repositorio y laboratorio", "Propuesta"], [list(d) for d in DISCREPANCIES]))
A("\n## 10. Limitaciones\n")
for t, d in LIMITATIONS:
    A(f"- **{t}.** {d}.")
A("\n## Anexo. Ejecuciones y evidencias\n")
A(table(["Ejecución", "Contenido"], [[k, v] for k, v in data["runs"].items()] + [
    ["raw/diag-*.txt", "diagnóstico de cada nodo (diagnose-cluster.sh); tres de edgenode01 (hostname ubuntu): el inicial y los de antes y después de reiniciar k3s-agent"],
    ["raw/node-exporter-logs.txt", "log del node-exporter del catálogo en los tres nodos"],
    ["local-evidence/", "pruebas en el clúster local (Docker Desktop, kind, arm64), no en el laboratorio: repositorio Helm, verificación estática y objetos sin etiqueta"]]))
A("\nUn primer intento de instalación (`lab-20260924T075022`) se detuvo en la fase base por el error `no repository definition for https://prometheus-community.github.io/helm-charts` (salida de `install.log` comunicada por el usuario); su directorio se eliminó antes de repetir la ejecución. La corrección es el commit 0a4cc19.\n")

(LAB / "INFORME_VALIDACION_LAB.md").write_text("\n".join(md).rstrip() + "\n")
data["answers"] = [dict(zip(("question", "answer", "evidence"), a)) for a in ANSWERS]
data["discrepancies"] = [dict(zip(("topic", "thesis", "repository_and_laboratory", "proposal"), d)) for d in DISCREPANCIES]
data["limitations"] = [dict(zip(("topic", "detail"), l)) for l in LIMITATIONS]
(LAB / "results.json").write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
print("report and results.json written")
