# Node-RED: Edge Input Data Monitoring and Ingestion

| Field | Value |
|-------|-------|
| **Chart** | `edge-node-red` |
| **Tier** | Edge |
| **Namespace** | `edge` |
| **Category** | Data Ingestion |
| **RA Component** | Input Data Monitoring (CMP-01) |
| **ISO/IEC 42001** | B.6.2.6.4 |
| **Helm Chart** | `schwarzit/node-red` 0.30.0 (Node-RED 3.1.3), wrapped |
| **K3S Compatible** | Yes |

---

## Description

Node-RED is the **Input Data Monitoring** component at the edge: it sits between the industrial protocol gateway and the edge data stock and decides which samples are fit to feed the models.

The chart ships a declarative ingestion flow ([`manifests/files/flows.json`](./manifests/files/flows.json)), versioned in git and copied into Node-RED at every start, so the running flow is always the one in the repository:

1. **Subscribe** to the OPC UA samples published by [`edge-opc-ua-gateway`](../opc-ua-gateway/README.md) on `plant/+/opcua` (authenticated MQTT user `nodered`).
2. **Validate** each sample: OPC UA quality must be *Good*, every value numeric, finite and within `INPUT_MAX_ABS`, and the timestamp plausible (not in the future, not older than `INPUT_MAX_AGE_S`).
3. **Write** the valid values to the `sensor_features` table of the edge data stock (`edge-postgresql`) in a single `unnest` insert per sample.
4. **Reject** invalid samples to `plant/<machine_id>/rejected` and log them as JSON (Fluent Bit and Loki).
5. **Expose** the monitoring counters on `GET /metrics` for the edge Prometheus Agent: `ingest_messages_valid_total`, `ingest_values_written_total`, `ingest_messages_rejected_total{reason}`, `ingest_db_errors_total` and `ingest_last_sample_timestamp_seconds`.

An init container prepares `/data`: it installs the pinned `node-red-contrib-postgresql@0.16.2` node, copies the flow, writes the MQTT credentials from the `edge-mosquitto-users` Secret and, if the `edge-node-red-admin` Secret exists, the bcrypt hash of the editor password. Database credentials reach the flow as environment variables from `edge-postgresql-auth`; no secret is written in the flow.

---

## ISO/IEC 42001 Mapping

| Clause | Requirement | How Node-RED addresses it |
|--------|-------------|---------------------------|
| B.6.2.6.4 | Operation: Retraining / Lifecycle | Only validated plant data reaches the data stock used for training; rejections are counted and logged |

---

## Prerequisites

- `edge-mosquitto` and `edge-opc-ua-gateway` (source of the samples).
- `edge-postgresql` (target) and the Secrets `edge-postgresql-auth` and `edge-mosquitto-users`.
- Egress from the Node-RED pod to the npm registry the first time the init container runs (allowed by the edge NetworkPolicy); mirror the registry for air-gapped sites.

---

## Deployment Questionnaire

The Rancher questionnaire is [`manifests/questions.yaml`](./manifests/questions.yaml).

---

## Installation (Helm)

```bash
helm repo add cigip-upv https://cigip-upv.github.io/MLOps-ISO42001-K3s-Catalog
helm install edge-node-red cigip-upv/edge-node-red -n edge

kubectl -n edge port-forward svc/edge-node-red 1880:1880
curl localhost:1880/metrics
```

The editor is at `http://localhost:1880/admin/` and asks for the password of the `edge-node-red-admin` Secret. Changes made in the editor are replaced by the flow of the chart at the next restart: change `files/flows.json` instead.

---

## Key Configuration Decisions

| Decision | Options | Choice in this chart |
|----------|---------|----------------------|
| Flow management | Editor / Node-RED projects / declarative file | **Declarative file in git**, copied at start-up |
| Validation | In the gateway / in Node-RED / in the model | **Node-RED**: rules are visible and editable as a flow, and every rejection is counted |
| Database access | Contrib node / HTTP to a service | `node-red-contrib-postgresql`, pinned version, credentials from environment variables |
| Editor exposure | Ingress / port-forward | **Port-forward** by default; the Ingress requires TLS and the admin Secret |

---

## Related Solutions

- [OPC-UA Gateway](../opc-ua-gateway/README.md): publishes the samples
- [Mosquitto](../mosquitto/README.md): MQTT broker
- [PostgreSQL (edge)](../../storage/postgresql/README.md): edge data stock
- [Prometheus Agent](../../monitoring/prometheus-agent/README.md): scrapes `/metrics`
