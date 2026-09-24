# FastAPI Model Server: Edge AI Inference

| Field | Value |
|-------|-------|
| **Chart** | `edge-fastapi-model` |
| **Tier** | Edge |
| **Namespace** | `edge` |
| **Category** | AI Inference |
| **RA Components** | Model (CMP-04, edge); Model Technical Performance Monitoring (CMP-10, edge subcomponent) |
| **ISO/IEC 42001** | B.6.2.6.2 · B.6.2.6.4 |
| **Deployment** | Own Helm chart; application code in `manifests/files/app.py`, public runtime image |
| **K3S Compatible** | Yes |

---

## Description

The FastAPI Model Server is the **edge Model** component: a Python service that serves the AI model through a REST API close to the data source, for **low-latency inference** without a round trip to the platform.

It never builds or bakes a model into an image. It serves the model version that the **edge Version Control** component ([`edge-mlflow-sync`](../../version-control/mlflow-sync/README.md)) has propagated from the platform MLflow registry into a shared volume:

```
/models/current.json              name, version, run, features and SHA-256 of the active version
/models/versions/<name>-v<N>/     MLflow pyfunc model of each synchronised version
```

The application (`manifests/files/app.py`) is mounted from a ConfigMap and runs on `ghcr.io/burakince/mlflow`, a public image that already bundles MLflow, scikit-learn, FastAPI, uvicorn, `prometheus_client` and `psycopg2`. No private registry is needed.

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Liveness (process up) |
| `GET /ready` | `200` when a model is loaded, `503` before the first promotion |
| `GET /version` | Model name, version, MLflow run, features and SHA-256 of the served version |
| `POST /reload` | Load the version pointed to by `current.json` (called by `edge-mlflow-sync`) |
| `POST /predict` | Score samples: `{"samples": [{"machine_id": "cnc-01", "features": {"temperature": 61.0, ...}}]}` |
| `GET /metrics` | Prometheus metrics |

Every prediction is written to the `predictions` table of the edge data stock (`edge-postgresql`) and emitted as a JSON line on stdout, which Fluent Bit ships to Loki (B.6.2.8.1).

The `/metrics` endpoint is the **edge subcomponent of CMP-10** (Model Technical Performance Monitoring): `edge-prometheus-agent` scrapes it through the pod annotations and forwards it to the platform Prometheus. Metrics: `model_predictions_total{model_name,model_version,outcome}`, `model_prediction_latency_seconds`, `model_anomaly_score`, `model_info{model_name,model_version}`, `model_loaded`, `model_reloads_total` and `model_prediction_log_errors_total`.

---

## ISO/IEC 42001 Mapping

| Clause | Requirement | How the FastAPI Model Server addresses it |
|--------|-------------|-------------------------------------------|
| B.6.2.6.2 | Operation: Model Performance | Latency, outcome and score metrics per model version on `/metrics` |
| B.6.2.6.4 | Operation: Retraining / Lifecycle | Hot reload of each version promoted in the registry; `/version` exposes which one is served |

---

## Prerequisites

- `edge-postgresql` (prediction log) and the Secret `edge-postgresql-auth`.
- `edge-mlflow-sync`, installed after this chart, to populate the model store.
- `edge-prometheus-agent` to scrape `/metrics`.
- An edge node labelled `node-role.kubernetes.io/edge=true`.

---

## Deployment Questionnaire

The Rancher questionnaire is [`manifests/questions.yaml`](./manifests/questions.yaml).

---

## Installation (Helm)

```bash
helm repo add cigip-upv https://cigip-upv.github.io/MLOps-ISO42001-K3s-Catalog
helm install edge-fastapi-model cigip-upv/edge-fastapi-model -n edge
```

Until a model version is promoted and synchronised, `/ready` returns `503` and `/predict` refuses requests. After the first synchronisation:

```bash
kubectl -n edge port-forward svc/edge-fastapi-model 8000:8000
curl localhost:8000/version
curl localhost:8000/predict -H 'content-type: application/json' \
  -d '{"samples":[{"machine_id":"cnc-01","features":{"temperature":61,"vibration":1.1,"pressure":5.2}}]}'
```

---

## Key Configuration Decisions

| Decision | Options | Choice in this chart |
|----------|---------|----------------------|
| Model loading | Baked into image / mounted volume / remote pull | **Mounted volume** written by `edge-mlflow-sync`: models change without rebuilding or restarting |
| Runtime image | Custom image / public image + code in ConfigMap | **Public image + ConfigMap**: reproducible without a private registry |
| Readiness | Model loaded / process up | Readiness on `/health` so the release installs before the first model exists; `/ready` reports the model state |
| Update strategy | RollingUpdate / Recreate | **Recreate**: the model volume is `ReadWriteOnce` |
| GPU | Enabled / Disabled | Not used: the reference model (IsolationForest) runs on CPU |

---

## Related Solutions

- [Edge Version Control](../../version-control/mlflow-sync/README.md): propagates the promoted model version to this server
- [PostgreSQL (edge)](../../storage/postgresql/README.md): prediction log
- [Prometheus Agent](../../monitoring/prometheus-agent/README.md): scrapes `/metrics`
- [MLflow](../../../platform/ai-lifecycle/mlflow/README.md): model registry on the platform
