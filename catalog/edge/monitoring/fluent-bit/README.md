# Fluent Bit — Edge Log Collector & Forwarder

| Field | Value |
|-------|-------|
| **Tier** | Edge |
| **Category** | Monitoring · Logging |
| **RA Component** | Logger (Edge) |
| **ISO/IEC 42001** | B.6.2.8.1 |
| **Helm Chart** | `fluent/fluent-bit` |
| **K3S Compatible** | Yes |

---

## Description

Fluent Bit is a lightweight, high-performance **log collector and forwarder** deployed as a DaemonSet on edge nodes. In the reference architecture, it implements the **Edge Logger** component, collecting and streaming event logs from all edge workloads to the centralised log aggregation platform (Loki).

Its key roles are:

- **Log collection**: collects container logs from all pods on the edge node, including Node-RED flows, FastAPI inference service, Falco security alerts, and PostgreSQL.
- **Log enrichment**: adds Kubernetes metadata (pod name, namespace, node, tier label) to every log record.
- **Forwarding to Loki**: ships logs to the platform-tier Loki instance for persistent, queryable storage.
- **Audit trail support**: ensures that operational events and incidents are captured and preserved for ISO/IEC 42001 auditability requirements.

---

## ISO/IEC 42001 Mapping

| Clause | Requirement | How Fluent Bit Addresses It |
|--------|-------------|------------------------------|
| B.6.2.8.1 | Event Logs | Automatically captures and forwards all edge workload logs |

---

## Prerequisites

- K3S cluster with at least one edge node
- Loki instance reachable from the edge node (platform tier)
- Network policy allowing outbound traffic from edge namespace to platform Loki port (3100)

---

## Deployment Questionnaire

See [`questionnaire.md`](./questionnaire.md).

---

## Installation (K3S / Helm)

```bash
helm repo add fluent https://fluent.github.io/helm-charts
helm repo update

helm install fluent-bit fluent/fluent-bit \
  --namespace logging \
  --create-namespace \
  -f values.yaml
```

---

## Key Configuration Decisions

| Decision | Options | Recommendation |
|----------|---------|----------------|
| Output destination | Loki / Elasticsearch / stdout | **Loki** — integrates with Grafana for unified observability |
| Log retention at edge | None / file buffer | Enable file-based buffer if connectivity to Loki is intermittent |
| Falco integration | Enabled / Disabled | **Enabled** — forward Falco security events via dedicated pipeline |
| Log level filtering | All / Warning+ / Error+ | Warning+ recommended to reduce volume on constrained nodes |

---

## Related Solutions

- [Loki](../../../platform/monitoring/loki/README.md) — centralised log storage (output destination)
- [Grafana](../../../platform/monitoring/grafana/README.md) — log visualisation and alerting
- [Falco](../../security/falco/README.md) — security events forwarded via Fluent Bit
