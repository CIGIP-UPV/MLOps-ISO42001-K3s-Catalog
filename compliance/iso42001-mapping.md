# ISO/IEC 42001 Compliance Matrix

This matrix maps every ISO/IEC 42001 Annex B requirement derived in the reference architecture to the K3S catalog solutions that implement it.

Use this matrix for:
- Internal compliance reviews
- External audit preparation
- Gap analysis when selecting a component subset (MVP deployments)

---

## Full Compliance Matrix

| Req. ID | Keyword | RA Component | K3S Solution(s) | Tier | Helm Chart / Tool |
|---------|---------|-------------|-----------------|------|-------------------|
| **B.6.1.2.2** | Integration of Metrics | Model-based Tech. Performance Monitoring · Infrastructural Tech. Performance Monitoring | Prometheus · Grafana · Prometheus Agent | Edge + Platform | `prometheus-community/kube-prometheus-stack` |
| **B.6.1.3.1** | Human Oversight | User Access and Oversight · Information Centre | Keycloak · Grafana | Enterprise + Platform | `bitnami/keycloak` · `grafana/grafana` |
| **B.6.1.3.2** | Version Control | Version Control | MLflow | Platform | `community-charts/mlflow` |
| **B.6.1.3.3** | Usability & Controllability | User Access and Oversight · Feedback Interface · Information Centre | Grafana · Zammad | Platform + Enterprise | `grafana/grafana` · `zammad/zammad` |
| **B.6.1.3.4** | Release Criteria | Version Control | MLflow (Model Registry staging gates) | Platform | `community-charts/mlflow` |
| **B.6.2.3.1** | Architecture Documentation | Document Store | MinIO (`iso42001-docs` bucket) | Enterprise | `minio/minio` |
| **B.6.2.5.1** | Deployment Plan | Document Store | MinIO (`iso42001-docs` bucket) | Enterprise | `minio/minio` |
| **B.6.2.6.1** | Error Monitoring | Infrastructural Technical Performance Monitoring · Data Stock | Prometheus · Loki · PostgreSQL | Platform + Edge | `prometheus-community/kube-prometheus-stack` · `grafana/loki-stack` |
| **B.6.2.6.2** | Technical Performance Monitoring | Model-based Technical Performance Monitoring | Prometheus · Grafana | Platform | `prometheus-community/kube-prometheus-stack` |
| **B.6.2.6.3** | Goal-oriented Performance Monitoring | Data Stock · Goal-oriented Performance Monitoring | Grafana · TimescaleDB | Platform + Enterprise | `grafana/grafana` · `timescale/timescaledb-single` |
| **B.6.2.6.4** | Retraining Monitoring | Input Data Monitoring · Feedback Interface · Retraining Recommendation | Node-RED · Grafana Feedback · MLflow Training Jobs | Edge + Platform | `node-red/node-red` · `community-charts/mlflow` |
| **B.6.2.6.5** | Update & Repair Plan | Document Store | MinIO (`iso42001-docs` bucket) | Enterprise | `minio/minio` |
| **B.6.2.6.6** | AI Helpdesk | AI Helpdesk | Zammad | Enterprise | `zammad/zammad` |
| **B.6.2.6.7** | Threat Detection | Input Data Monitoring · Security Monitoring | Falco · Node-RED (validation) · Keycloak | Edge + Enterprise | `falcosecurity/falco` · `bitnami/keycloak` |
| **B.6.2.8.1** | Event Logs | Data Stock · Logger | Fluent Bit · Loki · PostgreSQL | Edge + Platform | `fluent/fluent-bit` · `grafana/loki-stack` |
| **B.8.0.2.1** | User Information | Information Centre · User Access and Oversight | Grafana · Keycloak | Platform + Enterprise | `grafana/grafana` · `bitnami/keycloak` |
| **B.8.0.4.1** | Display of Adverse Treatment | AI Helpdesk | Zammad (Adverse Treatment ticket category) | Enterprise | `zammad/zammad` |
| **B.8.0.5.1** | Incident Communication | AI Helpdesk · Information Centre | Zammad · Grafana Alerting | Enterprise + Platform | `zammad/zammad` · `grafana/grafana` |

