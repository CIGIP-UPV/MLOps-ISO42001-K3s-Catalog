# Grafana: Information Centre and Monitoring Dashboards

| Field | Value |
|-------|-------|
| **Chart** | `platform-grafana` |
| **Tier** | Platform |
| **Namespace** | `monitoring` |
| **Category** | Monitoring · Dashboards |
| **RA Components** | Information Centre (CMP-06); Model Technical Performance Monitoring (CMP-10); Goal-Oriented Monitoring (CMP-11) |
| **ISO/IEC 42001** | B.6.1.3.1 · B.6.1.3.3 · B.6.2.6.2 |
| **Helm Chart** | `grafana/grafana` 8.x (Grafana 11.6, wrapped) |
| **K3S Compatible** | Yes |

---

## Description

Grafana is the **user-facing transparency interface** of the reference architecture: it brings metrics (Prometheus), logs (Loki) and operational data (TimescaleDB, edge PostgreSQL) together in dashboards for operators, engineers and managers.

What the chart configures:

- **Data sources**, provisioned with fixed uids that the dashboards use:

| Name | uid | Target |
|------|-----|--------|
| Prometheus | `prometheus` | `platform-prometheus-prometheus.monitoring:9090` |
| Loki | `loki` | `platform-loki.monitoring:3100` |
| TimescaleDB | `timescaledb` | `platform-timescaledb.platform:5432`, database `zdm_platform`, read-only role `grafana` |
| Edge PostgreSQL | `edgepg` | `edge-postgresql.edge:5432`, database `zdm_edge` |

- **Dashboard sidecar**: loads every ConfigMap labelled `grafana_dashboard=1` from all namespaces: the ZDM dashboards of [`enterprise-grafana-dashboards`](../../../enterprise/dashboards/grafana/README.md) and the Kubernetes dashboards of `platform-prometheus`.
- **Admin credentials and data source passwords** from Secrets (no literal secret in the values; the upstream chart refuses literal secrets in `grafana.ini`).

Not provided: an operator feedback capture interface (CMP-12). Grafana dashboards are read-only; the feedback records of the edge data stock are only displayed. Alerting is done by Alertmanager (`platform-prometheus`), not by Grafana. Keycloak single sign-on is configured but **disabled** by default (`auth.generic_oauth.enabled: false`).

---

## ISO/IEC 42001 Mapping

| Clause | Requirement | How Grafana Addresses It |
|--------|-------------|--------------------------|
| B.6.1.3.1 | Resources: Access Control | Authenticated access (local admin; Keycloak OIDC ready) |
| B.6.1.3.3 | Resources: Human Oversight / Feedback | Real-time visibility of model behaviour, data quality, drift and security |
| B.6.2.6.2 | Operation: Model Performance | Model health dashboards on Prometheus metrics |

---

## Prerequisites

- `platform-prometheus`, `platform-loki`, `platform-timescaledb` and `edge-postgresql`.
- Secrets `platform-grafana-admin` (keys `admin-user`, `admin-password`) and `platform-grafana-datasources` (keys `TIMESCALEDB_PASSWORD`, `EDGEPG_PASSWORD`), created by `infrastructure/install.sh`.

---

## Deployment Questionnaire

The Rancher questionnaire is [`manifests/questions.yaml`](./manifests/questions.yaml).

---

## Installation (Helm)

```bash
helm repo add cigip-upv https://cigip-upv.github.io/MLOps-ISO42001-K3s-Catalog
helm install platform-grafana cigip-upv/platform-grafana -n monitoring

kubectl -n monitoring port-forward svc/platform-grafana 3000:80
kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/chart=platform-grafana
```

---

## Dashboards (enterprise overlay)

| Dashboard | RA Component |
|-----------|--------------|
| ZDM: Model Health | CMP-10 |
| ZDM: Input Data Monitoring | CMP-01 |
| ZDM: Data Consolidation, KPIs and Drift | CMP-02, CMP-11, CMP-14 |
| ZDM: Security Events and Audit Trail | CMP-15, CMP-09 |
| ZDM: Edge Predictions and Model Versions | CMP-03 |
| Kubernetes dashboards (kube-prometheus-stack) | CMP-08 |

---

## Related Solutions

- [Prometheus](../prometheus/README.md): metrics and alerting
- [Loki](../loki/README.md): logs
- [TimescaleDB](../../data-management/timescaledb/README.md): consolidated data, KPIs, drift
- [Grafana Dashboards (Overlay)](../../../enterprise/dashboards/grafana/README.md): ZDM dashboards
- [Keycloak](../../../enterprise/access-management/keycloak/README.md): single sign-on (optional)
