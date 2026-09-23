# Zammad: AI Helpdesk and Incident Management

| Field | Value |
|-------|-------|
| **Chart** | `enterprise-zammad` |
| **Tier** | Enterprise |
| **Namespace** | `helpdesk` |
| **Category** | Helpdesk |
| **RA Component** | AI Helpdesk (CMP-13) |
| **ISO/IEC 42001** | B.6.2.6.6 · B.8.0.4.1 · B.8.0.5.1 |
| **Helm Chart** | `zammad/zammad` 10.x (wrapped), image `ghcr.io/zammad/zammad` (chart appVersion) |
| **K3S Compatible** | Yes |

---

## Description

Zammad is an open-source **ticketing and helpdesk system** implementing the **AI Helpdesk** component: a single, traceable point of contact for incidents, adverse treatment reports and support requests about the AI system.

Its roles in the reference architecture are:

- **Incident reporting**: users report unexpected AI behaviour, prediction errors or failures as tickets, each one an auditable record.
- **Adverse treatment tracking**: operators report cases where predictions caused adverse outcomes (unnecessary stops, missed defects), addressing B.8.0.4.1.
- **Support knowledge base**: FAQs and operating procedures for AI system users.
- **SLA tracking**: response times of AI-related incidents.

What the chart deploys: the Zammad services (rails server, scheduler, websocket, nginx) with their data in the platform PostgreSQL (`platform-postgresql.platform`, database and role `zammad`), plus Elasticsearch (full-text search, about 1.5 GiB of memory), Redis and Memcached as subcharts with `bitnamilegacy` images. Earlier values targeted keys of an older chart layout and were ignored.

**Alerts to tickets are not automated.** Zammad has no endpoint that accepts the Alertmanager webhook format, and the previous `zammad-webhook` receiver of `platform-prometheus` could not work, so it was removed. Route critical alerts to Zammad through its e-mail channel (Alertmanager `email_configs` to a Zammad mailbox) or through an adapter that calls the Zammad ticket API.

---

## ISO/IEC 42001 Mapping

| Clause | Requirement | How Zammad Addresses It |
|--------|-------------|--------------------------|
| B.6.2.6.6 | Operation: Incident Communication | Single point of contact for user assistance; traceable support interactions |
| B.8.0.4.1 | Continual Improvement: Helpdesk | Ticket category for adverse treatment reports |
| B.8.0.5.1 | Continual Improvement: Alerts | Incident notification workflow (manual or by e-mail from Alertmanager) |

---

## Recommended Ticket Categories

| Category | Description | ISO Clause |
|----------|-------------|------------|
| Prediction Error | Model produced an incorrect prediction | B.6.2.6.6 |
| Adverse Treatment | AI action caused a negative outcome | B.8.0.4.1 |
| System Outage | AI service unavailable | B.8.0.5.1 |
| Data Quality Issue | Sensor data problem reported by an operator | B.6.2.6.4 |
| Access Request | User requesting new permissions | B.6.1.3.1 |

---

## Prerequisites

- `platform-postgresql` (database `zammad`).
- Secrets `enterprise-zammad-db` (key `postgresql-pass`) and `enterprise-zammad-redis` (key `redis-password`), created by `infrastructure/install.sh` (letters and digits only: the chart builds connection URLs without encoding).
- An SMTP relay for e-mail notifications (optional).

---

## Deployment Questionnaire

The Rancher questionnaire is [`manifests/questions.yaml`](./manifests/questions.yaml).

---

## Installation (Helm)

```bash
helm repo add cigip-upv https://cigip-upv.github.io/MLOps-ISO42001-K3s-Catalog
helm install enterprise-zammad cigip-upv/enterprise-zammad -n helpdesk

kubectl get pods,svc,deploy,sts -A -l mlops-iso42001.cigip-upv.es/chart=enterprise-zammad
```

The upstream chart has no label hook: `infrastructure/install.sh` adds the iso42001 labels with its post-renderer.

---

## Related Solutions

- [Prometheus + Alertmanager](../../../platform/monitoring/prometheus/README.md): alert source (e-mail route to be configured)
- [Keycloak](../../access-management/keycloak/README.md): identity provider (OIDC client `zammad` defined)
- [PostgreSQL (platform)](../../../platform/data-management/postgresql/README.md): Zammad database
