# PostgreSQL — Edge Feature Cache & Prediction Store

| Field | Value |
|-------|-------|
| **Tier** | Edge |
| **Category** | Storage |
| **RA Component** | Data Stock (Edge) |
| **ISO/IEC 42001** | B.6.2.6.1 · B.6.2.6.3 · B.6.2.8.1 |
| **Helm Chart** | `bitnami/postgresql` |
| **K3S Compatible** | Yes |

---

## Description

PostgreSQL serves as the **local persistent storage** at the edge tier, implementing the **Data Stock** component. It stores recent sensor features, inference results, and operational metadata with low latency, independent of platform connectivity.

Its key roles are:

- **Feature cache**: stores preprocessed sensor windows for the LSTM inference service, enabling replay and retraining sample collection.
- **Prediction store**: persists inference outputs (timestamp, input hash, prediction score, model version) for audit and feedback purposes.
- **Operational buffer**: during connectivity outages, acts as a durable queue before data is synced to the platform-tier TimescaleDB.
- **Event metadata**: stores structured operational events that Fluent Bit cannot capture (e.g., operator acknowledgements, manual overrides).

---

## ISO/IEC 42001 Mapping

| Clause | Requirement | How PostgreSQL Addresses It |
|--------|-------------|------------------------------|
| B.6.2.6.1 | Error Monitoring | Stores error events and system state snapshots |
| B.6.2.6.3 | Goal-oriented Performance Monitoring | Persists prediction history for KPI calculation |
| B.6.2.8.1 | Event Logs | Durable storage of structured operational events |

---

## Prerequisites

- K3S cluster with local-path storage class (default in K3S)
- Persistent volume with at least 10 GB available
- Network access from Node-RED and FastAPI model server pods

---

## Deployment Questionnaire

See [`questionnaire.md`](./questionnaire.md).

---

## Installation (K3S / Helm)

```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

helm install postgresql bitnami/postgresql \
  --namespace edge \
  -f values.yaml
```

---

## Related Solutions

- [Node-RED](../../data-ingestion/node-red/README.md) — writes buffered sensor data
- [FastAPI Model Server](../../ai-inference/fastapi-model/README.md) — writes prediction logs
- [TimescaleDB](../../../platform/data-management/timescaledb/README.md) — platform-tier sync target
- [Fluent Bit](../../monitoring/fluent-bit/README.md) — forwards PostgreSQL logs to Loki