---

## Coverage by Standard

### ISO/IEC 42001 Annex B

**Total requirements derived**: 18
**Covered by at least one catalog solution**: 18 (100%)

### ALTAI (Assessment List for Trustworthy AI)

| ALTAI Principle | Covered By |
|-----------------|-----------|
| Human agency and oversight | Grafana Feedback Interface · Keycloak · Zammad |
| Technical robustness and safety | Falco · Prometheus · Fluent Bit · PostgreSQL buffering |
| Privacy and data governance | Keycloak (access control) · Falco (monitoring) |
| Transparency | MLflow · Grafana Information Centre · MinIO Document Store |
| Diversity, non-discrimination and fairness | Feedback Interface (operator corrections) |
| Societal and environmental wellbeing | OEE monitoring → reduced resource waste |
| Accountability | Zammad · Event Logs · MLflow audit trail |

### EU AI Act (High-Risk Systems)

| Requirement | Covered By |
|-------------|-----------|
| Auditability | Fluent Bit + Loki + MLflow |
| Explainability (minimal) | Grafana prediction panels + feedback loop |
| Human-in-the-loop control | Grafana Feedback Interface + MLflow approval gates |
| Data governance | Node-RED validation + TimescaleDB + MinIO |
| Accuracy, robustness, cybersecurity | Prometheus monitoring + Falco + Keycloak |

### ISA/IEC 62443

| Requirement | Covered By |
|-------------|-----------|
| Zone segmentation | K3S namespaces + network policies |
| Intrusion detection | Falco (runtime) + Prometheus (anomaly metrics) |
| Secure remote access | Keycloak SSO + TLS ingress |
| Industrial interoperability | Node-RED protocol adapters + OPC-UA bridge |

---

## Minimum Viable Product (MVP) Coverage

If deploying a subset of solutions, this table shows which requirements remain unaddressed:

| Req. ID | MVP Covered? | MVP Alternative / Workaround |
|---------|-------------|------------------------------|
| B.6.1.2.2 | ✅ Prometheus + Grafana | — |
| B.6.1.3.1 | ⚠️ Partial | Use Grafana basic auth (no role segregation) |
| B.6.1.3.2 | ✅ MLflow | — |
| B.6.1.3.3 | ⚠️ Partial | Use Grafana without Keycloak roles |
| B.6.1.3.4 | ✅ MLflow gates | — |
| B.6.2.3.1 | ⚠️ Partial | Store docs in Git repository as interim |
| B.6.2.5.1 | ⚠️ Partial | Store in Git repository as interim |
| B.6.2.6.1 | ✅ Prometheus + Loki | — |
| B.6.2.6.2 | ✅ Prometheus | — |
| B.6.2.6.3 | ✅ Grafana + PostgreSQL | TimescaleDB deferred |
| B.6.2.6.4 | ✅ Node-RED + MLflow | — |
| B.6.2.6.5 | ⚠️ Partial | Store in Git repository as interim |
| B.6.2.6.6 | ❌ Not covered | Use email inbox as interim helpdesk |
| B.6.2.6.7 | ✅ Falco + Node-RED | Keycloak deferred |
| B.6.2.8.1 | ✅ Fluent Bit + Loki | — |
| B.8.0.2.1 | ⚠️ Partial | Grafana only (no Keycloak account console) |
| B.8.0.4.1 | ❌ Not covered | Use email or Grafana annotation as interim |
| B.8.0.5.1 | ⚠️ Partial | Grafana alerts only (no structured ticketing) |

**Legend**: ✅ Fully covered · ⚠️ Partially covered · ❌ Not covered in MVP

> Document all gaps and workarounds in the Deployment Plan (MinIO `iso42001-docs/deployment-plan/`) with a timeline for addressing them in subsequent iterations.
