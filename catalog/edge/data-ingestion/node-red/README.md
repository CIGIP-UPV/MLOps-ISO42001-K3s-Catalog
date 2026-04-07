# Node-RED — Edge Data Ingestion & Orchestration

| Field | Value |
|-------|-------|
| **Tier** | Edge |
| **Category** | Data Ingestion · Orchestration |
| **RA Component** | Input Data Monitoring · Data Stock |
| **ISO/IEC 42001** | B.6.2.6.4 · B.6.2.6.7 |
| **Helm Chart** | `node-red/node-red` (community) |
| **K3S Compatible** | Yes |

---

## Description

Node-RED is a flow-based programming tool that serves as the primary **data aggregation, protocol translation, and pre-processing engine** at the Edge tier. In the reference architecture, it sits between the device tier (sensors, PLCs, CNC machines) and the rest of the edge stack.

Its key roles in the reference architecture are:

- **Protocol translation**: converts OPC-UA, MQTT, Modbus, and other industrial protocols into a normalised JSON format.
- **Input data monitoring**: enforces schema validation, value range checks, and signal quality filtering before data reaches the inference engine (addresses model degradation caused by data quality artefacts).
- **Flow orchestration**: triggers downstream actions such as forwarding data to Kafka, writing to PostgreSQL, or calling the FastAPI inference endpoint.
- **Buffering**: when the edge-to-platform connection is unavailable, Node-RED can queue events locally using its file or MongoDB nodes.

---

## ISO/IEC 42001 Mapping

| Clause | Requirement | How Node-RED Addresses It |
|--------|-------------|--------------------------|
| B.6.2.6.4 | Retraining Monitoring | Detects data drift signals at ingress; can trigger notifications to the retraining recommendation engine |
| B.6.2.6.7 | Threat Detection | Schema and range validation acts as a first-line filter against data poisoning attempts |

---

## Prerequisites

- K3S cluster running on edge node (minimum 2 CPU cores, 2 GB RAM recommended)
- Persistent volume available (local-path storage class is sufficient)
- Network access to device tier (OPC-UA/MQTT ports open)
- Optionally: Kafka or MQTT broker for downstream event forwarding

---

## Deployment Questionnaire

See [`questionnaire.md`](./questionnaire.md) for the pre-deployment decision guide.

---

## Installation (K3S / Helm)

```bash
helm repo add node-red https://helm.goffinet.org/node-red
helm repo update

helm install node-red node-red/node-red \
  --namespace edge \
  --create-namespace \
  -f values.yaml
```

A reference `values.yaml` is provided in [`manifests/`](./manifests/).

---

## Key Configuration Decisions

| Decision | Options | Recommendation |
|----------|---------|----------------|
| Persistence | Enabled / Disabled | **Enabled** — required for buffering during connectivity loss |
| Authentication | None / Basic Auth | **Basic Auth minimum** — required by B.6.1.3.1 |
| Protocol nodes | MQTT, OPC-UA, Modbus | Select based on device tier protocols in use |
| Upstream sink | Kafka / Direct HTTP | Kafka preferred for decoupling and replay capability |

---

## Related Solutions

- [Kafka](../kafka/README.md) — downstream event streaming
- [Mosquitto](../mosquitto/README.md) — MQTT broker for device-tier devices
- [PostgreSQL](../../storage/postgresql/README.md) — local buffering and feature persistence
- [FastAPI Model Server](../../ai-inference/fastapi-model/README.md) — inference endpoint called by Node-RED flows
