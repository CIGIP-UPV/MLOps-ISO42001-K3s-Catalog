# MinIO — S3-Compatible Object Storage

| Field | Value |
|-------|-------|
| **Tier** | Platform · Enterprise |
| **Category** | Storage · Data Management |
| **RA Component** | Data Stock (Platform) · Document Store |
| **ISO/IEC 42001** | B.6.2.3.1 · B.6.2.5.1 · B.6.2.6.5 · B.6.2.8.1 |
| **Helm Chart** | `minio/minio` |
| **K3S Compatible** | Yes |

---

## Description

MinIO is a **high-performance, S3-compatible object storage system** that serves two roles in the reference architecture:

1. **Platform Data Lake**: stores raw and processed datasets, model artefacts (MLflow backend), and training data for the AI lifecycle.
2. **Document Store**: provides governed, versioned storage for ISO/IEC 42001-required documents (system architecture documentation, deployment plans, update/repair plans, audit reports).

Its key capabilities in the reference architecture are:

- **MLflow artefact backend**: stores model files, evaluation notebooks, and training artefacts under a `mlflow-artifacts` bucket.
- **Dataset catalogue backend**: stores structured datasets available for model training under a `datasets` bucket.
- **Document Store**: an `iso42001-docs` bucket holds compliance documents with versioning enabled, providing an immutable audit trail.
- **Log archive**: an `audit-logs` bucket archives Loki log exports for long-term retention.
- **Model artefact registry**: serves model files to the edge tier when connectivity allows.

---

## ISO/IEC 42001 Mapping

| Clause | Requirement | How MinIO Addresses It |
|--------|-------------|------------------------|
| B.6.2.3.1 | Architecture Documentation | `iso42001-docs` bucket stores system architecture documents |
| B.6.2.5.1 | Deployment Plan | Deployment plan documents stored with versioning |
| B.6.2.6.5 | Update & Repair Plan | Maintenance and repair procedures stored and versioned |
| B.6.2.8.1 | Event Logs | Long-term archive of audit log exports |

---

## Recommended Bucket Structure

| Bucket | Contents | Versioning |
|--------|----------|------------|
| `mlflow-artifacts` | Model files, evaluation artefacts | Enabled |
| `datasets` | Training and validation datasets | Enabled |
| `iso42001-docs` | Compliance documentation | Enabled (immutable) |
| `audit-logs` | Long-term log archives | Enabled |
| `model-registry` | Promoted edge model artefacts | Enabled |

---

## Prerequisites

- K3S cluster with persistent volumes (minimum 100 GB recommended for production)
- TLS certificate for HTTPS access (recommended via cert-manager)
- Keycloak integration for access control (enterprise tier)

---

## Deployment Questionnaire

See [`questionnaire.md`](./questionnaire.md).

---

## Installation (K3S / Helm)

```bash
helm repo add minio https://charts.min.io/
helm repo update

helm install minio minio/minio \
  --namespace minio \
  --create-namespace \
  -f values.yaml
```

---

## Related Solutions

- [MLflow](../../ai-lifecycle/mlflow/README.md) — uses MinIO as artefact backend
- [Loki](../loki/README.md) — uses MinIO for long-term log storage
- [Keycloak](../../../enterprise/access-management/keycloak/README.md) — access control for MinIO
- [TimescaleDB](../timescaledb/README.md) — complementary time-series storage
