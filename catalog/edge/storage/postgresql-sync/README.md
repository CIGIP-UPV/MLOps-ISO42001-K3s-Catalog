# Edge Data Consolidation: `edge-postgresql-sync`

> Incremental, watermark-based consolidation of the edge data stock into the platform data stock, with a batch log for data provenance.

[![Tier](https://img.shields.io/badge/tier-edge-065f46)](#) [![ISO/IEC 42001](https://img.shields.io/badge/ISO%2FIEC-42001-991b1b)](#) [![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Part of the [K3s Solution Catalog for ISO/IEC 42001](https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog).

---

## Overview

- **Tier**: `edge`
- **Category**: `Storage`
- **Namespace**: `edge`
- **Reference architecture component**: `CMP-02` Data Stock, *data consolidation* flow (Data Stock edge to Data Stock platform)
- **ISO/IEC 42001 Annex B clauses covered**: `B.6.2.6.1`, `B.6.2.8.1`

The reference architecture places a **Data Stock** at both the edge and the platform level and adds a *data consolidation* flow between them: the data captured and buffered at the plant floor must reach the platform, where models are trained and KPIs are computed. Before this chart, the catalog shipped both data stocks (`edge-postgresql` and `platform-timescaledb`) but nothing moved data from one to the other.

This chart closes that gap with a **CronJob** that runs in the edge namespace and **pushes** new rows to the platform (the edge initiates the connection, which matches the edge egress NetworkPolicy and works behind NAT). Each run:

1. reads the **watermark** of the site: the highest edge row id of the last successful batch, stored on the platform;
2. opens a batch in `consolidation_batches` (`status = running`);
3. streams the new rows with `COPY ... TO STDOUT` from the edge and `\copy ... FROM pstdin` into the platform, without temporary files;
4. inserts them **idempotently** (`ON CONFLICT DO NOTHING` on site, source id and time), so a retried batch never duplicates rows;
5. closes the batch with the rows read and written (`status = ok`), or marks it `failed`.

Every batch also prints one JSON line to stdout, which Fluent Bit ships to Loki. Together, the `consolidation_batches` table and the logs give a complete **provenance record**: which edge rows reached the platform, when and in which batch.

The chart has no upstream dependency and uses the official `postgres:16-alpine` image (only `psql` is needed).

---

## Prerequisites

- `edge-postgresql` in the `edge` namespace (source; tables `sensor_features` and `predictions`).
- `platform-timescaledb` in the `platform` namespace (target; tables `sensor_readings`, `predictions` and `consolidation_batches`, role `sync`).
- Two Secrets in the `edge` namespace, created by `infrastructure/install.sh`:
  - `edge-postgresql-auth` (key `password`, user `edge_app`);
  - `edge-postgresql-sync-target` (key `password`, a copy of the `sync-password` of `platform-timescaledb-auth`).
- The edge NetworkPolicy must allow egress to the platform namespace on TCP 5432 (it does in `infrastructure/01-network-policies.yaml`).

---

## Quick start

```bash
helm repo add cigip-upv https://cigip-upv.github.io/MLOps-ISO42001-K3s-Catalog
helm repo update

helm install edge-postgresql-sync cigip-upv/edge-postgresql-sync \
  --namespace edge \
  --set siteId=plant-a-line-1
```

Run a batch immediately instead of waiting for the schedule:

```bash
kubectl -n edge create job --from=cronjob/edge-postgresql-sync sync-now
kubectl -n edge logs job/sync-now
```

Check the provenance log on the platform:

```sql
SELECT id, site_id, source_table, from_id, to_id, rows_read, rows_written, status, finished_at
  FROM consolidation_batches ORDER BY id DESC LIMIT 10;
```

---

## Configuration

The default values are defined in [`values.yaml`](./manifests/values.yaml);
the Rancher questionnaire lives in [`questions.yaml`](./manifests/questions.yaml).

| Area | Variable | Default | Notes |
|------|----------|---------|-------|
| Site | `siteId` | `edge-site-01` | Stored in every consolidated row |
| Schedule | `schedule` | `*/5 * * * *` | `concurrencyPolicy: Forbid`: batches never overlap |
| Volume | `batchSize` | `50000` | Rows per table and run; the backlog is drained over successive runs |
| Tables | `tables.sensorFeatures`, `tables.predictions` | `true`, `true` | Tables copied in each run |
| Source | `source.*` | `edge-postgresql.edge` | Edge data stock |
| Target | `target.*` | `platform-timescaledb.platform` | Platform data stock, role `sync` |

---

## Key design decisions

- **Push from the edge, not pull from the platform.** Edge sites often sit behind NAT or a firewall; the edge opens the connection, and the platform does not need network access into the edge namespace.
- **Watermark on the platform.** The edge stays stateless: if the CronJob or its node is replaced, the next run resumes from the last successful batch.
- **Idempotent inserts.** A batch that fails half-way is retried in full; the unique key (site, source id, time) discards rows already present.
- **Least privilege.** The `sync` role can only insert into the consolidated tables and write the batch log.

---

## ISO/IEC 42001 traceability

| Clause | Requirement |
|--------|-------------|
| `B.6.2.6.1` | Operation: Infrastructure Monitoring (every batch is recorded with its status and row counts) |
| `B.6.2.8.1` | Operation: Logging / Audit Trail (batch log and JSON log lines give the provenance of consolidated data) |

Every resource carries the label `iso42001: "true"` and one label per clause:

```bash
kubectl get cronjob,job,pod -n edge -l mlops-iso42001.cigip-upv.es/chart=edge-postgresql-sync
```

The mapping is maintained at the catalog level in the root [`README.md`](https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog#isoiec-42001-coverage-summary).

---

## Maintainer

- **CIGIP-UPV**, *https://cigip.webs.upv.es/*, `cigip@upv.es`

Released under the Apache 2.0 License.
