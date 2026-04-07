# Grafana — Dashboards, Goal-oriented Monitoring & Feedback Interface

| Field | Value |
|-------|-------|
| **Tier** | Platform · Enterprise |
| **Category** | Monitoring · Dashboards |
| **RA Component** | Goal-oriented Performance Monitoring · Model-based Technical Performance Monitoring · Feedback Interface · Information Centre |
| **ISO/IEC 42001** | B.6.1.2.2 · B.6.1.3.1 · B.6.1.3.3 · B.6.2.6.2 · B.6.2.6.3 · B.8.0.5.1 |
| **Helm Chart** | Included in `kube-prometheus-stack` or standalone `grafana/grafana` |
| **K3S Compatible** | Yes |

---

## Description

Grafana is the **primary observability and user-facing transparency interface** in the reference architecture. It consolidates metrics (Prometheus), logs (Loki), and operational data (TimescaleDB) into unified dashboards, implementing multiple RA components simultaneously.

Its key roles are:

- **Goal-oriented performance monitoring**: business KPI dashboards (OEE, availability, maintenance downtime, machine uptime) that translate AI predictions into actionable operational intelligence.
- **Model technical monitoring**: dashboards showing inference latency, accuracy trends, prediction score distributions, and drift indicators.
- **Information Centre**: provides operators and managers with a real-time overview of AI system status, predictions, and incidents.
- **Feedback interface**: annotated panels allow operators to confirm or reject predictions (human-in-the-loop), creating labelled events that feed the retraining recommendation.
- **Alerting**: Grafana Alerting routes threshold violations to Zammad (helpdesk), Slack, or email, implementing B.8.0.5.1 incident communication.
- **Log exploration**: Loki integration enables querying audit logs and security events directly from the dashboard.

---

## ISO/IEC 42001 Mapping

| Clause | Requirement | How Grafana Addresses It |
|--------|-------------|--------------------------|
| B.6.1.2.2 | Integration of Metrics | Unified view of all lifecycle metrics |
| B.6.1.3.1 | Human Oversight | Real-time visibility into AI decisions and system state |
| B.6.1.3.3 | Usability & Controllability | Intuitive dashboards for operators; feedback annotation capability |
| B.6.2.6.2 | Technical Performance Monitoring | Model accuracy, latency, and drift dashboards |
| B.6.2.6.3 | Goal-oriented Performance Monitoring | Business KPI dashboards (OEE, downtime, availability) |
| B.8.0.5.1 | Incident Communication | Alert routing to Zammad and operators |

---

## Prerequisites

- Prometheus deployed (primary data source)
- Loki deployed (log data source)
- TimescaleDB deployed (historical KPI data source)
- Persistent volume for Grafana (dashboard and configuration storage)
- Keycloak (for SSO authentication — recommended for enterprise tier access)

---

## Deployment Questionnaire

See [`questionnaire.md`](./questionnaire.md).

---

## Recommended Dashboards

| Dashboard | Purpose | RA Component |
|-----------|---------|--------------|
| OEE & Maintenance KPIs | Business performance visibility | Goal-oriented Performance Monitoring |
| Model Inference Health | Latency, error rates, prediction scores | Model-based Performance Monitoring |
| Infrastructure Overview | Node health, resource utilisation | Infrastructural Performance Monitoring |
| Security Events (Falco) | Runtime security alerts | Security Monitoring |
| Audit Log Explorer (Loki) | Event log search and review | Logger |
| Operator Feedback Panel | Prediction validation by operators | Feedback Interface |

---

## Feedback Interface Implementation

The Operator Feedback Panel is implemented as a Grafana annotation panel:

1. Grafana displays recent predictions from the FastAPI model server.
2. Operators annotate predictions as "Correct", "Incorrect", or "Uncertain".
3. Annotations are stored as Grafana annotations (or written back to PostgreSQL via a webhook).
4. The retraining recommendation engine reads these annotations as labelled samples.

This implements human-in-the-loop oversight per ALTAI and ISO/IEC 42001 B.6.1.3.3.

---

## Related Solutions

- [Prometheus](../prometheus/README.md) — primary metrics data source
- [Loki](../loki/README.md) — log data source
- [TimescaleDB](../../data-management/timescaledb/README.md) — historical KPI data source
- [Keycloak](../../../enterprise/access-management/keycloak/README.md) — SSO authentication for Grafana
- [Zammad](../../../enterprise/helpdesk/zammad/README.md) — alert routing target
