# Grafana Dashboards (Overlay): `enterprise-grafana-dashboards`

> Provisioned Grafana dashboards for OEE, model health, infrastructure, security events and the audit log.

[![Tier](https://img.shields.io/badge/tier-enterprise-92400e)](#) [![ISO/IEC 42001](https://img.shields.io/badge/ISO%2FIEC-42001-991b1b)](#) [![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

Part of the [K3s Solution Catalog for ISO/IEC 42001](https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog).

---

## Overview

- **Tier**: `enterprise`
- **Category**: `Dashboards`
- **Namespace**: `monitoring`
- **Reference architecture components**: `CMP-06` Information Centre, `CMP-11` Goal-Oriented Monitoring (enterprise view); *Business Dashboard* subcomponent
- **ISO/IEC 42001 Annex B clauses covered**: `B.6.1.3.3`, `B.6.2.6.2`

The chart provisions the enterprise dashboards of the AI system into the Grafana of [`platform-grafana`](../../../platform/monitoring/grafana/README.md): one ConfigMap per dashboard, labelled `grafana_dashboard=1` so the Grafana sidecar loads it into the folder *ZDM AI System*. The dashboards are standard Grafana JSON models ([`manifests/files/dashboards/`](./manifests/files/dashboards/)) that use the data sources provisioned by `platform-grafana` (uids `prometheus`, `loki`, `timescaledb`, `edgepg`).

| Dashboard | Data source | Content |
|-----------|-------------|---------|
| ZDM: Model Health (CMP-10) | Prometheus | Served version, predictions by outcome, anomaly ratio, p95 latency, score distribution, reloads |
| ZDM: Input Data Monitoring (CMP-01) | Prometheus | Age of the last valid sample, valid and rejected samples by reason, OPC UA reads and errors |
| ZDM: Data Consolidation, KPIs and Drift | TimescaleDB | Rows consolidated from the edge, last batches, OEE by machine, drift share and retraining recommendations |
| ZDM: Security Events and Audit Trail | Loki | Falco events, Kubernetes API changes (audit log), events of the MLOps jobs |
| ZDM: Edge Predictions and Model Versions | Edge PostgreSQL | Predictions, version history of edge version control, operator feedback records of the edge table |
| ZDM: Operator Feedback (CMP-12) | TimescaleDB | Disagreement rate by model version, verdicts over time, corrected labels and latest verdicts from the feedback interface |

The Kubernetes infrastructure dashboards (CMP-08) come from `platform-prometheus` (kube-prometheus-stack), which renders them for the same sidecar.

Earlier versions of this chart shipped an empty `values.yaml` and a ConfigMap with pseudo-JSON descriptions of dashboards that Grafana could not import.

Operator verdicts are captured by [`enterprise-feedback-interface`](../../human-oversight/feedback-interface/README.md) (Feedback Interface, CMP-12) and stored in the platform data stock, which the *Operator Feedback* dashboard reads; the edge `operator_feedback` table is kept for a future interface at the plant.

---

## Quick start

```bash
helm repo add cigip-upv https://cigip-upv.github.io/MLOps-ISO42001-K3s-Catalog
helm install enterprise-grafana-dashboards cigip-upv/enterprise-grafana-dashboards -n monitoring
```

Prerequisite: `platform-grafana` with its sidecar searching all namespaces (default).

---

## Configuration

The default values are defined in [`values.yaml`](./manifests/values.yaml) (folder and one switch per dashboard);
the Rancher questionnaire lives in [`questions.yaml`](./manifests/questions.yaml). To change a dashboard,
edit it in Grafana, export the JSON model and replace the file in `manifests/files/dashboards/`.

---

## ISO/IEC 42001 traceability

| Clause | Requirement |
|--------|-------------|
| `B.6.1.3.3` | Resources: Human Oversight / Feedback (operators and managers see model behaviour, data quality, drift and security) |
| `B.6.2.6.2` | Operation: Model Performance (model health dashboard) |

```bash
kubectl get configmap -n monitoring -l mlops-iso42001.cigip-upv.es/chart=enterprise-grafana-dashboards
```

The mapping is maintained at the catalog level in the root [`README.md`](https://github.com/CIGIP-UPV/MLOps-ISO42001-K3s-Catalog#isoiec-42001-coverage-summary).

---

## Maintainer

- **CIGIP-UPV**, *https://cigip.webs.upv.es/*, `cigip@upv.es`

Released under the Apache 2.0 License.
