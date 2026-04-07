# Prometheus — Infrastructure & Model Performance Monitoring

| Field | Value |
|-------|-------|
| **Tier** | Platform |
| **Category** | Monitoring |
| **RA Component** | Infrastructural Technical Performance Monitoring · Model-based Technical Performance Monitoring |
| **ISO/IEC 42001** | B.6.1.2.2 · B.6.2.6.1 · B.6.2.6.2 |
| **Helm Chart** | `prometheus-community/kube-prometheus-stack` |
| **K3S Compatible** | Yes |

---

## Description

Prometheus is the **metrics collection and alerting backbone** for both infrastructure monitoring and AI model performance monitoring in the reference architecture. Deployed at the platform tier, it scrapes metrics from all tiers (edge agents forward metrics via remote-write or federation).

Its key roles are:

- **Infrastructure monitoring**: monitors CPU, memory, disk, network, and container health for all K3S nodes and pods across edge and platform tiers.
- **AI model technical monitoring**: scrapes custom metrics from the FastAPI model server (`/metrics` endpoint) — inference latency, error rates, prediction score distribution, model version.
- **Alerting**: Alertmanager integration triggers alerts when thresholds are crossed (e.g., latency > 500ms, error rate > 1%, disk usage > 85%).
- **Drift signal source**: Prometheus metrics on prediction score distributions feed the retraining recommendation decision logic.

The `kube-prometheus-stack` Helm chart bundles Prometheus, Alertmanager, and Grafana (pre-configured dashboards), providing an integrated observability stack.

---

## ISO/IEC 42001 Mapping

| Clause | Requirement | How Prometheus Addresses It |
|--------|-------------|------------------------------|
| B.6.1.2.2 | Integration of Metrics | Central metrics collection across all lifecycle stages |
| B.6.2.6.1 | Error Monitoring | Infrastructure and application error rate tracking with alerting |
| B.6.2.6.2 | Technical Performance Monitoring | Model-specific metrics (latency, accuracy, throughput) |

---

## Prerequisites

- K3S platform cluster with at least 4 GB RAM (Prometheus is memory-intensive)
- Persistent volumes for Prometheus data retention (minimum 20 GB recommended)
- Edge Prometheus Agent (`prometheus-agent` mode) deployed at edge tier and configured for remote-write

---

## Deployment Questionnaire

See [`questionnaire.md`](./questionnaire.md).

---

## Installation (K3S / Helm)

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  -f values.yaml
```

---

## Key Metrics to Monitor (AI System)

| Metric | Source | Alert Threshold |
|--------|--------|-----------------|
| `model_inference_latency_p95` | FastAPI | > 500ms |
| `model_prediction_score_mean` | FastAPI | Drift from baseline ± 2σ |
| `model_error_rate` | FastAPI | > 1% |
| `model_version` | FastAPI | Change triggers notification |
| `node_memory_utilisation` | K3S node | > 85% |
| `container_cpu_throttling` | cAdvisor | > 20% |

---

## Related Solutions

- [Grafana](../grafana/README.md) — dashboards consuming Prometheus metrics
- [Prometheus Agent](../../../edge/monitoring/prometheus-agent/README.md) — edge-tier metrics collection
- [FastAPI Model Server](../../../edge/ai-inference/fastapi-model/README.md) — primary metrics source for AI monitoring
- [Training Jobs](../../ai-lifecycle/training-jobs/README.md) — training run metrics exposed during execution
