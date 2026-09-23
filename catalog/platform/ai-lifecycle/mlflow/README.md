# MLflow: Experiment Tracking and Model Registry

| Field | Value |
|-------|-------|
| **Chart** | `platform-mlflow` |
| **Tier** | Platform |
| **Namespace** | `mlops` |
| **Category** | AI Lifecycle |
| **RA Component** | Version Control (CMP-03, platform) |
| **ISO/IEC 42001** | B.6.1.3.2 · B.6.1.3.4 · B.6.2.6.4 |
| **Helm Chart** | `community-charts/mlflow` 0.18.0 (MLflow 2.22.1, wrapped), image `ghcr.io/burakince/mlflow:2.22.1` |
| **K3S Compatible** | Yes |

---

## Description

MLflow is the **AI lifecycle** platform implementing the platform **Version Control** component: it tracks experiments and keeps the registry of model versions that the edge follows.

Its roles in the reference architecture are:

- **Experiment tracking**: `platform-training-jobs` logs every run (parameters, metrics, training frame as reference data, data provenance tags); `platform-evidently` logs every drift report in the experiment `zdm-drift-monitoring`.
- **Model registry**: each run registers a version of `zdm-anomaly-detector`; the serving alias (`champion`) marks the version released to the edge. `edge-mlflow-sync` follows that alias.
- **Artefact store**: model files and reports in the MinIO bucket `mlflow-artifacts`, **served through the MLflow server** (`--serve-artifacts`): clients, including the edge, upload and download over HTTP and never hold object storage credentials.
- **Metadata**: PostgreSQL database `mlflow` on `platform-postgresql`, with schema migration at start-up.

The image `ghcr.io/burakince/mlflow` bundles the PostgreSQL (psycopg2) and S3 (boto3) drivers missing from the official image; the tag 2.14.0 referenced before does not exist. It is also the runtime of the catalog's training, drift, edge sync and model server code.

---

## ISO/IEC 42001 Mapping

| Clause | Requirement | How MLflow Addresses It |
|--------|-------------|--------------------------|
| B.6.1.3.2 | Resources: Version Control | Versioned models and artefacts; alias per environment |
| B.6.1.3.4 | Resources: Inventory / Registry | Registry of every model version with its run, data provenance and release criteria tag |
| B.6.2.6.4 | Operation: Retraining / Lifecycle | Scheduled, manual and drift-triggered runs linked to their versions |

---

## Prerequisites

- `platform-postgresql` (database `mlflow`) and `platform-minio` (bucket `mlflow-artifacts`, user `mlflow`).
- Secrets `platform-mlflow-db` (keys `username`, `password`) and `platform-mlflow-s3` (keys `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`), created by `infrastructure/install.sh`.
- `platform-prometheus` first (the chart ships a ServiceMonitor for `/mlflow/metrics`).

---

## Deployment Questionnaire

The Rancher questionnaire is [`manifests/questions.yaml`](./manifests/questions.yaml).

---

## Installation (Helm)

```bash
helm repo add cigip-upv https://cigip-upv.github.io/MLOps-ISO42001-K3s-Catalog
helm install platform-mlflow cigip-upv/platform-mlflow -n mlops

kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/chart=platform-mlflow
```

The upstream chart has no pod label hook: `infrastructure/install.sh` adds the iso42001 labels with its post-renderer.

---

## Key Configuration Decisions

| Decision | Options | Choice in this chart |
|----------|---------|----------------------|
| Artefact backend | Local filesystem / MinIO / S3 | **MinIO**, proxied by the MLflow server |
| Metadata backend | SQLite / PostgreSQL | **PostgreSQL** on the platform |
| Promotion | Stages / aliases | **Alias** `champion`, moved by the training job when the release criteria pass |
| Authentication | None / basic / OIDC proxy | **None inside the cluster**, reachable only through the NetworkPolicies (edge, monitoring); add an OIDC proxy before exposing it |
| Ingress | Enabled / disabled | **Disabled**; port-forward for operators |

---

## Model Promotion Workflow

```
platform-training-jobs -> MLflow run + registered version (release criteria tag)
     |  criteria passed
     v
alias champion -> new version
     |
     v
edge-mlflow-sync: download, verify, switch, reload edge-fastapi-model
```

---

## Related Solutions

- [Training Jobs](../training-jobs/README.md): produces the runs and versions
- [Evidently](../evidently/README.md): drift reports logged to MLflow
- [MinIO](../../data-management/minio/README.md): artefact storage backend
- [Edge Version Control](../../../edge/version-control/mlflow-sync/README.md): propagates the promoted version
