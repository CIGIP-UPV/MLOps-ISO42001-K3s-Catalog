# Loki — Centralised Log Aggregation

| Field | Value |
|-------|-------|
| **Tier** | Platform |
| **Category** | Monitoring · Logging |
| **RA Component** | Logger (Platform) |
| **ISO/IEC 42001** | B.6.2.8.1 |
| **Helm Chart** | `grafana/loki-stack` |
| **K3S Compatible** | Yes |

---

## Description

Loki is a **horizontally scalable log aggregation system** that stores and indexes logs from all tiers via Fluent Bit. In the reference architecture, it implements the **Platform Logger** component, providing the centralised event log required for ISO/IEC 42001 auditability.

Its key roles are:

- **Centralised log storage**: receives log streams from Edge (Fluent Bit), Platform (Promtail), and Enterprise workloads.
- **Audit trail**: preserves timestamped, immutable log records of all system events (inference requests, model promotions, access control events, security alerts from Falco).
- **Log querying**: LogQL query language enables compliance officers to extract specific event sequences for audit preparation.
- **Grafana integration**: Loki is natively integrated with Grafana as a data source, enabling unified log and metric correlation.

---

## ISO/IEC 42001 Mapping

| Clause | Requirement | How Loki Addresses It |
|--------|-------------|------------------------|
| B.6.2.8.1 | Event Logs | Central persistent store for all AI system event logs |

---

## Prerequisites

- K3S platform cluster with persistent volumes (minimum 50 GB for 30-day retention)
- Fluent Bit deployed at edge (log forwarding source)
- Grafana deployed (log querying UI)
- S3-compatible storage (MinIO) for long-term log archiving (optional but recommended)

---

## Installation (K3S / Helm)

```bash
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

helm install loki grafana/loki-stack \
  --namespace monitoring \
  -f values.yaml
```

---

## Key Configuration Decisions

| Decision | Options | Recommendation |
|----------|---------|----------------|
| Storage backend | Filesystem / MinIO (S3) | **MinIO** for production — prevents log loss if Loki pod restarts |
| Retention period | 7 / 30 / 90 / 365 days | **90+ days** for ISO/IEC 42001 audit readiness |
| Log ingestion rate | Low (<10 MB/s) / High | Single-instance Loki sufficient for most industrial edge deployments |

---

## Related Solutions

- [Fluent Bit](../../../edge/monitoring/fluent-bit/README.md) — primary log forwarder from edge
- [Grafana](../grafana/README.md) — log query and visualisation UI
- [MinIO](../../data-management/minio/README.md) — long-term log archive backend
