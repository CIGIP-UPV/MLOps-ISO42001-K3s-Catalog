# Feedback Interface: `enterprise-feedback-interface`

> Operators approve, correct or reject model predictions; supervisors can suspend the version in service. The verdicts are labels for the next training.

[![Tier](https://img.shields.io/badge/tier-enterprise-92400e)](#) [![ISO/IEC 42001](https://img.shields.io/badge/ISO%2FIEC-42001-991b1b)](#) [![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Part of the [K3s Solution Catalog for ISO/IEC 42001](https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog).

---

## Overview

- **Tier**: `enterprise`
- **Category**: `Human Oversight`
- **Namespace**: `feedback`
- **Reference architecture component**: `CMP-12` Feedback Interface
- **ISO/IEC 42001 Annex B clauses covered**: `B.6.1.3.3`, `B.6.2.6.4`

The reference architecture includes a **Feedback Interface** (CMP-12, recommended, enterprise level) in the short detection and repair loop: the operator approves, corrects or rejects what the model says, and that evidence feeds the next iterations of the lifecycle. It also supports the requirement that a person can supervise, interrupt and correct the decisions of the system. Until this chart, the catalog had no component for it: the edge data stock had an `operator_feedback` table that nothing used.

This chart provides a small web application (FastAPI with server-side HTML, no JavaScript) that:

1. lists the recent predictions **consolidated in the platform data stock** (TimescaleDB), with the model version that made them and the latest verdict;
2. records the **verdict** of the signed-in operator on a prediction: `correct`, `incorrect` or `uncertain`, with an optional corrected label (`normal`, `anomaly`) and comment. Verdicts are appended to the `operator_feedback` table of the platform, never overwritten; the operator, the model version and the predicted label are taken from the session and the stored prediction, not from the request;
3. lets a **supervisor suspend** the version in service, with a reason, and resume it. The suspension is a tag on the model version in the MLflow registry; [`edge-mlflow-sync`](../../../edge/version-control/mlflow-sync/README.md) propagates it and [`edge-fastapi-model`](../../../edge/ai-inference/fastapi-model/README.md) answers `503` while the version is suspended.

The verdicts close the loop: [`platform-training-jobs`](../../../platform/ai-lifecycle/training-jobs/README.md) uses the latest verdict of each prediction, with the input features recorded for it, as a label to measure the agreement of every new candidate with the operators and, with enough labels, to block its release. [`enterprise-grafana-dashboards`](../../dashboards/grafana/README.md) shows verdicts and the disagreement rate by model version.

The application runs on the same public image as the model server and the training job (`ghcr.io/burakince/mlflow`), with its code in a ConfigMap: no extra image and no package download at start-up.

---

## Prerequisites

- `platform-timescaledb` with the `operator_feedback` table and the `feedback` role, created by its schema Job, and the Secret `enterprise-feedback-db` (created by `install.sh`).
- `enterprise-keycloak` with the client `feedback-interface` in the `ai-system` realm (part of its realm import) and users holding the `operator`, `production-manager` or `compliance-officer` realm roles.
- `platform-mlflow` for the suspension tags.
- The `feedback` namespace and its conduits from `infrastructure/`: the interface may reach only the TimescaleDB, Keycloak and MLflow pods.

---

## Quick start

```bash
helm repo add cigip-upv https://cigip-upv.github.io/MLOps-ISO42001-K3s-Catalog
helm install enterprise-feedback-interface cigip-upv/enterprise-feedback-interface -n feedback

kubectl -n feedback port-forward svc/enterprise-feedback-interface 8000:8000
# open http://127.0.0.1:8000 and sign in with a user of the ai-system realm
```

Scripted use (JSON API, same session and CSRF protection as the pages):

```bash
curl -c jar -H 'Content-Type: application/json' -d '{"username":"...","password":"..."}' http://127.0.0.1:8000/login
CSRF=$(curl -b jar http://127.0.0.1:8000/api/session | python3 -c 'import json,sys;print(json.load(sys.stdin)["csrf"])')
curl -b jar http://127.0.0.1:8000/api/predictions
curl -b jar -H "X-CSRF-Token: $CSRF" -H 'Content-Type: application/json' \
  -d '{"site_id":"...","source_id":1,"time":"...","verdict":"incorrect","corrected_label":"normal"}' \
  http://127.0.0.1:8000/feedback
```

Disagreement rate by model version:

```sql
WITH latest AS (
  SELECT DISTINCT ON (site_id, prediction_source_id, prediction_time) model_version, verdict
    FROM operator_feedback ORDER BY site_id, prediction_source_id, prediction_time, created_at DESC)
SELECT model_version, count(*) FILTER (WHERE verdict = 'incorrect')::float
       / NULLIF(count(*) FILTER (WHERE verdict <> 'uncertain'), 0) AS disagreement_rate
  FROM latest GROUP BY model_version;
```

---

## Configuration

The default values are defined in [`values.yaml`](./manifests/values.yaml);
the Rancher questionnaire lives in [`questions.yaml`](./manifests/questions.yaml).

| Area | Variable | Default | Notes |
|------|----------|---------|-------|
| Sign-in | `keycloak.url`, `keycloak.realm`, `keycloak.clientId` | `enterprise-keycloak`, `ai-system`, `feedback-interface` | In-cluster address |
| Roles | `roles.verdict`, `roles.suspend` | operator and supervisors; supervisors | Realm roles |
| Session | `session.ttlSeconds`, `session.secureCookie` | `1800`, `false` | Set `secureCookie` behind TLS |
| Data | `dataStock.*` | TimescaleDB, role `feedback` | Secret `enterprise-feedback-db` |
| Registry | `registry.modelName`, `registry.alias` | `zdm-anomaly-detector`, `champion` | Version that can be suspended |
| Listing | `predictions.lookback`, `predictions.pageSize` | `24 hours`, `50` | |
| Exposure | `ingress.enabled` | `false` | Port-forward by default |

---

## Key design decisions

- **Enterprise level, platform data.** The interface reads and writes the platform data stock, so it needs no conduit into the edge; operators see predictions once they are consolidated (every 5 minutes by default).
- **Append-only verdicts.** Every verdict is kept for the audit trail; the latest verdict of a prediction is the one in force.
- **Suspension in the registry.** The suspension lives on the model version in MLflow, the single source of version control, and reaches the edge through the existing propagation flow instead of a new conduit.
- **Sign-in from the server side.** The interface sends the credentials to Keycloak from inside the cluster (resource owner password grant) and checks the signature and roles of the token. This avoids exposing Keycloak to browsers, which the browser redirect flow needs; the password grant is discouraged by OAuth 2.1, so use the redirect flow once Keycloak is published with TLS.

---

## ISO/IEC 42001 traceability

| Clause | Requirement |
|--------|-------------|
| `B.6.1.3.3` | Resources: Human Oversight / Feedback (operator verdicts; suspension of the version in service) |
| `B.6.2.6.4` | Operation: Retraining / Lifecycle (verdicts used as labels by the training job) |

```bash
kubectl get deploy,svc,pod -n feedback -l mlops-iso42001.cigip-upv.es/chart=enterprise-feedback-interface
```

The application logs `feedback_recorded`, `login_succeeded`, `login_failed`, `model_suspended` and `model_resumed` as JSON lines, and exposes `feedback_verdicts_total`, `feedback_logins_total` and `model_suspensions_total` on `/metrics`.

The mapping is maintained at the catalog level in the root [`README.md`](https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog#isoiec-42001-coverage-summary).

---

## Tests

```bash
pip install pytest httpx   # plus the application dependencies (FastAPI, PyJWT, ...)
pytest catalog/enterprise/human-oversight/feedback-interface/tests
```

---

## Maintainer

- **CIGIP-UPV**, *https://cigip.webs.upv.es/*, `cigip@upv.es`

Released under the Apache 2.0 License.
