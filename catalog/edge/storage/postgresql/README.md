# PostgreSQL: Edge Data Stock

| Field | Value |
|-------|-------|
| **Chart** | `edge-postgresql` |
| **Tier** | Edge |
| **Namespace** | `edge` |
| **Category** | Storage |
| **RA Component** | Data Stock (CMP-02, edge) |
| **ISO/IEC 42001** | B.6.2.6.1 · B.6.2.6.3 · B.6.2.8.1 |
| **Helm Chart** | `bitnami/postgresql` (wrapped), image `bitnamilegacy/postgresql:16.4.0-debian-12-r14` |
| **K3S Compatible** | Yes |

---

## Description

PostgreSQL is the **local persistent storage** of the edge, the edge **Data Stock** component. It keeps recent plant data, inference results and operational metadata close to the machines, independent of platform connectivity. Database `zdm_edge`, application user `edge_app`.

Schema created on first start (`primary.initdb`):

| Table | Written by | Content |
|-------|------------|---------|
| `sensor_features` | `edge-node-red` (validated OPC UA samples) | One row per machine, signal and sample |
| `predictions` | `edge-fastapi-model` | Timestamp, machine, model name and version, input hash, score, label |
| `operator_feedback` | (no capture interface in the catalog) | Feedback on predictions |
| `model_versions` | `edge-mlflow-sync` | Version history of edge version control, with SHA-256 and status |
| `system_events` | operational tools | Structured events |

`edge-postgresql-sync` reads `sensor_features` and `predictions` and consolidates them into the platform data stock (`platform-timescaledb`).

Bitnami moved its versioned images to `docker.io/bitnamilegacy`, which receives no new security patches; replace it with a maintained image for production.

---

## ISO/IEC 42001 Mapping

| Clause | Requirement | How PostgreSQL Addresses It |
|--------|-------------|------------------------------|
| B.6.2.6.1 | Operation: Infrastructure Monitoring | postgres-exporter sidecar scraped by the edge Prometheus Agent |
| B.6.2.6.3 | Operation: KPI Assessment (OEE) | Prediction history for KPI calculation |
| B.6.2.8.1 | Operation: Logging / Audit Trail | Data changes and connections logged (`log_statement = 'mod'`); model version history |

---

## Prerequisites

- An edge node labelled `node-role.kubernetes.io/edge=true`.
- Secret `edge-postgresql-auth` (keys `postgres-password`, `password`), created by `infrastructure/install.sh`.

---

## Deployment Questionnaire

The Rancher questionnaire is [`manifests/questions.yaml`](./manifests/questions.yaml).

---

## Installation (Helm)

```bash
helm repo add cigip-upv https://cigip-upv.github.io/MLOps-ISO42001-K3s-Catalog
helm install edge-postgresql cigip-upv/edge-postgresql -n edge

kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/chart=edge-postgresql
```

The init script grants privileges to `edge_app`; if `auth.username` changes, adjust the `GRANT` statements in `values.yaml`.

---

## Related Solutions

- [Node-RED](../../data-ingestion/node-red/README.md): writes validated sensor data
- [FastAPI Model Server](../../ai-inference/fastapi-model/README.md): writes predictions
- [Edge Version Control](../../version-control/mlflow-sync/README.md): writes the model version history
- [Edge Data Consolidation](../postgresql-sync/README.md): copies the data to the platform
- [TimescaleDB](../../../platform/data-management/timescaledb/README.md): platform data stock
