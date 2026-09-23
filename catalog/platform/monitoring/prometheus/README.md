# Prometheus + Alertmanager: Infrastructure and Model Performance Monitoring

| Field | Value |
|-------|-------|
| **Chart** | `platform-prometheus` |
| **Tier** | Platform |
| **Namespace** | `monitoring` |
| **Category** | Monitoring |
| **RA Components** | Infrastructure Technical Monitoring (CMP-08); Model Technical Performance Monitoring (CMP-10); Goal-Oriented Monitoring (CMP-11) |
| **ISO/IEC 42001** | B.6.1.2.2 · B.6.2.6.2 · B.8.0.5.1 |
| **Helm Chart** | `prometheus-community/kube-prometheus-stack` 61.x (wrapped) |
| **K3S Compatible** | Yes |

---

## Description

Prometheus is the **metrics and alerting backbone** of the reference architecture. The chart deploys kube-prometheus-stack (Prometheus Operator, Prometheus, Alertmanager, node-exporter, kube-state-metrics) with `fullnameOverride: platform-prometheus`.

Key settings:

- **Remote-write receiver** on: the edge Prometheus Agents (`edge-prometheus-agent`) push the edge metrics (model server, ingestion flow, OPC UA gateway, brokers, databases).
- **ServiceMonitor selection across the catalog**: `serviceMonitorSelectorNilUsesHelmValues: false` (and the same for PodMonitors, rules and probes), so the ServiceMonitors of MLflow, MinIO, PostgreSQL, TimescaleDB, Loki, Grafana, Keycloak and cert-manager are scraped. With the upstream default, only this release's monitors would be.
- **K3s**: the controller manager, scheduler, proxy and etcd run inside the k3s process and cannot be scraped; those targets are disabled to avoid permanent `TargetDown` alerts.
- **Kubernetes dashboards** are rendered as ConfigMaps for the sidecar of `platform-grafana` (`forceDeployDashboards`).
- **Grafana** of the stack is disabled (deployed by `platform-grafana`).

Alert rules (`ai-system-rules`, validated with `promtool`) use the metrics the catalog actually exposes:

| Alert | Expression basis | Severity |
|-------|------------------|----------|
| ModelNotLoaded | `model_loaded == 0` for 15 min | warning |
| ModelInferenceLatencyHigh | p95 of `model_prediction_latency_seconds` > 0.5 s | warning |
| ModelAnomalyRateHigh | anomalies / predictions > 20% for 15 min | critical |
| PredictionLogFailing | `model_prediction_log_errors_total` increases | warning |
| IngestionStalled | no valid sample for 5 min (`ingest_last_sample_timestamp_seconds`) | critical |
| IngestionRejectionRateHigh | rejected samples > 10% | warning |
| OpcUaGatewayReadErrors | `internal_gather_errors{input="opcua"}` increases | warning |
| AIContainerThrottled | CPU throttling of AI containers > 25% | warning |

The earlier rules queried metrics that no component exposed, so they could never fire.

**Alertmanager** groups the `component=ai-system` alerts in the receiver `ai-system`, which has no notifier configured. Zammad offers no endpoint for the Alertmanager webhook format, so the earlier `zammad-webhook` receiver was removed: add an `email_configs` entry to a Zammad mailbox, or an adapter that calls the Zammad ticket API, to open tickets automatically.

---

## ISO/IEC 42001 Mapping

| Clause | Requirement | How Prometheus Addresses It |
|--------|-------------|------------------------------|
| B.6.1.2.2 | Resources: Monitoring Performance | Central metrics collection for every tier |
| B.6.2.6.2 | Operation: Model Performance | Model latency, outcomes and anomaly rate, with alert rules |
| B.8.0.5.1 | Continual Improvement: Alerts | Alertmanager grouping and routing of AI system alerts |

---

## Prerequisites

- Memory: Prometheus requests 1 GiB (limit 3 GiB); 20 GiB volume, 15-day retention.
- Install it before the charts that ship ServiceMonitors (`infrastructure/install.sh` applies the Prometheus Operator CRDs in its base phase).

---

## Deployment Questionnaire

The Rancher questionnaire is [`manifests/questions.yaml`](./manifests/questions.yaml).

---

## Installation (Helm)

```bash
helm repo add cigip-upv https://cigip-upv.github.io/MLOps-ISO42001-K3s-Catalog
helm install platform-prometheus cigip-upv/platform-prometheus -n monitoring

kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/chart=platform-prometheus
```

---

## Related Solutions

- [Grafana](../grafana/README.md): dashboards on Prometheus metrics
- [Prometheus Agent](../../../edge/monitoring/prometheus-agent/README.md): edge metrics via remote-write
- [FastAPI Model Server](../../../edge/ai-inference/fastapi-model/README.md): model metrics
- [Node-RED](../../../edge/data-ingestion/node-red/README.md): input data monitoring metrics
- [Zammad](../../../enterprise/helpdesk/zammad/README.md): helpdesk (alert integration to be configured)
