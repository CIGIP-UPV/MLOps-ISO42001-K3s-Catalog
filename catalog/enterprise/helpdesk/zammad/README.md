# Zammad — AI Helpdesk & Incident Management

| Field | Value |
|-------|-------|
| **Tier** | Enterprise |
| **Category** | Helpdesk |
| **RA Component** | AI Helpdesk |
| **ISO/IEC 42001** | B.6.2.6.6 · B.8.0.4.1 · B.8.0.5.1 |
| **Helm Chart** | `zammad/zammad` |
| **K3S Compatible** | Yes |

---

## Description

Zammad is an open-source **ticketing and helpdesk system** implementing the **AI Helpdesk** component. It provides a single, traceable point of contact for all user-reported incidents, adverse treatment events, and AI system support requests.

Its key roles in the reference architecture are:

- **Incident reporting**: users report unexpected AI behaviour, prediction errors, or system failures through Zammad tickets. Each ticket creates an auditable incident record.
- **Adverse treatment tracking**: operators can report cases where AI predictions caused adverse outcomes (e.g., unnecessary machine shutdown, missed defect) — directly addressing B.8.0.4.1.
- **Incident communication**: Grafana Alertmanager automatically creates Zammad tickets when monitoring thresholds are crossed, implementing B.8.0.5.1.
- **Support knowledge base**: Zammad's knowledge base stores FAQs and operating procedures for AI system users.
- **SLA tracking**: tracks response times for AI-related incidents, supporting continuous improvement requirements.

---

## ISO/IEC 42001 Mapping

| Clause | Requirement | How Zammad Addresses It |
|--------|-------------|--------------------------|
| B.6.2.6.6 | AI Helpdesk | Single point of contact for user assistance; traceable support interactions |
| B.8.0.4.1 | Display of Adverse Treatment | Dedicated ticket category for reporting AI-caused adverse treatment |
| B.8.0.5.1 | Incident Communication | Automated ticket creation from Grafana alerts; incident notification workflow |

---

## Recommended Ticket Categories

| Category | Description | ISO Clause |
|----------|-------------|------------|
| Prediction Error | Model produced an incorrect prediction | B.6.2.6.6 |
| Adverse Treatment | AI action caused negative outcome | B.8.0.4.1 |
| System Outage | AI service unavailable | B.8.0.5.1 |
| Data Quality Issue | Sensor data problem reported by operator | B.6.2.6.4 |
| Access Request | User requesting new permissions | B.6.1.3.1 |
| Compliance Query | Question about AI system governance | B.6.2.6.6 |

---

## Prerequisites

- K3S enterprise cluster
- PostgreSQL for Zammad database
- Elasticsearch for Zammad full-text search (or use internal search for small deployments)
- SMTP server or email relay for ticket notifications
- Keycloak for SSO authentication (recommended)

---

## Deployment Questionnaire

See [`questionnaire.md`](./questionnaire.md).

---

## Installation (K3S / Helm)

```bash
helm repo add zammad https://zammad.github.io/zammad-helm
helm repo update

helm install zammad zammad/zammad \
  --namespace helpdesk \
  --create-namespace \
  -f values.yaml
```

---

## Grafana Alert → Zammad Integration

Configure Grafana Alertmanager to post to Zammad's email or webhook:

```yaml
# Grafana alerting contact point (webhook)
url: https://zammad.enterprise.local/api/v1/tickets
method: POST
headers:
  Authorization: "Token token=<zammad-api-token>"
message: |
  {
    "title": "{{ .GroupLabels.alertname }}",
    "group": "AI System Alert",
    "customer": "ai-system@plant.local",
    "article": {
      "subject": "{{ .GroupLabels.alertname }}",
      "body": "{{ .CommonAnnotations.description }}",
      "type": "note"
    }
  }
```

---

## Related Solutions

- [Grafana](../../../platform/monitoring/grafana/README.md) — alert source creating Zammad tickets
- [Keycloak](../access-management/keycloak/README.md) — SSO for helpdesk authentication
- [Fluent Bit](../../../edge/monitoring/fluent-bit/README.md) — log correlation with incidents
