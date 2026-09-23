# TimescaleDB: Platform Time-Series Data Stock

| Field | Value |
|-------|-------|
| **Chart** | `platform-timescaledb` |
| **Tier** | Platform |
| **Namespace** | `platform` |
| **Category** | Data Management |
| **RA Components** | Data Stock (CMP-02, platform); Goal-Oriented Monitoring (CMP-11) |
| **ISO/IEC 42001** | B.6.2.6.1 · B.6.2.6.3 |
| **Deployment** | Own templates (StatefulSet), image `timescale/timescaledb:2.17.2-pg16` |
| **K3S Compatible** | Yes |

---

## Description

TimescaleDB is a **time-series optimised relational database** (PostgreSQL 16) serving as the **platform Data Stock**: the target of the data consolidation flow from the edge, the source of the training data and the store of goal-oriented KPIs.

Earlier versions wrapped `timescale/timescaledb-single ~0.35`, a version that does not exist; the last release of that deprecated chart (0.33.1) rejects the catalog values. The chart now renders its own StatefulSet with the official image, a `postgres-exporter` sidecar (`quay.io/prometheuscommunity/postgres-exporter`) and a ServiceMonitor when the Prometheus Operator CRDs exist.

Schema of the database `zdm_platform`, created on first start:

| Table | Type | Written by |
|-------|------|------------|
| `sensor_readings` | hypertable, unique (site, source id, time) | `edge-postgresql-sync` |
| `predictions` | hypertable, unique (site, source id, time) | `edge-postgresql-sync` |
| `oee_kpis` | hypertable | plant systems (OEE source) |
| `consolidation_batches` | table | `edge-postgresql-sync` (provenance of every batch) |
| `retraining_recommendations` | table | `platform-evidently` (drift check) |

Least-privilege roles: `sync` (insert consolidated data and the batch log), `ml` (read training data, write recommendations; used by training jobs and Evidently) and `grafana` (read only).

---

## ISO/IEC 42001 Mapping

| Clause | Requirement | How TimescaleDB Addresses It |
|--------|-------------|------------------------------|
| B.6.2.6.1 | Operation: Infrastructure Monitoring | Exporter metrics; consolidation batch log |
| B.6.2.6.3 | Operation: KPI Assessment (OEE) | Long-term KPI data for the Grafana business dashboards |

---

## Prerequisites

- Secret `platform-timescaledb-auth` (keys `postgres-password`, `sync-password`, `ml-password`, `grafana-password`), created by `infrastructure/install.sh`.

---

## Deployment Questionnaire

The Rancher questionnaire is [`manifests/questions.yaml`](./manifests/questions.yaml).

---

## Installation (Helm)

```bash
helm repo add cigip-upv https://cigip-upv.github.io/MLOps-ISO42001-K3s-Catalog
helm install platform-timescaledb cigip-upv/platform-timescaledb -n platform

kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/chart=platform-timescaledb
```

The init script runs only on the first start of an empty volume.

---

## Related Solutions

- [Edge Data Consolidation](../../../edge/storage/postgresql-sync/README.md): writes consolidated edge data
- [Training Jobs](../../ai-lifecycle/training-jobs/README.md): reads the training windows
- [Evidently](../../ai-lifecycle/evidently/README.md): reads recent data, writes recommendations
- [Grafana](../../monitoring/grafana/README.md): dashboards querying TimescaleDB
