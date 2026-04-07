# MLflow — AI Lifecycle & Version Control

| Field | Value |
|-------|-------|
| **Tier** | Platform |
| **Category** | AI Lifecycle |
| **RA Component** | Version Control · Retraining Recommendation |
| **ISO/IEC 42001** | B.6.1.3.2 · B.6.1.3.4 · B.6.2.6.4 |
| **Helm Chart** | `community-charts/mlflow` |
| **K3S Compatible** | Yes |

---

## Description

MLflow is the **AI lifecycle management** platform implementing the **Version Control** and **Retraining Recommendation** components in the reference architecture. It provides end-to-end tracking of experiments, model versions, and deployment states.

Its key roles in the reference architecture are:

- **Experiment tracking**: logs training runs (hyperparameters, metrics, artefacts) for reproducibility and comparison, satisfying the documentation requirements of ISO/IEC 42001.
- **Model registry**: manages the lifecycle of model versions (Staging → Production → Archived), implementing the release criteria gate (B.6.1.3.4) before any model is promoted to the edge inference service.
- **Artefact store**: stores model files, training notebooks, and evaluation reports in MinIO (S3-compatible), creating a governed audit trail.
- **Retraining trigger integration**: scheduled Python jobs evaluate drift metrics and log new training runs; MLflow tracks their outcomes and supports the retraining recommendation decision.

---

## ISO/IEC 42001 Mapping

| Clause | Requirement | How MLflow Addresses It |
|--------|-------------|--------------------------|
| B.6.1.3.2 | Version Control | Full model and artefact versioning with stage transitions |
| B.6.1.3.4 | Release Criteria | Model registry staging gates; requires approval before Production promotion |
| B.6.2.6.4 | Retraining Monitoring | Tracks drift-triggered retraining runs; links performance metrics to model versions |

---

## Prerequisites

- K3S cluster (platform tier) with at least 2 CPU cores, 4 GB RAM
- MinIO deployed and accessible (artefact storage backend)
- PostgreSQL deployed (MLflow metadata backend)
- S3-compatible endpoint configured (MinIO)

---

## Deployment Questionnaire

See [`questionnaire.md`](./questionnaire.md).

---

## Installation (K3S / Helm)

```bash
helm repo add community-charts https://community-charts.github.io/helm-charts
helm repo update

helm install mlflow community-charts/mlflow \
  --namespace mlops \
  --create-namespace \
  -f values.yaml
```

---

## Key Configuration Decisions

| Decision | Options | Recommendation |
|----------|---------|----------------|
| Artefact backend | Local filesystem / MinIO / S3 | **MinIO** — S3-compatible, runs on-premises |
| Metadata backend | SQLite / PostgreSQL | **PostgreSQL** — required for multi-user production use |
| Authentication | None / Basic | Basic auth minimum; integrate with Keycloak via OIDC proxy for enterprise |
| Model approval workflow | Automatic / Manual | **Manual** — approval by data scientist + compliance officer (B.6.1.3.4) |
| Ingress | Traefik (K3S default) | Expose on internal subdomain; do not expose externally without authentication |

---

## Model Promotion Workflow

```
Training Job → MLflow Experiment (Staging)
     ↓
Performance Evaluation (metrics threshold check)
     ↓
Manual Approval (data scientist + compliance officer)
     ↓
MLflow Registry: Staging → Production
     ↓
Edge Version Control: pull new model artefact → redeploy FastAPI service
```

This workflow implements B.6.1.3.4 (Release Criteria) and provides a documented, auditable chain from training to deployment.

---

## Related Solutions

- [Training Jobs](../training-jobs/README.md) — produces model runs logged in MLflow
- [MinIO](../../data-management/minio/README.md) — artefact storage backend
- [FastAPI Model Server](../../../edge/ai-inference/fastapi-model/README.md) — consumes promoted model versions
- [Keycloak](../../../enterprise/access-management/keycloak/README.md) — authentication for MLflow UI
