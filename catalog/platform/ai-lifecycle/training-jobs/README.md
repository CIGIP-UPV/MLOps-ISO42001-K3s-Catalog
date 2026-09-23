# Training Jobs: `platform-training-jobs`

> Model training pipeline: scheduled CronJob and on-demand Job that train on the consolidated platform data and register the model in MLflow.

[![Tier](https://img.shields.io/badge/tier-platform-1e40af)](#) [![ISO/IEC 42001](https://img.shields.io/badge/ISO%2FIEC-42001-991b1b)](#) [![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Part of the [K3s Solution Catalog for ISO/IEC 42001](https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog).

---

## Overview

- **Tier**: `platform`
- **Category**: `AI Lifecycle`
- **Namespace**: `mlops`
- **Reference architecture components**: `CMP-04` Model (platform), `CMP-14` Retraining Recommendation (execution of the recommended retraining); *Model Training Pipeline* subcomponent
- **ISO/IEC 42001 Annex B clauses covered**: `B.6.2.6.4`

This chart provides the **Model Training Pipeline** of the reference architecture. The training code (`manifests/files/train.py`) is mounted from a ConfigMap and runs on the public `ghcr.io/burakince/mlflow` image, so no private registry is needed. Each run:

1. reads the consolidated sensor readings of the training window from the platform data stock (`platform-timescaledb`, table `sensor_readings`, read-only role `ml`) and builds one feature vector per machine and time bucket;
2. trains an **IsolationForest** anomaly detector, the reference model for zero-defect manufacturing (abnormal process states flagged before they become defects);
3. evaluates the **release criteria** (minimum number of samples, maximum anomaly rate on the training data, B.6.1.3.4);
4. logs parameters, metrics and the training frame (`reference/reference.csv`, the reference data used by the drift check) to MLflow and registers a new model version;
5. tags the version with its **data provenance** (source table, time window, number of rows, edge sites and last consolidation batch) and, when the criteria pass, moves the serving alias (`champion`), which `edge-mlflow-sync` then propagates to the edge.

The same job template serves three triggers, recorded in the `trigger` tag of the run and the version:

| Trigger | How |
|---------|-----|
| `schedule` | The CronJob (`schedule`, nightly by default) |
| `manual` | `kubectl -n mlops create job --from=cronjob/platform-training-jobs retrain-now` |
| `drift` | The drift check of `platform-evidently`, when drift exceeds its threshold |

Exit codes: `0` registered and promoted, `2` not enough data (nothing registered), `3` registered but not promoted (release criteria failed).

---

## Quick start

```bash
helm repo add cigip-upv https://cigip-upv.github.io/MLOps-ISO42001-K3s-Catalog
helm install platform-training-jobs cigip-upv/platform-training-jobs -n mlops

kubectl -n mlops create job --from=cronjob/platform-training-jobs retrain-now
kubectl -n mlops logs job/retrain-now
```

Prerequisites: `platform-timescaledb` with consolidated data, `platform-mlflow`, and the Secret `platform-ml-db` (key `password` of the role `ml`), created by `infrastructure/install.sh`.

---

## Configuration

The default values are defined in [`values.yaml`](./manifests/values.yaml);
the Rancher questionnaire lives in [`questions.yaml`](./manifests/questions.yaml).

| Area | Variable | Default |
|------|----------|---------|
| Schedule | `schedule` | `0 2 * * *` |
| Registry | `mlflow.modelName`, `mlflow.alias`, `mlflow.promote` | `zdm-anomaly-detector`, `champion`, `true` |
| Training | `training.window`, `training.bucket`, `training.contamination` | `24 hours`, `10 seconds`, `0.02` |
| Release criteria | `releaseCriteria.minSamples`, `releaseCriteria.maxAnomalyRate` | `200`, `0.10` |
| Data | `dataStock.*` | `platform-timescaledb.platform`, role `ml` |

---

## ISO/IEC 42001 traceability

| Clause | Requirement |
|--------|-------------|
| `B.6.2.6.4` | Operation: Retraining / Lifecycle (scheduled, manual and drift-triggered retraining with release criteria and provenance) |

```bash
kubectl get cronjob,job,pod -n mlops -l mlops-iso42001.cigip-upv.es/chart=platform-training-jobs
```

The mapping is maintained at the catalog level in the root [`README.md`](https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog#isoiec-42001-coverage-summary).

---

## Maintainer

- **CIGIP-UPV**, *https://cigip.webs.upv.es/*, `cigip@upv.es`

Released under the Apache 2.0 License.
