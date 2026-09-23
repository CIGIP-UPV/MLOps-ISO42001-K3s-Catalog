# Loki: Centralised Log Aggregation

| Field | Value |
|-------|-------|
| **Chart** | `platform-loki` |
| **Tier** | Platform |
| **Namespace** | `monitoring` |
| **Category** | Monitoring · Logging |
| **RA Component** | Logger (CMP-09: platform aggregation, and the enterprise-level log archive in MinIO) |
| **ISO/IEC 42001** | B.6.2.8.1 |
| **Helm Chart** | `grafana/loki` 6.x (Loki 3.6, single binary, wrapped) |
| **K3S Compatible** | Yes |

---

## Description

Loki is the **log aggregation system** of the platform and the store of the catalog's audit trail. It receives:

- container logs of every node and the Kubernetes API audit log, from [`edge-fluent-bit`](../../../edge/monitoring/fluent-bit/README.md);
- Falco security events, from Falcosidekick ([`edge-falco`](../../../edge/security/falco/README.md));
- the JSON event lines of the MLOps jobs (version sync, consolidation, training, drift check), through Fluent Bit.

Chunks and index are stored in the `loki-logs` bucket of `platform-minio` (user `loki`), not on the Loki pod's disk: the audit trail survives the loss of the pod or its node. Retention is 90 days (`retention_period: 2160h`, compactor retention enabled). The local volume only holds the WAL and caches.

To keep the footprint small, the nginx gateway, the memcached caches, the canary and the rules sidecar are disabled; clients use the service `platform-loki.monitoring:3100` directly.

---

## ISO/IEC 42001 Mapping

| Clause | Requirement | How Loki Addresses It |
|--------|-------------|------------------------|
| B.6.2.8.1 | Operation: Logging / Audit Trail | Central store of the AI system event logs, archived in object storage |

---

## Prerequisites

- `platform-minio` with the bucket `loki-logs`.
- Secret `platform-loki-s3` (keys `LOKI_S3_ACCESS_KEY`, `LOKI_S3_SECRET_KEY`), created by `infrastructure/install.sh`.

---

## Deployment Questionnaire

The Rancher questionnaire is [`manifests/questions.yaml`](./manifests/questions.yaml).

---

## Installation (Helm)

```bash
helm repo add cigip-upv https://cigip-upv.github.io/MLOps-ISO42001-K3s-Catalog
helm install platform-loki cigip-upv/platform-loki -n monitoring

kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/chart=platform-loki
```

---

## Key Configuration Decisions

| Decision | Options | Choice in this chart |
|----------|---------|----------------------|
| Storage backend | Filesystem / MinIO (S3) | **MinIO**: logs survive pod and node loss |
| Retention period | 7 / 30 / 90 / 365 days | **90 days** for ISO/IEC 42001 audit readiness |
| Deployment mode | Single binary / simple scalable / distributed | **Single binary**: enough for an industrial site |
| Gateway and caches | Enabled / disabled | **Disabled** at this scale |

---

## Related Solutions

- [Fluent Bit](../../../edge/monitoring/fluent-bit/README.md): log forwarder
- [Grafana](../grafana/README.md): log query and visualisation
- [MinIO](../../data-management/minio/README.md): log archive backend
