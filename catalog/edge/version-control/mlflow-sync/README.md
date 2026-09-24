# Edge Version Control (MLflow Sync): `edge-mlflow-sync`

> Propagates the model version promoted in the platform MLflow registry to the edge: downloads it, records the version history and hot-reloads the edge model server.

[![Tier](https://img.shields.io/badge/tier-edge-065f46)](#) [![ISO/IEC 42001](https://img.shields.io/badge/ISO%2FIEC-42001-991b1b)](#) [![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Part of the [K3s Solution Catalog for ISO/IEC 42001](https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog).

---

## Overview

- **Tier**: `edge`
- **Category**: `Version Control`
- **Namespace**: `edge`
- **Reference architecture component**: `CMP-03` Version Control (edge), *version propagation* flow (Version Control platform to Version Control edge)
- **ISO/IEC 42001 Annex B clauses covered**: `B.6.1.3.2`, `B.6.2.6.4`, `B.6.2.8.1`

The reference architecture places **Version Control** (CMP-03, mandatory) at both the platform and the edge level, and adds a *version propagation* flow from the platform to the edge. The catalog covered the platform side with MLflow, but nothing at the edge kept track of which model version was deployed or brought new versions to the edge model server, which loaded a fixed file.

This chart provides the edge side. A **CronJob** follows an alias of a registered model (by default `models:/zdm-anomaly-detector@champion`) and, whenever the alias moves to a new version:

1. downloads the version **through the MLflow server** (proxied artefacts), so the edge never holds object storage credentials;
2. loads it once as a smoke test and computes the **SHA-256** of the artefact;
3. switches `current.json` in the model store of [`edge-fastapi-model`](../../ai-inference/fastapi-model/README.md) atomically and calls `POST /reload`;
4. verifies that `GET /version` reports the new version; if not, it restores the previous version;
5. records each step (`downloaded`, `active`, `download_failed`, `activation_failed`) in the `model_versions` table of the edge data stock and as JSON lines for Fluent Bit.

The last `keepVersions` versions stay on disk, so the edge can go back to a previous version by moving the alias back in the registry. The alias is the single control point: promoting, rolling back or pinning a version at the edge is a registry operation, recorded by MLflow on the platform and by this chart on the edge.

The chart has no upstream dependency; the script (`manifests/files/sync.py`) runs on the same public MLflow image as the model server.

---

## Prerequisites

- `platform-mlflow` reachable from the edge namespace (TCP 5000; allowed by `infrastructure/01-network-policies.yaml`).
- `edge-fastapi-model` installed first: this chart mounts its model store PVC (`edge-fastapi-model-storage`).
- `edge-postgresql` with the `model_versions` table and the Secret `edge-postgresql-auth`.

---

## Quick start

```bash
helm repo add cigip-upv https://cigip-upv.github.io/MLOps-ISO42001-K3s-Catalog
helm install edge-mlflow-sync cigip-upv/edge-mlflow-sync -n edge

# Force a synchronisation now
kubectl -n edge create job --from=cronjob/edge-mlflow-sync sync-now
kubectl -n edge logs job/sync-now
```

Version history at the edge:

```sql
SELECT model_name, model_version, status, artefact_sha256, received_at
  FROM model_versions ORDER BY id DESC;
```

---

## Configuration

The default values are defined in [`values.yaml`](./manifests/values.yaml);
the Rancher questionnaire lives in [`questions.yaml`](./manifests/questions.yaml).

| Area | Variable | Default | Notes |
|------|----------|---------|-------|
| Registry | `registry.trackingUri` | `http://platform-mlflow.mlops.svc.cluster.local:5000` | Platform MLflow |
| Registry | `registry.modelName`, `registry.alias` | `zdm-anomaly-detector`, `champion` | Alias followed by the edge |
| Schedule | `schedule` | `*/2 * * * *` | Maximum propagation delay |
| Model server | `modelServer.url`, `modelServer.modelStoreClaim` | `edge-fastapi-model` | Reload endpoint and shared PVC |
| Rollback | `modelServer.keepVersions` | `3` | Versions kept on disk |

---

## Key design decisions

- **Pull from the edge.** The edge asks the registry for the alias; the platform needs no network access into the edge.
- **Alias, not stage.** MLflow aliases replace the deprecated stages and give a single, auditable pointer per environment.
- **Verify before and after switching.** The version must load before it becomes current, and the server must report it after the reload; otherwise the previous version is restored.
- **One run at a time.** Runs take a lock on the model store, so a run started by hand while the CronJob runs waits for it instead of downloading the same version at the same time.
- **Suspension.** When a supervisor suspends the served version in [`enterprise-feedback-interface`](../../../enterprise/human-oversight/feedback-interface/README.md) (tag `suspended=true` in the registry), the next run marks it as suspended in `current.json`, the model server answers `503`, and `model_versions` records `suspended`; removing the tag records `resumed`.

---

## ISO/IEC 42001 traceability

| Clause | Requirement |
|--------|-------------|
| `B.6.1.3.2` | Resources: Version Control (version history and SHA-256 of every model version deployed at the edge) |
| `B.6.2.6.4` | Operation: Retraining / Lifecycle (retrained versions reach the edge without manual steps) |
| `B.6.2.8.1` | Operation: Logging / Audit Trail (JSON log of every propagation step) |

```bash
kubectl get cronjob,job,pod -n edge -l mlops-iso42001.cigip-upv.es/chart=edge-mlflow-sync
```

The mapping is maintained at the catalog level in the root [`README.md`](https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog#isoiec-42001-coverage-summary).

---

## Maintainer

- **CIGIP-UPV**, *https://cigip.webs.upv.es/*, `cigip@upv.es`

Released under the Apache 2.0 License.
