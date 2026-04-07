# TimescaleDB — Time-Series Data Warehouse

| Field | Value |
|-------|-------|
| **Tier** | Platform |
| **Category** | Data Management |
| **RA Component** | Data Stock (Platform) |
| **ISO/IEC 42001** | B.6.2.6.3 · B.6.2.8.1 |
| **Helm Chart** | `timescale/timescaledb-single` |
| **K3S Compatible** | Yes |

---

## Description

TimescaleDB is a **time-series optimised relational database** (built on PostgreSQL) serving as the long-term **data warehouse** at the platform tier. It is designed for high-volume sensor data, prediction histories, and operational KPIs that require both SQL querying and time-series analytics.

Its key roles in the reference architecture are:

- **Long-horizon analytics**: stores months or years of sensor readings, inference results, and KPI snapshots for trend analysis and model retraining.
- **KPI persistence**: Goal-oriented performance metrics (OEE, availability, downtime hours) are stored and queried by Grafana dashboards.
- **Training data source**: the retraining recommendation engine queries TimescaleDB for training data windows based on date ranges and equipment identifiers.
- **Data sync target**: edge PostgreSQL data is periodically synced to TimescaleDB (batch or streaming via Kafka).

---

## ISO/IEC 42001 Mapping

| Clause | Requirement | How TimescaleDB Addresses It |
|--------|-------------|------------------------------|
| B.6.2.6.3 | Goal-oriented Performance Monitoring | Persists long-term KPI data for Grafana business dashboards |
| B.6.2.8.1 | Event Logs | Structured time-series event storage for audit queries |

---

## Prerequisites

- K3S platform cluster with persistent volumes (minimum 50 GB; scale based on data volume)
- PostgreSQL client tools for schema management
- Grafana deployed (primary data consumer for dashboards)

---

## Installation (K3S / Helm)

```bash
helm repo add timescale https://charts.timescale.com
helm repo update

helm install timescaledb timescale/timescaledb-single \
  --namespace platform \
  -f values.yaml
```

---

## Key Tables (Reference Schema)

```sql
-- Sensor readings (compressed after 7 days)
CREATE TABLE sensor_readings (
  time        TIMESTAMPTZ NOT NULL,
  machine_id  TEXT NOT NULL,
  signal_name TEXT NOT NULL,
  value       DOUBLE PRECISION
);
SELECT create_hypertable('sensor_readings', 'time');

-- Model predictions
CREATE TABLE predictions (
  time         TIMESTAMPTZ NOT NULL,
  machine_id   TEXT NOT NULL,
  model_version TEXT NOT NULL,
  score        DOUBLE PRECISION,
  label        TEXT,         -- operator feedback (correct/incorrect)
  acknowledged BOOLEAN DEFAULT FALSE
);
SELECT create_hypertable('predictions', 'time');

-- OEE KPIs
CREATE TABLE oee_kpis (
  time        TIMESTAMPTZ NOT NULL,
  machine_id  TEXT NOT NULL,
  oee         DOUBLE PRECISION,
  availability DOUBLE PRECISION,
  performance  DOUBLE PRECISION,
  quality      DOUBLE PRECISION
);
SELECT create_hypertable('oee_kpis', 'time');
```

---

## Related Solutions

- [Grafana](../../monitoring/grafana/README.md) — dashboards querying TimescaleDB
- [PostgreSQL Edge](../../../edge/storage/postgresql/README.md) — edge data source synced here
- [Training Jobs](../../ai-lifecycle/training-jobs/README.md) — queries TimescaleDB for training datasets
- [MinIO](../minio/README.md) — complementary document and artefact storage
