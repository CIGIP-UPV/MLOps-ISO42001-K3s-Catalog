# FastAPI Model Server — Edge AI Inference

| Field | Value |
|-------|-------|
| **Tier** | Edge |
| **Category** | AI Inference |
| **RA Component** | Edge AI Model |
| **ISO/IEC 42001** | B.6.1.2.2 · B.6.1.3.4 · B.6.2.6.1 |
| **Deployment** | Custom container (no public Helm chart — provided as K3S manifest) |
| **K3S Compatible** | Yes |

---

## Description

The FastAPI Model Server is the **Edge AI Model** component — a containerised Python service that exposes an AI model (e.g., LSTM, Random Forest, anomaly detector) as a REST API for **low-latency inference** close to the data source.

In the reference architecture, the edge inference service provides:

- **Real-time predictions** from time-series sensor data (e.g., vibration, temperature, energy consumption) without round-trip latency to the platform.
- **Prediction logging**: every inference request and response is logged to PostgreSQL and forwarded to Fluent Bit, supporting the audit trail required by B.6.2.8.1.
- **Health and readiness endpoints**: expose `/health` and `/ready` endpoints consumed by Prometheus Agent for infrastructure monitoring.
- **Version endpoint**: exposes the deployed model version, linked to the version control component (MLflow) for traceability (B.6.1.3.2).

The edge model is a **lightweight variant** of the platform model — same architecture, potentially quantised or pruned for constrained hardware. Model artefacts are promoted from the platform tier via the Version Control mechanism (MLflow model registry).

---

## ISO/IEC 42001 Mapping

| Clause | Requirement | How FastAPI Model Server Addresses It |
|--------|-------------|---------------------------------------|
| B.6.1.2.2 | Integration of Metrics | Exposes `/metrics` endpoint for Prometheus scraping |
| B.6.1.3.4 | Release Criteria | Version endpoint linked to MLflow registry; only promoted models are served |
| B.6.2.6.1 | Error Monitoring | Health endpoint; structured error logging per request |

---

## Prerequisites

- Container image with your model artefact baked in (or mounted via PVC from MinIO)
- K3S cluster with GPU support (optional — for GPU-accelerated inference)
- PostgreSQL deployed for prediction logging
- Prometheus Agent deployed for metrics scraping
- Access to MLflow registry on the platform tier (for model version metadata)

---

## Deployment Questionnaire

See [`questionnaire.md`](./questionnaire.md).

---

## Installation (K3S Manifest)

```bash
kubectl apply -f manifests/fastapi-deployment.yaml
kubectl apply -f manifests/fastapi-service.yaml
```

Edit `manifests/fastapi-deployment.yaml` to set your container image, resource limits, and environment variables.

---

## Key Configuration Decisions

| Decision | Options | Recommendation |
|----------|---------|----------------|
| Model loading | Baked into image / mounted PVC / remote pull | **Mounted PVC** — simplifies model updates without image rebuilds |
| GPU | Enabled / Disabled | Enable only if edge node has GPU; most edge scenarios use CPU |
| Replicas | 1 / 2+ | 1 for constrained edge; 2 for high-availability setups |
| Inference timeout | 100ms / 500ms / custom | Set based on process latency requirements (e.g., 500ms for stamping press) |

---

## Related Solutions

- [Node-RED](../../data-ingestion/node-red/README.md) — calls this endpoint with preprocessed sensor data
- [PostgreSQL](../../storage/postgresql/README.md) — prediction cache and feature store
- [Prometheus Agent](../../monitoring/prometheus-agent/README.md) — scrapes `/metrics` endpoint
- [MLflow](../../../platform/ai-lifecycle/mlflow/README.md) — source of model artefacts and version metadata
