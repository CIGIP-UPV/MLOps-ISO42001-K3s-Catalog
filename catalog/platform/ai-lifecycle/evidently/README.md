# Evidently AI: `platform-evidently`

> Drift monitoring UI plus a scheduled drift check that records a retraining recommendation and, above the threshold, launches the retraining job.

[![Tier](https://img.shields.io/badge/tier-platform-1e40af)](#) [![ISO/IEC 42001](https://img.shields.io/badge/ISO%2FIEC-42001-991b1b)](#) [![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Part of the [K3s Solution Catalog for ISO/IEC 42001](https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog).

---

## Overview

- **Tier**: `platform`
- **Category**: `AI Lifecycle`
- **Namespace**: `mlops`
- **Reference architecture components**: `CMP-10` Model Technical Performance Monitoring (data drift), `CMP-14` Retraining Recommendation
- **ISO/IEC 42001 Annex B clauses covered**: `B.6.2.6.2`, `B.6.2.8.1`, `B.8.0.5.1`

The chart has two parts:

1. **Evidently UI** (`evidently ui`, image `evidently/evidently-service:0.4.33`): a workspace, on a persistent volume, that keeps every drift report so engineers can browse the history per model.
2. **Drift check** (CronJob, every 30 minutes by default), the **Retraining Recommendation** component. Each run has three steps that share an `emptyDir`:

| Step | Image | What it does |
|------|-------|--------------|
| `extract` | `ghcr.io/burakince/mlflow` | Resolves the version behind the serving alias in MLflow, downloads its training frame (`reference/reference.csv`) and builds the same feature vectors from the recent data of the platform data stock (`sensor_readings`) |
| `drift` | Evidently | Runs the `DataDriftPreset` between both datasets and stores the report in the Evidently UI project of the model |
| `recommend` | `ghcr.io/burakince/mlflow` | Recommends retraining when the share of drifted features reaches `threshold`; records the result in `retraining_recommendations` (TimescaleDB), logs the HTML report to MLflow (experiment `zdm-drift-monitoring`) and, when `autoRetrain` is on, creates a retraining Job from the `platform-training-jobs` CronJob with `TRIGGER=drift` |

The drift reference is always the training data **of the version actually served**, so a recommendation is traceable to a model version, its MLflow run and its report. A `cooldown` prevents a persistent drift from launching a retraining every 30 minutes. The drift check runs under a dedicated ServiceAccount whose Role only allows reading that CronJob and creating Jobs.

Every step writes JSON lines to stdout (Fluent Bit and Loki, B.6.2.8.1).

---

## Quick start

```bash
helm repo add cigip-upv https://cigip-upv.github.io/MLOps-ISO42001-K3s-Catalog
helm install platform-evidently cigip-upv/platform-evidently -n mlops

# Run a drift check now
kubectl -n mlops create job --from=cronjob/platform-evidently-drift drift-now
kubectl -n mlops logs job/drift-now --all-containers
```

Prerequisites: `platform-mlflow`, `platform-timescaledb`, `platform-training-jobs` and the Secret `platform-ml-db`, created by `infrastructure/install.sh`.

```sql
SELECT created_at, model_version, drift_share, drifted_columns, recommended, action, report_uri
  FROM retraining_recommendations ORDER BY id DESC LIMIT 10;
```

---

## Configuration

The default values are defined in [`values.yaml`](./manifests/values.yaml);
the Rancher questionnaire lives in [`questions.yaml`](./manifests/questions.yaml).

| Area | Variable | Default |
|------|----------|---------|
| Schedule | `driftCheck.schedule` | `*/30 * * * *` |
| Windows | `driftCheck.currentWindow`, `driftCheck.bucket`, `driftCheck.minCurrentRows` | `1 hour`, `10 seconds`, `30` |
| Decision | `driftCheck.threshold` | `0.5` (share of drifted features) |
| Activation | `driftCheck.autoRetrain`, `driftCheck.trainingCronJob`, `driftCheck.cooldown` | `true`, `platform-training-jobs`, `6 hours` |
| UI | `ui.persistence.size`, `ingress.enabled` | `5Gi`, `false` |

---

## ISO/IEC 42001 traceability

| Clause | Requirement |
|--------|-------------|
| `B.6.2.6.2` | Operation: Model Performance (data drift of the served model version) |
| `B.6.2.8.1` | Operation: Logging / Audit Trail (reports kept in the UI and in MLflow, recommendations in the data stock) |
| `B.8.0.5.1` | Continual Improvement: Alerts (retraining recommendation and activation) |

```bash
kubectl get deploy,cronjob,job,pod -n mlops -l mlops-iso42001.cigip-upv.es/chart=platform-evidently
```

The mapping is maintained at the catalog level in the root [`README.md`](https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog#isoiec-42001-coverage-summary).

---

## Maintainer

- **CIGIP-UPV**, *https://cigip.webs.upv.es/*, `cigip@upv.es`

Released under the Apache 2.0 License.
