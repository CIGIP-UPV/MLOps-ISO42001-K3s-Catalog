# MinIO: S3-Compatible Object Storage

| Field | Value |
|-------|-------|
| **Chart** | `platform-minio` |
| **Tier** | Platform |
| **Namespace** | `minio` |
| **Category** | Storage · Data Management |
| **RA Components** | Data Stock (CMP-02, platform); storage backend of the Document Store (CMP-05) |
| **ISO/IEC 42001** | B.6.2.3.1 · B.6.2.5.1 |
| **Helm Chart** | `minio/minio` (wrapped), images from `quay.io/minio` |
| **K3S Compatible** | Yes |

---

## Description

MinIO is an **S3-compatible object storage system** (standalone mode, one volume) that serves the platform and, through the enterprise overlay, the document store.

Platform buckets created by this chart:

| Bucket | Contents | Versioning | Used by |
|--------|----------|------------|---------|
| `mlflow-artifacts` | Model files, reference data, drift reports | Enabled | `platform-mlflow` (proxied artefacts) |
| `datasets` | Curated training and validation datasets (Dataset Catalogue) | Enabled | operators and data scientists |
| `loki-logs` | Loki chunks and index: long-term log archive | Disabled | `platform-loki` |

The document store buckets (`iso42001-docs`, `model-cards`, `audit-evidence`, with object locking and retention) are created in this same MinIO by [`enterprise-minio-overlay`](../../../enterprise/document-store/minio/README.md). The buckets `model-registry` and `audit-logs` of earlier versions were removed: nothing used them.

Access: least-privilege service users `mlflow` (read and write on `mlflow-artifacts`) and `loki` (read and write on `loki-logs`). The upstream chart's default `console` user (fixed password, `consoleAdmin`) is replaced by this list. Root credentials come from a Secret; no password is written in the chart.

---

## ISO/IEC 42001 Mapping

| Clause | Requirement | How MinIO Addresses It |
|--------|-------------|------------------------|
| B.6.2.3.1 | Planning: System Documentation | Versioned storage of artefacts and documentation (with the enterprise overlay) |
| B.6.2.5.1 | Planning: Deployment Plan | Storage backend of the deployment plan documents and model artefacts |

---

## Prerequisites

- Secrets `platform-minio-root` (keys `rootUser`, `rootPassword`) and `platform-minio-users` (keys `mlflow`, `loki`), created by `infrastructure/install.sh`.
- `platform-prometheus` first (the chart ships a ServiceMonitor; metrics are public inside the cluster).

---

## Deployment Questionnaire

The Rancher questionnaire is [`manifests/questions.yaml`](./manifests/questions.yaml).

---

## Installation (Helm)

```bash
helm repo add cigip-upv https://cigip-upv.github.io/MLOps-ISO42001-K3s-Catalog
helm install platform-minio cigip-upv/platform-minio -n minio

kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/chart=platform-minio
```

The bucket, policy and user provisioning runs in a post-install hook Job of the upstream chart; Helm does not pass hooks through the post-renderer, so that Job carries no iso42001 labels.

---

## Related Solutions

- [MLflow](../../ai-lifecycle/mlflow/README.md): artefact backend
- [Loki](../../monitoring/loki/README.md): log archive
- [MinIO Docs Overlay](../../../enterprise/document-store/minio/README.md): document store buckets
- [TimescaleDB](../timescaledb/README.md): complementary time-series storage
